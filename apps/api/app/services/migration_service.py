"""
Migration service for importing users from various identity providers
"""

import asyncio
import csv
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx
import bcrypt
import hashlib
import hmac
from passlib.hash import pbkdf2_sha256, scrypt, argon2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models import User, Organization
from ..models.migration import (
    MigrationJob, MigrationProvider, MigrationStatus,
    MigratedUser, MigrationLog, HashAlgorithm,
    PasswordHashAdapter, MigrationTemplate
)
from ..database import get_db

logger = logging.getLogger(__name__)


class MigrationService:
    """Service for migrating users from various identity providers"""
    
    def __init__(self):
        self.providers = {
            MigrationProvider.AUTH0: Auth0MigrationAdapter(),
            MigrationProvider.OKTA: OktaMigrationAdapter(),
            MigrationProvider.COGNITO: CognitoMigrationAdapter(),
            MigrationProvider.FIREBASE: FirebaseMigrationAdapter(),
            MigrationProvider.CSV: CSVMigrationAdapter(),
            MigrationProvider.JSON: JSONMigrationAdapter(),
        }
        
        self.hash_adapters = {
            HashAlgorithm.BCRYPT: BCryptAdapter(),
            HashAlgorithm.PBKDF2: PBKDF2Adapter(),
            HashAlgorithm.SCRYPT: ScryptAdapter(),
            HashAlgorithm.ARGON2: Argon2Adapter(),
            HashAlgorithm.SHA256: SHA256Adapter(),
            HashAlgorithm.SHA512: SHA512Adapter(),
        }
    
    async def create_migration_job(
        self,
        db: AsyncSession,
        organization_id: Optional[str],
        provider: MigrationProvider,
        name: str,
        source_config: Dict[str, Any],
        mapping_config: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new migration job"""
        try:
            # Get default template if no mapping provided
            if not mapping_config:
                template = await self._get_default_template(db, provider)
                if template:
                    mapping_config = template.field_mappings
                else:
                    mapping_config = self._get_default_mapping(provider)
            
            job = MigrationJob(
                organization_id=organization_id,
                name=name,
                provider=provider,
                source_config=source_config,
                mapping_config=mapping_config,
                options=options or {}
            )
            
            db.add(job)
            await db.commit()
            
            await self._log_migration(
                db, str(job.id), "info",
                f"Migration job created for {provider.value}"
            )
            
            return {
                "job_id": str(job.id),
                "status": job.status.value,
                "provider": provider.value
            }
            
        except Exception as e:
            logger.error(f"Failed to create migration job: {e}")
            raise
    
    async def start_migration(
        self,
        db: AsyncSession,
        job_id: str,
        batch_size: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Start migration job and yield progress updates"""
        try:
            # Get migration job
            job = await db.get(MigrationJob, job_id)
            if not job:
                raise ValueError("Migration job not found")
            
            # Update job status
            job.status = MigrationStatus.IN_PROGRESS
            job.started_at = datetime.utcnow()
            await db.commit()
            
            # Get provider adapter
            adapter = self.providers.get(job.provider)
            if not adapter:
                raise ValueError(f"Provider {job.provider} not supported")
            
            # Fetch users from source
            total_users = 0
            migrated_count = 0
            failed_count = 0
            
            async for user_batch in adapter.fetch_users(
                job.source_config,
                batch_size
            ):
                total_users += len(user_batch)
                job.total_users = total_users
                
                # Process batch
                for source_user in user_batch:
                    try:
                        # Map user data
                        mapped_data = await self._map_user_data(
                            source_user,
                            job.mapping_config
                        )
                        
                        # Check if user already exists
                        existing_user = await self._check_existing_user(
                            db,
                            mapped_data.get("email"),
                            mapped_data.get("username")
                        )
                        
                        if existing_user and not job.options.get("update_existing"):
                            await self._log_migration(
                                db, job_id, "info",
                                f"User {mapped_data.get('email')} already exists, skipping",
                                source_user.get("id")
                            )
                            job.skipped_users += 1
                            continue
                        
                        # Migrate password if available
                        password_hash = None
                        hash_algorithm = None
                        requires_reset = False
                        
                        if source_user.get("password_hash"):
                            password_hash, hash_algorithm, requires_reset = \
                                await self._migrate_password(
                                    source_user.get("password_hash"),
                                    source_user.get("hash_algorithm")
                                )
                        
                        # Create or update user
                        if existing_user:
                            target_user = await self._update_user(
                                db,
                                existing_user,
                                mapped_data,
                                password_hash
                            )
                        else:
                            target_user = await self._create_user(
                                db,
                                mapped_data,
                                password_hash,
                                job.organization_id
                            )
                        
                        # Track migrated user
                        migrated_user = MigratedUser(
                            migration_job_id=job_id,
                            source_user_id=str(source_user.get("id", "")),
                            source_email=source_user.get("email"),
                            source_username=source_user.get("username"),
                            target_user_id=target_user.id,
                            is_migrated=True,
                            password_migrated=bool(password_hash),
                            requires_password_reset=requires_reset,
                            hash_algorithm=hash_algorithm,
                            source_data=source_user,
                            mapped_data=mapped_data,
                            migrated_at=datetime.utcnow()
                        )
                        db.add(migrated_user)
                        
                        migrated_count += 1
                        job.migrated_users = migrated_count
                        
                        # Yield progress update
                        yield {
                            "type": "progress",
                            "total": total_users,
                            "migrated": migrated_count,
                            "failed": failed_count,
                            "current_user": mapped_data.get("email")
                        }
                        
                    except Exception as e:
                        failed_count += 1
                        job.failed_users = failed_count
                        job.last_error = str(e)
                        job.error_count += 1
                        
                        await self._log_migration(
                            db, job_id, "error",
                            f"Failed to migrate user: {e}",
                            source_user.get("id")
                        )
                        
                        # Track failed migration
                        migrated_user = MigratedUser(
                            migration_job_id=job_id,
                            source_user_id=str(source_user.get("id", "")),
                            source_email=source_user.get("email"),
                            source_username=source_user.get("username"),
                            is_migrated=False,
                            migration_errors=[str(e)],
                            source_data=source_user
                        )
                        db.add(migrated_user)
                
                # Commit batch
                await db.commit()
            
            # Update job completion
            job.status = MigrationStatus.COMPLETED if failed_count == 0 else MigrationStatus.PARTIAL
            job.completed_at = datetime.utcnow()
            await db.commit()
            
            yield {
                "type": "completed",
                "total": total_users,
                "migrated": migrated_count,
                "failed": failed_count,
                "skipped": job.skipped_users
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            job.status = MigrationStatus.FAILED
            job.last_error = str(e)
            await db.commit()
            
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def _map_user_data(
        self,
        source_user: Dict[str, Any],
        mapping_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map source user data to target schema"""
        mapped = {}
        
        for target_field, mapping in mapping_config.items():
            if isinstance(mapping, str):
                # Simple field mapping
                mapped[target_field] = source_user.get(mapping)
            elif isinstance(mapping, dict):
                # Complex mapping with transformation
                source_field = mapping.get("source")
                transform = mapping.get("transform")
                
                if isinstance(source_field, list):
                    # Multiple source fields
                    values = [source_user.get(f) for f in source_field]
                    value = self._apply_transformation(values, transform)
                else:
                    # Single source field
                    value = source_user.get(source_field)
                    if transform:
                        value = self._apply_transformation(value, transform)
                
                mapped[target_field] = value
        
        return mapped
    
    async def _migrate_password(
        self,
        password_hash: str,
        algorithm: Optional[str]
    ) -> tuple[Optional[str], Optional[HashAlgorithm], bool]:
        """Migrate password hash to our format"""
        if not password_hash or not algorithm:
            return None, None, True
        
        try:
            # Try to identify algorithm
            hash_algorithm = self._identify_hash_algorithm(algorithm, password_hash)
            
            # Check if we can directly use the hash
            if hash_algorithm == HashAlgorithm.BCRYPT:
                # BCrypt hashes can be used directly
                return password_hash, hash_algorithm, False
            
            # For other algorithms, we'll need to verify and re-hash on login
            # Store the original hash with metadata
            return password_hash, hash_algorithm, True
            
        except Exception as e:
            logger.warning(f"Failed to migrate password hash: {e}")
            return None, None, True
    
    def _identify_hash_algorithm(
        self,
        algorithm: str,
        hash_value: str
    ) -> HashAlgorithm:
        """Identify hash algorithm from string"""
        algorithm_lower = algorithm.lower()
        
        # Check by algorithm name
        if "bcrypt" in algorithm_lower:
            return HashAlgorithm.BCRYPT
        elif "pbkdf2" in algorithm_lower:
            return HashAlgorithm.PBKDF2
        elif "scrypt" in algorithm_lower:
            return HashAlgorithm.SCRYPT
        elif "argon2" in algorithm_lower:
            return HashAlgorithm.ARGON2
        elif "sha512" in algorithm_lower:
            return HashAlgorithm.SHA512
        elif "sha256" in algorithm_lower:
            return HashAlgorithm.SHA256
        elif "md5" in algorithm_lower:
            return HashAlgorithm.MD5
        
        # Check by hash format
        if hash_value.startswith("$2"):  # BCrypt
            return HashAlgorithm.BCRYPT
        elif hash_value.startswith("$argon2"):  # Argon2
            return HashAlgorithm.ARGON2
        elif hash_value.startswith("$pbkdf2"):  # PBKDF2
            return HashAlgorithm.PBKDF2
        elif hash_value.startswith("$scrypt"):  # Scrypt
            return HashAlgorithm.SCRYPT
        
        return HashAlgorithm.CUSTOM
    
    def _apply_transformation(self, value: Any, transform: str) -> Any:
        """Apply transformation to value"""
        if not transform or value is None:
            return value
        
        try:
            if transform == "lowercase":
                return str(value).lower()
            elif transform == "uppercase":
                return str(value).upper()
            elif transform == "concat":
                if isinstance(value, list):
                    return " ".join(filter(None, value))
                return str(value)
            elif transform == "json":
                if isinstance(value, str):
                    return json.loads(value)
                return value
            elif transform == "string":
                return str(value)
            elif transform == "boolean":
                return bool(value)
            elif transform == "date":
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
                return value
        except:
            pass
        
        return value
    
    async def _check_existing_user(
        self,
        db: AsyncSession,
        email: Optional[str],
        username: Optional[str]
    ) -> Optional[User]:
        """Check if user already exists"""
        if email:
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            if user:
                return user
        
        if username:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        
        return None
    
    async def _create_user(
        self,
        db: AsyncSession,
        user_data: Dict[str, Any],
        password_hash: Optional[str],
        organization_id: Optional[str]
    ) -> User:
        """Create new user from migrated data"""
        user = User(
            email=user_data.get("email"),
            username=user_data.get("username"),
            password_hash=password_hash,
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            display_name=user_data.get("display_name"),
            email_verified=user_data.get("email_verified", False),
            phone_number=user_data.get("phone_number"),
            phone_verified=user_data.get("phone_verified", False),
            user_metadata=user_data.get("metadata", {})
        )
        
        db.add(user)
        await db.flush()
        
        # Add to organization if specified
        if organization_id:
            # TODO: Add organization membership
            pass
        
        return user
    
    async def _update_user(
        self,
        db: AsyncSession,
        user: User,
        user_data: Dict[str, Any],
        password_hash: Optional[str]
    ) -> User:
        """Update existing user with migrated data"""
        # Update fields that are not already set
        if not user.first_name and user_data.get("first_name"):
            user.first_name = user_data.get("first_name")
        if not user.last_name and user_data.get("last_name"):
            user.last_name = user_data.get("last_name")
        if not user.display_name and user_data.get("display_name"):
            user.display_name = user_data.get("display_name")
        if not user.phone_number and user_data.get("phone_number"):
            user.phone_number = user_data.get("phone_number")
        
        # Update password if provided and user doesn't have one
        if password_hash and not user.password_hash:
            user.password_hash = password_hash
        
        # Merge metadata
        if user_data.get("metadata"):
            user.user_metadata = {**user.user_metadata, **user_data.get("metadata")}
        
        await db.flush()
        return user
    
    async def _log_migration(
        self,
        db: AsyncSession,
        job_id: str,
        level: str,
        message: str,
        user_id: Optional[str] = None
    ):
        """Log migration event"""
        log = MigrationLog(
            migration_job_id=job_id,
            level=level,
            message=message,
            user_id=user_id
        )
        db.add(log)
        await db.flush()
    
    async def _get_default_template(
        self,
        db: AsyncSession,
        provider: MigrationProvider
    ) -> Optional[MigrationTemplate]:
        """Get default template for provider"""
        result = await db.execute(
            select(MigrationTemplate).where(
                MigrationTemplate.provider == provider,
                MigrationTemplate.is_default == True
            )
        )
        return result.scalar_one_or_none()
    
    def _get_default_mapping(self, provider: MigrationProvider) -> Dict[str, Any]:
        """Get default field mapping for provider"""
        if provider == MigrationProvider.AUTH0:
            return {
                "email": "email",
                "username": "username",
                "email_verified": "email_verified",
                "first_name": {"source": "given_name", "transform": "string"},
                "last_name": {"source": "family_name", "transform": "string"},
                "display_name": "name",
                "phone_number": "phone_number",
                "phone_verified": "phone_verified",
                "metadata": {"source": "user_metadata", "transform": "json"}
            }
        elif provider == MigrationProvider.OKTA:
            return {
                "email": {"source": "profile.email", "transform": "lowercase"},
                "username": {"source": "profile.login", "transform": "lowercase"},
                "email_verified": {"source": "status", "transform": "boolean"},
                "first_name": "profile.firstName",
                "last_name": "profile.lastName",
                "display_name": {"source": ["profile.firstName", "profile.lastName"], "transform": "concat"},
                "phone_number": "profile.mobilePhone",
                "metadata": "profile"
            }
        else:
            return {
                "email": "email",
                "username": "username",
                "first_name": "first_name",
                "last_name": "last_name",
                "display_name": "display_name"
            }


class Auth0MigrationAdapter:
    """Auth0 migration adapter"""
    
    async def fetch_users(
        self,
        config: Dict[str, Any],
        batch_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users from Auth0"""
        domain = config.get("domain")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        connection = config.get("connection", "Username-Password-Authentication")
        
        if not all([domain, client_id, client_secret]):
            raise ValueError("Missing Auth0 configuration")
        
        async with httpx.AsyncClient() as client:
            # Get access token
            token_response = await client.post(
                f"https://{domain}/oauth/token",
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "audience": f"https://{domain}/api/v2/",
                    "grant_type": "client_credentials"
                }
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            
            # Fetch users with pagination
            page = 0
            headers = {"Authorization": f"Bearer {access_token}"}
            
            while True:
                response = await client.get(
                    f"https://{domain}/api/v2/users",
                    headers=headers,
                    params={
                        "per_page": batch_size,
                        "page": page,
                        "connection": connection,
                        "include_totals": "true"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                users = data.get("users", [])
                if not users:
                    break
                
                # Transform Auth0 users
                transformed_users = []
                for user in users:
                    transformed_users.append({
                        "id": user.get("user_id"),
                        "email": user.get("email"),
                        "username": user.get("username"),
                        "email_verified": user.get("email_verified"),
                        "given_name": user.get("given_name"),
                        "family_name": user.get("family_name"),
                        "name": user.get("name"),
                        "picture": user.get("picture"),
                        "phone_number": user.get("phone_number"),
                        "phone_verified": user.get("phone_verified"),
                        "user_metadata": user.get("user_metadata", {}),
                        "app_metadata": user.get("app_metadata", {}),
                        "created_at": user.get("created_at"),
                        "updated_at": user.get("updated_at")
                    })
                
                yield transformed_users
                
                # Check if more pages
                total = data.get("total", 0)
                if (page + 1) * batch_size >= total:
                    break
                
                page += 1


class OktaMigrationAdapter:
    """Okta migration adapter"""
    
    async def fetch_users(
        self,
        config: Dict[str, Any],
        batch_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users from Okta"""
        domain = config.get("domain")
        api_token = config.get("api_token")
        
        if not all([domain, api_token]):
            raise ValueError("Missing Okta configuration")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"SSWS {api_token}"}
            url = f"https://{domain}/api/v1/users"
            
            while url:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"limit": batch_size}
                )
                response.raise_for_status()
                users = response.json()
                
                if not users:
                    break
                
                # Transform Okta users
                transformed_users = []
                for user in users:
                    profile = user.get("profile", {})
                    transformed_users.append({
                        "id": user.get("id"),
                        "status": user.get("status"),
                        "created": user.get("created"),
                        "activated": user.get("activated"),
                        "statusChanged": user.get("statusChanged"),
                        "lastLogin": user.get("lastLogin"),
                        "lastUpdated": user.get("lastUpdated"),
                        "profile": profile,
                        # Flatten common fields for easier access
                        "email": profile.get("email"),
                        "username": profile.get("login"),
                        "firstName": profile.get("firstName"),
                        "lastName": profile.get("lastName"),
                        "mobilePhone": profile.get("mobilePhone")
                    })
                
                yield transformed_users
                
                # Check for next page
                link_header = response.headers.get("link")
                url = None
                if link_header:
                    links = link_header.split(",")
                    for link in links:
                        if 'rel="next"' in link:
                            url = link.split(";")[0].strip("<>")
                            break


class CognitoMigrationAdapter:
    """AWS Cognito migration adapter"""
    
    async def fetch_users(
        self,
        config: Dict[str, Any],
        batch_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users from Cognito"""
        # Implementation would use boto3 for AWS SDK
        # This is a placeholder for the structure
        yield []


class FirebaseMigrationAdapter:
    """Firebase migration adapter"""
    
    async def fetch_users(
        self,
        config: Dict[str, Any],
        batch_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users from Firebase"""
        # Implementation would use Firebase Admin SDK
        # This is a placeholder for the structure
        yield []


class CSVMigrationAdapter:
    """CSV file migration adapter"""
    
    async def fetch_users(
        self,
        config: Dict[str, Any],
        batch_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users from CSV file"""
        file_path = config.get("file_path")
        encoding = config.get("encoding", "utf-8")
        delimiter = config.get("delimiter", ",")
        
        if not file_path:
            raise ValueError("Missing CSV file path")
        
        with open(file_path, "r", encoding=encoding) as file:
            reader = csv.DictReader(file, delimiter=delimiter)
            batch = []
            
            for row in reader:
                batch.append(row)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            
            if batch:
                yield batch


class JSONMigrationAdapter:
    """JSON file migration adapter"""
    
    async def fetch_users(
        self,
        config: Dict[str, Any],
        batch_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users from JSON file"""
        file_path = config.get("file_path")
        
        if not file_path:
            raise ValueError("Missing JSON file path")
        
        with open(file_path, "r") as file:
            data = json.load(file)
            
            users = data if isinstance(data, list) else data.get("users", [])
            
            for i in range(0, len(users), batch_size):
                yield users[i:i + batch_size]


# Password hash adapters
class BCryptAdapter:
    """BCrypt password hash adapter"""
    
    def verify(self, password: str, hash_value: str) -> bool:
        """Verify password against BCrypt hash"""
        return bcrypt.checkpw(password.encode(), hash_value.encode())
    
    def hash(self, password: str, rounds: int = 12) -> str:
        """Hash password with BCrypt"""
        salt = bcrypt.gensalt(rounds)
        return bcrypt.hashpw(password.encode(), salt).decode()


class PBKDF2Adapter:
    """PBKDF2 password hash adapter"""
    
    def verify(self, password: str, hash_value: str) -> bool:
        """Verify password against PBKDF2 hash"""
        return pbkdf2_sha256.verify(password, hash_value)
    
    def hash(self, password: str, iterations: int = 100000) -> str:
        """Hash password with PBKDF2"""
        return pbkdf2_sha256.hash(password, rounds=iterations)


class ScryptAdapter:
    """Scrypt password hash adapter"""
    
    def verify(self, password: str, hash_value: str) -> bool:
        """Verify password against Scrypt hash"""
        return scrypt.verify(password, hash_value)
    
    def hash(self, password: str) -> str:
        """Hash password with Scrypt"""
        return scrypt.hash(password)


class Argon2Adapter:
    """Argon2 password hash adapter"""
    
    def verify(self, password: str, hash_value: str) -> bool:
        """Verify password against Argon2 hash"""
        return argon2.verify(password, hash_value)
    
    def hash(self, password: str) -> str:
        """Hash password with Argon2"""
        return argon2.hash(password)


class SHA256Adapter:
    """SHA256 password hash adapter (legacy)"""
    
    def verify(self, password: str, hash_value: str, salt: str = "") -> bool:
        """Verify password against SHA256 hash"""
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash == hash_value
    
    def hash(self, password: str, salt: str = "") -> str:
        """Hash password with SHA256"""
        return hashlib.sha256((password + salt).encode()).hexdigest()


class SHA512Adapter:
    """SHA512 password hash adapter (legacy)"""
    
    def verify(self, password: str, hash_value: str, salt: str = "") -> bool:
        """Verify password against SHA512 hash"""
        password_hash = hashlib.sha512((password + salt).encode()).hexdigest()
        return password_hash == hash_value
    
    def hash(self, password: str, salt: str = "") -> str:
        """Hash password with SHA512"""
        return hashlib.sha512((password + salt).encode()).hexdigest()