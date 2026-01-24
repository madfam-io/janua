"""
Comprehensive Storage Service Test Suite
Tests for file upload, download, deletion and avatar management
"""

import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.storage import (
    StorageService,
    AvatarService,
    _is_r2_endpoint,
    storage_service,
)

pytestmark = pytest.mark.asyncio


class TestIsR2Endpoint:
    """Test R2 endpoint validation function."""

    def test_valid_r2_endpoint(self):
        """Test valid R2 endpoint is recognized."""
        assert _is_r2_endpoint("abc123.r2.cloudflarestorage.com") is True

    def test_valid_r2_endpoint_uppercase(self):
        """Test R2 endpoint is case-insensitive."""
        assert _is_r2_endpoint("ABC123.R2.CLOUDFLARESTORAGE.COM") is True

    def test_valid_r2_endpoint_with_spaces(self):
        """Test R2 endpoint strips whitespace."""
        assert _is_r2_endpoint("  abc123.r2.cloudflarestorage.com  ") is True

    def test_invalid_r2_endpoint_regular_s3(self):
        """Test regular S3 endpoint is not recognized as R2."""
        assert _is_r2_endpoint("bucket.s3.amazonaws.com") is False

    def test_invalid_r2_endpoint_subdomain_bypass(self):
        """Test subdomain bypass attack is prevented."""
        # This would be a security bypass attempt
        assert _is_r2_endpoint("r2.cloudflarestorage.com.attacker.com") is False

    def test_invalid_r2_endpoint_prefix_bypass(self):
        """Test prefix bypass is prevented."""
        assert _is_r2_endpoint("evil-r2.cloudflarestorage.com") is False

    def test_invalid_r2_endpoint_empty(self):
        """Test empty string is not R2 endpoint."""
        assert _is_r2_endpoint("") is False


class TestStorageServiceInitialization:
    """Test StorageService initialization."""

    def test_service_initialization_local(self):
        """Test service initializes with local storage when S3 not configured."""
        with patch("app.services.storage.boto3", None):
            service = StorageService()
            assert service.storage_type == "local"
            assert service.s3_client is None

    def test_service_has_upload_dir(self):
        """Test service has upload directory for local storage."""
        with patch("app.services.storage.boto3", None):
            service = StorageService()
            assert hasattr(service, "upload_dir")

    def test_service_determines_storage_type(self):
        """Test service determines storage type correctly."""
        with patch("app.services.storage.boto3", None):
            service = StorageService()
            result = service._determine_storage_type()
            # Without boto3, should fallback to local
            assert result == "local"


class TestStorageServiceLocalUpload:
    """Test local file upload functionality."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    async def test_upload_file_local_success(self, service):
        """Test successful local file upload."""
        file_content = b"test file content"
        filename = "test.txt"

        # Mock aiofiles
        mock_file = AsyncMock()
        mock_file.write = AsyncMock()

        # Mock _validate_file_type to return True
        with patch.object(service, "_validate_file_type", return_value=True):
            with patch("app.services.storage.aiofiles") as mock_aiofiles:
                mock_aiofiles.open = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_file), __aexit__=AsyncMock()))

                result = await service.upload_file(
                    file_content=file_content,
                    filename=filename,
                    content_type="text/plain",
                )

        assert "url" in result
        assert "filename" in result
        assert "path" in result
        assert result["size"] == len(file_content)
        assert result["storage_type"] == "local"

    async def test_upload_file_invalid_type(self, service):
        """Test upload with invalid file type."""
        file_content = b"malicious content"
        filename = "test.exe"

        with patch.object(service, "_validate_file_type", return_value=False):
            with pytest.raises(ValueError, match="Invalid file type"):
                await service.upload_file(
                    file_content=file_content,
                    filename=filename,
                )

    async def test_upload_file_with_user_id(self, service):
        """Test upload creates user-specific path."""
        file_content = b"test content"
        user_id = "user-123"

        mock_file = AsyncMock()
        mock_file.write = AsyncMock()

        with patch.object(service, "_validate_file_type", return_value=True):
            with patch("app.services.storage.aiofiles") as mock_aiofiles:
                mock_aiofiles.open = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_file), __aexit__=AsyncMock()))

                result = await service.upload_file(
                    file_content=file_content,
                    filename="test.txt",
                    user_id=user_id,
                )

        assert user_id in result["path"]

    async def test_upload_file_generates_hash(self, service):
        """Test upload generates file hash."""
        file_content = b"test content"

        mock_file = AsyncMock()
        mock_file.write = AsyncMock()

        with patch.object(service, "_validate_file_type", return_value=True):
            with patch("app.services.storage.aiofiles") as mock_aiofiles:
                mock_aiofiles.open = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_file), __aexit__=AsyncMock()))

                result = await service.upload_file(
                    file_content=file_content,
                    filename="test.txt",
                )

        assert "hash" in result
        assert len(result["hash"]) == 64  # SHA256 hex length


class TestStorageServiceLocalDelete:
    """Test local file deletion functionality."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    async def test_delete_file_local_success(self, service):
        """Test successful local file deletion."""
        with patch("os.path.exists", return_value=True):
            with patch("os.remove") as mock_remove:
                result = await service.delete_file("uploads/test.txt")

        assert result is True
        mock_remove.assert_called_once()

    async def test_delete_file_not_exists(self, service):
        """Test deletion when file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = await service.delete_file("uploads/nonexistent.txt")

        assert result is True  # Returns True even if file doesn't exist

    async def test_delete_file_error(self, service):
        """Test deletion handles errors."""
        with patch("os.path.exists", return_value=True):
            with patch("os.remove", side_effect=PermissionError("Access denied")):
                result = await service.delete_file("uploads/test.txt")

        assert result is False


class TestStorageServiceLocalGet:
    """Test local file retrieval functionality."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    async def test_get_file_local_success(self, service):
        """Test successful local file retrieval."""
        file_content = b"test content"

        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=file_content)

        with patch("os.path.exists", return_value=True):
            with patch("app.services.storage.aiofiles") as mock_aiofiles:
                mock_aiofiles.open = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_file), __aexit__=AsyncMock()))

                result = await service.get_file("uploads/test.txt")

        assert result == file_content

    async def test_get_file_not_exists(self, service):
        """Test retrieval when file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = await service.get_file("uploads/nonexistent.txt")

        assert result is None


class TestStorageServicePresignedUrl:
    """Test presigned URL generation."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    async def test_presigned_url_local_returns_none(self, service):
        """Test local storage returns None for presigned URLs."""
        result = await service.generate_presigned_url("uploads/test.txt")
        assert result is None


class TestFileTypeValidation:
    """Test file type validation."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    def test_validate_valid_jpeg(self, service):
        """Test validation of JPEG file."""
        # JPEG magic bytes
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01'

        with patch("app.services.storage.magic") as mock_magic:
            mock_mime = MagicMock()
            mock_mime.from_buffer.return_value = "image/jpeg"
            mock_magic.Magic.return_value = mock_mime

            result = service._validate_file_type(jpeg_content, "image/jpeg")

        assert result is True

    def test_validate_valid_png(self, service):
        """Test validation of PNG file."""
        # PNG magic bytes
        png_content = b'\x89PNG\r\n\x1a\n'

        with patch("app.services.storage.magic") as mock_magic:
            mock_mime = MagicMock()
            mock_mime.from_buffer.return_value = "image/png"
            mock_magic.Magic.return_value = mock_mime

            result = service._validate_file_type(png_content, "image/png")

        assert result is True

    def test_validate_invalid_type(self, service):
        """Test validation rejects invalid type."""
        executable_content = b'\x4d\x5a'  # MZ header

        with patch("app.services.storage.magic") as mock_magic:
            mock_mime = MagicMock()
            mock_mime.from_buffer.return_value = "application/x-msdownload"
            mock_magic.Magic.return_value = mock_mime

            result = service._validate_file_type(executable_content)

        assert result is False

    def test_validate_type_mismatch(self, service):
        """Test validation rejects type mismatch."""
        with patch("app.services.storage.magic") as mock_magic:
            mock_mime = MagicMock()
            mock_mime.from_buffer.return_value = "image/png"  # Actual
            mock_magic.Magic.return_value = mock_mime

            result = service._validate_file_type(b"content", "image/jpeg")  # Claimed

        assert result is False


class TestFileSizeValidation:
    """Test file size validation."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    def test_validate_size_under_limit(self, service):
        """Test file under size limit passes."""
        small_content = b"x" * (1024 * 1024)  # 1MB
        result = service._validate_file_size(small_content, max_size_mb=5)
        assert result is True

    def test_validate_size_at_limit(self, service):
        """Test file at size limit passes."""
        content = b"x" * (5 * 1024 * 1024)  # Exactly 5MB
        result = service._validate_file_size(content, max_size_mb=5)
        assert result is True

    def test_validate_size_over_limit(self, service):
        """Test file over size limit fails."""
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        result = service._validate_file_size(large_content, max_size_mb=5)
        assert result is False

    def test_validate_size_custom_limit(self, service):
        """Test custom size limit."""
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        result = service._validate_file_size(content, max_size_mb=1)
        assert result is False


class TestImageOptimization:
    """Test image optimization."""

    @pytest.fixture
    def service(self):
        """Create StorageService with local storage."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    async def test_optimize_image_success(self, service):
        """Test image optimization returns optimized content."""
        # Create a mock image
        mock_img = MagicMock()
        mock_img.mode = "RGB"
        mock_img.size = (1024, 1024)
        mock_img.thumbnail = MagicMock()
        mock_img.save = MagicMock()

        with patch("PIL.Image.open", return_value=mock_img):
            result = await service.optimize_image(b"fake image content")

        # Should return bytes
        assert isinstance(result, bytes)

    async def test_optimize_image_rgba_conversion(self, service):
        """Test RGBA to RGB conversion."""
        mock_img = MagicMock()
        mock_img.mode = "RGBA"
        mock_img.size = (512, 512)
        mock_img.split.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_img.thumbnail = MagicMock()

        mock_background = MagicMock()
        mock_background.paste = MagicMock()
        mock_background.thumbnail = MagicMock()
        mock_background.save = MagicMock()

        with patch("PIL.Image.open", return_value=mock_img):
            with patch("PIL.Image.new", return_value=mock_background):
                result = await service.optimize_image(b"rgba image content")

        assert isinstance(result, bytes)

    async def test_optimize_image_error_returns_original(self, service):
        """Test optimization error returns original content."""
        original_content = b"original content"

        with patch("PIL.Image.open", side_effect=Exception("PIL error")):
            result = await service.optimize_image(original_content)

        assert result == original_content


class TestAvatarService:
    """Test AvatarService functionality."""

    async def test_upload_avatar_success(self):
        """Test successful avatar upload."""
        user_id = "user-123"
        file_content = b"x" * 1024  # Small file
        filename = "avatar.jpg"

        with patch.object(storage_service, "_validate_file_size", return_value=True):
            with patch.object(storage_service, "_validate_file_type", return_value=True):
                with patch.object(storage_service, "optimize_image", return_value=file_content):
                    with patch.object(storage_service, "upload_file") as mock_upload:
                        mock_upload.return_value = {
                            "url": "/uploads/avatars/user-123/avatar.jpg",
                            "path": "avatars/user-123/avatar.jpg",
                        }

                        result = await AvatarService.upload_avatar(
                            user_id=user_id,
                            file_content=file_content,
                            filename=filename,
                            content_type="image/jpeg",
                        )

        assert "url" in result
        mock_upload.assert_called_once()

    async def test_upload_avatar_size_exceeded(self):
        """Test avatar upload with size exceeded."""
        user_id = "user-123"
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB

        with patch.object(storage_service, "_validate_file_size", return_value=False):
            with pytest.raises(ValueError, match="File size exceeds"):
                await AvatarService.upload_avatar(
                    user_id=user_id,
                    file_content=large_content,
                    filename="avatar.jpg",
                )

    async def test_upload_avatar_invalid_type(self):
        """Test avatar upload with invalid file type."""
        user_id = "user-123"
        file_content = b"executable content"

        with patch.object(storage_service, "_validate_file_size", return_value=True):
            with patch.object(storage_service, "_validate_file_type", return_value=False):
                with pytest.raises(ValueError, match="Invalid image file type"):
                    await AvatarService.upload_avatar(
                        user_id=user_id,
                        file_content=file_content,
                        filename="avatar.exe",
                    )

    async def test_delete_avatar_success(self):
        """Test successful avatar deletion."""
        with patch.object(storage_service, "delete_file", return_value=True) as mock_delete:
            result = await AvatarService.delete_avatar(
                user_id="user-123",
                avatar_path="avatars/user-123/avatar.jpg",
            )

        assert result is True
        mock_delete.assert_called_once_with("avatars/user-123/avatar.jpg")

    async def test_delete_avatar_error(self):
        """Test avatar deletion handles errors."""
        with patch.object(storage_service, "delete_file", side_effect=Exception("Delete error")):
            result = await AvatarService.delete_avatar(
                user_id="user-123",
                avatar_path="avatars/user-123/avatar.jpg",
            )

        assert result is False


class TestStorageServiceS3:
    """Test S3/R2 storage functionality."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client."""
        return MagicMock()

    async def test_upload_to_s3_success(self, mock_s3_client):
        """Test successful S3 upload."""
        mock_endpoint = MagicMock()
        mock_endpoint.host = "abc123.r2.cloudflarestorage.com"
        mock_s3_client._endpoint = mock_endpoint
        mock_s3_client.put_object = MagicMock()

        with patch("app.services.storage.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3_client

            with patch("app.services.storage.settings") as mock_settings:
                mock_settings.CLOUDFLARE_R2_ACCESS_KEY = "test_key"
                mock_settings.CLOUDFLARE_R2_SECRET_KEY = "test_secret"
                mock_settings.CLOUDFLARE_ACCOUNT_ID = "abc123"
                mock_settings.CLOUDFLARE_R2_BUCKET = "test-bucket"

                service = StorageService()
                service.s3_client = mock_s3_client
                service.bucket_name = "test-bucket"
                service.storage_type = "s3"

                result = await service._upload_to_s3(
                    file_content=b"test content",
                    file_path="uploads/test.txt",
                    content_type="text/plain",
                )

        assert "r2.dev" in result
        mock_s3_client.put_object.assert_called_once()

    async def test_delete_from_s3_success(self, mock_s3_client):
        """Test successful S3 deletion."""
        mock_s3_client.delete_object = MagicMock()

        with patch("app.services.storage.boto3"):
            service = StorageService()
            service.s3_client = mock_s3_client
            service.bucket_name = "test-bucket"
            service.storage_type = "s3"

            result = await service._delete_from_s3("uploads/test.txt")

        assert result is True
        mock_s3_client.delete_object.assert_called_once()

    async def test_get_from_s3_success(self, mock_s3_client):
        """Test successful S3 retrieval."""
        mock_body = MagicMock()
        mock_body.read.return_value = b"test content"
        mock_s3_client.get_object = MagicMock(return_value={"Body": mock_body})

        with patch("app.services.storage.boto3"):
            service = StorageService()
            service.s3_client = mock_s3_client
            service.bucket_name = "test-bucket"
            service.storage_type = "s3"

            result = await service._get_from_s3("uploads/test.txt")

        assert result == b"test content"

    async def test_presigned_url_s3(self, mock_s3_client):
        """Test presigned URL generation for S3."""
        mock_s3_client.generate_presigned_url = MagicMock(
            return_value="https://presigned-url.example.com"
        )

        with patch("app.services.storage.boto3"):
            service = StorageService()
            service.s3_client = mock_s3_client
            service.bucket_name = "test-bucket"
            service.storage_type = "s3"

            result = await service.generate_presigned_url("uploads/test.txt", expires_in=3600)

        assert result == "https://presigned-url.example.com"
        mock_s3_client.generate_presigned_url.assert_called_once()


class TestStorageSingleton:
    """Test storage_service singleton."""

    def test_singleton_exists(self):
        """Test storage_service singleton is available."""
        assert storage_service is not None

    def test_singleton_is_storage_service(self):
        """Test singleton is StorageService instance."""
        assert isinstance(storage_service, StorageService)


class TestServiceMethodExistence:
    """Test that required service methods exist."""

    @pytest.fixture
    def service(self):
        """Create StorageService instance."""
        with patch("app.services.storage.boto3", None):
            return StorageService()

    def test_has_upload_file(self, service):
        """Test service has upload_file method."""
        import asyncio
        assert hasattr(service, "upload_file")
        assert asyncio.iscoroutinefunction(service.upload_file)

    def test_has_delete_file(self, service):
        """Test service has delete_file method."""
        import asyncio
        assert hasattr(service, "delete_file")
        assert asyncio.iscoroutinefunction(service.delete_file)

    def test_has_get_file(self, service):
        """Test service has get_file method."""
        import asyncio
        assert hasattr(service, "get_file")
        assert asyncio.iscoroutinefunction(service.get_file)

    def test_has_generate_presigned_url(self, service):
        """Test service has generate_presigned_url method."""
        import asyncio
        assert hasattr(service, "generate_presigned_url")
        assert asyncio.iscoroutinefunction(service.generate_presigned_url)

    def test_has_validate_file_type(self, service):
        """Test service has _validate_file_type method."""
        assert hasattr(service, "_validate_file_type")
        assert callable(service._validate_file_type)

    def test_has_validate_file_size(self, service):
        """Test service has _validate_file_size method."""
        assert hasattr(service, "_validate_file_size")
        assert callable(service._validate_file_size)

    def test_has_optimize_image(self, service):
        """Test service has optimize_image method."""
        import asyncio
        assert hasattr(service, "optimize_image")
        assert asyncio.iscoroutinefunction(service.optimize_image)
