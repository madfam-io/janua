"""
Tests for User model
"""

from app.models import User, UserStatus


class TestUserModel:
    """Test User model"""

    def test_user_creation_with_email(self):
        """Test user can be created with email"""
        user = User(email="test@example.com")
        assert user.email == "test@example.com"

    def test_user_creation_with_first_and_last_name(self):
        """Test user can be created with first and last name"""
        user = User(email="test@example.com", first_name="Test", last_name="User")
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        # Test the computed name property
        assert user.name == "Test User"

    def test_user_name_property_first_only(self):
        """Test name property with only first name"""
        user = User(email="test@example.com", first_name="Test")
        assert user.name == "Test"

    def test_user_name_property_last_only(self):
        """Test name property with only last name"""
        user = User(email="test@example.com", last_name="User")
        assert user.name == "User"

    def test_user_name_property_display_name_fallback(self):
        """Test name property falls back to display_name"""
        user = User(email="test@example.com", display_name="DisplayName")
        assert user.name == "DisplayName"

    def test_user_name_property_none(self):
        """Test name property returns None when no name fields set"""
        user = User(email="test@example.com")
        assert user.name is None

    def test_user_status_can_be_set(self):
        """Test user status can be explicitly set"""
        user = User(email="test@example.com", status=UserStatus.ACTIVE)
        assert user.status == UserStatus.ACTIVE

        user2 = User(email="test2@example.com", status=UserStatus.SUSPENDED)
        assert user2.status == UserStatus.SUSPENDED

    def test_user_is_active_can_be_set(self):
        """Test user is_active can be explicitly set"""
        user = User(email="test@example.com", is_active=True)
        assert user.is_active is True

        user2 = User(email="test2@example.com", is_active=False)
        assert user2.is_active is False

    def test_user_mfa_enabled_can_be_set(self):
        """Test user MFA can be explicitly enabled"""
        user = User(email="test@example.com", mfa_enabled=False)
        assert user.mfa_enabled is False

        user2 = User(email="test2@example.com", mfa_enabled=True)
        assert user2.mfa_enabled is True

    def test_user_email_verified_can_be_set(self):
        """Test user email_verified can be explicitly set"""
        user = User(email="test@example.com", email_verified=False)
        assert user.email_verified is False

        user2 = User(email="test2@example.com", email_verified=True)
        assert user2.email_verified is True

    def test_user_is_admin_can_be_set(self):
        """Test user is_admin can be explicitly set"""
        user = User(email="test@example.com", is_admin=False)
        assert user.is_admin is False

        user2 = User(email="admin@example.com", is_admin=True)
        assert user2.is_admin is True

    def test_user_with_all_profile_fields(self):
        """Test user with all profile fields"""
        user = User(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            username="testuser",
            phone="+1234567890",
            bio="Test bio",
            timezone="America/New_York",
            locale="en-US",
        )
        assert user.username == "testuser"
        assert user.phone == "+1234567890"
        assert user.bio == "Test bio"
        assert user.timezone == "America/New_York"
        assert user.locale == "en-US"

    def test_user_status_enum_values(self):
        """Test UserStatus enum has expected values"""
        assert UserStatus.ACTIVE == "active"
        assert UserStatus.INACTIVE == "inactive"
        assert UserStatus.SUSPENDED == "suspended"
        assert UserStatus.PENDING == "pending"
        assert UserStatus.DELETED == "deleted"
