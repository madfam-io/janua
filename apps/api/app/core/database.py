from typing import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData, select
import structlog

# Import config with error handling
try:
    from app.config import settings
except Exception as e:
    print(f"Failed to import settings: {e}")
    raise

logger = structlog.get_logger()

# Database naming conventions
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Create async engine with error handling
try:
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured")
    
    # Auto-fix Railway PostgreSQL URL format for SQLAlchemy async
    if settings.DATABASE_URL.startswith('postgresql://'):
        database_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
    else:
        database_url = settings.DATABASE_URL
    
    # Configure engine based on database type
    if database_url.startswith('sqlite'):
        # SQLite doesn't support connection pooling
        engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_pre_ping=True
        )
    else:
        # PostgreSQL with connection pooling
        engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=True
        )
    
    # Create async session maker
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
except Exception as e:
    print(f"Failed to create database engine: {e}")
    print(f"DATABASE_URL: {getattr(settings, 'DATABASE_URL', 'NOT SET')}")
    raise


async def init_db():
    """Initialize database connection and create tables if needed"""
    try:
        async with engine.begin() as conn:
            if settings.AUTO_MIGRATE:
                await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")

        # Bootstrap admin user if ADMIN_BOOTSTRAP_PASSWORD is set
        await bootstrap_admin_user()
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def bootstrap_admin_user():
    """Bootstrap the admin user if ADMIN_BOOTSTRAP_PASSWORD environment variable is set.

    This creates admin@madfam.io with is_admin=True and email_verified=True.
    Only runs if the user doesn't already exist.
    """
    admin_password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    if not admin_password:
        logger.debug("ADMIN_BOOTSTRAP_PASSWORD not set, skipping admin bootstrap")
        return

    admin_email = "admin@madfam.io"

    try:
        # Import here to avoid circular imports
        from app.models import User
        from passlib.context import CryptContext
        from app.core.database_manager import db_manager

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with db_manager.get_session() as session:
            # Check if admin already exists
            result = await session.execute(
                select(User).where(User.email == admin_email)
            )
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                logger.info("Admin user already exists, skipping bootstrap", email=admin_email)
                return

            # Create admin user
            password_hash = pwd_context.hash(admin_password)
            admin_user = User(
                email=admin_email,
                email_verified=True,
                password_hash=password_hash,
                is_admin=True,
                is_active=True,
                first_name="Admin",
                last_name="User",
            )
            session.add(admin_user)
            await session.commit()

            logger.info("Admin user bootstrapped successfully", email=admin_email)
    except Exception as e:
        logger.error("Failed to bootstrap admin user", error=str(e))
        # Don't raise - this is a non-critical bootstrap operation


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()