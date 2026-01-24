"""
Comprehensive WebSocket Manager Test Suite
Tests for real-time WebSocket connection management and message routing
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.websocket_manager import (
    ConnectionManager,
    EventType,
    manager,
)

pytestmark = pytest.mark.asyncio


class TestEventType:
    """Test EventType enum values."""

    def test_connection_value(self):
        """Test CONNECTION event type."""
        assert EventType.CONNECTION.value == "connection"

    def test_authentication_value(self):
        """Test AUTHENTICATION event type."""
        assert EventType.AUTHENTICATION.value == "authentication"

    def test_subscription_value(self):
        """Test SUBSCRIPTION event type."""
        assert EventType.SUBSCRIPTION.value == "subscription"

    def test_unsubscription_value(self):
        """Test UNSUBSCRIPTION event type."""
        assert EventType.UNSUBSCRIPTION.value == "unsubscription"

    def test_message_value(self):
        """Test MESSAGE event type."""
        assert EventType.MESSAGE.value == "message"

    def test_notification_value(self):
        """Test NOTIFICATION event type."""
        assert EventType.NOTIFICATION.value == "notification"

    def test_organization_update_value(self):
        """Test ORGANIZATION_UPDATE event type."""
        assert EventType.ORGANIZATION_UPDATE.value == "organization.update"

    def test_user_update_value(self):
        """Test USER_UPDATE event type."""
        assert EventType.USER_UPDATE.value == "user.update"

    def test_policy_evaluation_value(self):
        """Test POLICY_EVALUATION event type."""
        assert EventType.POLICY_EVALUATION.value == "policy.evaluation"

    def test_invitation_received_value(self):
        """Test INVITATION_RECEIVED event type."""
        assert EventType.INVITATION_RECEIVED.value == "invitation.received"

    def test_webhook_event_value(self):
        """Test WEBHOOK_EVENT event type."""
        assert EventType.WEBHOOK_EVENT.value == "webhook.event"

    def test_audit_event_value(self):
        """Test AUDIT_EVENT event type."""
        assert EventType.AUDIT_EVENT.value == "audit.event"

    def test_error_value(self):
        """Test ERROR event type."""
        assert EventType.ERROR.value == "error"

    def test_ping_value(self):
        """Test PING event type."""
        assert EventType.PING.value == "ping"

    def test_pong_value(self):
        """Test PONG event type."""
        assert EventType.PONG.value == "pong"

    def test_event_type_is_string_enum(self):
        """Test EventType inherits from str."""
        assert isinstance(EventType.CONNECTION, str)
        assert EventType.CONNECTION == "connection"


class TestConnectionManagerInitialization:
    """Test ConnectionManager initialization."""

    def test_initialization(self):
        """Test manager initializes with empty state."""
        cm = ConnectionManager()

        assert cm.active_connections == {}
        assert cm.user_connections == {}
        assert cm.organization_subscribers == {}
        assert cm.topic_subscribers == {}
        assert cm._connection_counter == 0
        assert cm.background_tasks == set()

    def test_initialization_has_cache(self):
        """Test manager initializes with cache service."""
        cm = ConnectionManager()
        assert cm.cache is not None

    def test_global_manager_exists(self):
        """Test global manager instance exists."""
        assert manager is not None
        assert isinstance(manager, ConnectionManager)


class TestConnect:
    """Test WebSocket connect method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_connect_accepts_websocket(self, connection_manager, mock_websocket):
        """Test connect accepts the WebSocket."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            await connection_manager.connect(mock_websocket)

        mock_websocket.accept.assert_called_once()

    async def test_connect_returns_connection_id(self, connection_manager, mock_websocket):
        """Test connect returns a connection ID."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        assert connection_id is not None
        assert connection_id.startswith("conn_")

    async def test_connect_stores_connection(self, connection_manager, mock_websocket):
        """Test connect stores connection info."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        assert connection_id in connection_manager.active_connections
        connection = connection_manager.active_connections[connection_id]
        assert connection["websocket"] is mock_websocket
        assert connection["authenticated"] is False
        assert connection["subscriptions"] == set()

    async def test_connect_with_user_id(self, connection_manager, mock_websocket):
        """Test connect with user_id sets authenticated."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        connection = connection_manager.active_connections[connection_id]
        assert connection["authenticated"] is True
        assert connection["user_id"] == "user-123"
        assert "user-123" in connection_manager.user_connections
        assert connection_id in connection_manager.user_connections["user-123"]

    async def test_connect_sends_confirmation(self, connection_manager, mock_websocket):
        """Test connect sends confirmation message."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            await connection_manager.connect(mock_websocket)

        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == EventType.CONNECTION
        assert call_args["data"]["status"] == "connected"

    async def test_connect_increments_counter(self, connection_manager, mock_websocket):
        """Test connect increments connection counter."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            assert connection_manager._connection_counter == 0
            await connection_manager.connect(mock_websocket)
            assert connection_manager._connection_counter == 1
            await connection_manager.connect(mock_websocket)
            assert connection_manager._connection_counter == 2


class TestDisconnect:
    """Test WebSocket disconnect method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_disconnect_removes_connection(self, connection_manager, mock_websocket):
        """Test disconnect removes connection from active_connections."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)
            assert connection_id in connection_manager.active_connections

            await connection_manager.disconnect(connection_id)
            assert connection_id not in connection_manager.active_connections

    async def test_disconnect_removes_from_user_connections(self, connection_manager, mock_websocket):
        """Test disconnect removes connection from user_connections."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            assert "user-123" in connection_manager.user_connections

            await connection_manager.disconnect(connection_id)
            assert "user-123" not in connection_manager.user_connections

    async def test_disconnect_closes_websocket(self, connection_manager, mock_websocket):
        """Test disconnect closes the WebSocket."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)
            await connection_manager.disconnect(connection_id)

        mock_websocket.close.assert_called_once()

    async def test_disconnect_nonexistent_connection(self, connection_manager):
        """Test disconnect with nonexistent connection ID."""
        # Should not raise
        await connection_manager.disconnect("nonexistent-connection")

    async def test_disconnect_removes_from_organization_subscribers(self, connection_manager, mock_websocket):
        """Test disconnect removes from organization subscriptions."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

            # Add to organization subscribers
            connection_manager.organization_subscribers["org-1"] = {connection_id}

            await connection_manager.disconnect(connection_id)
            assert "org-1" not in connection_manager.organization_subscribers

    async def test_disconnect_removes_from_topic_subscribers(self, connection_manager, mock_websocket):
        """Test disconnect removes from topic subscriptions."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

            # Add to topic subscribers
            connection_manager.topic_subscribers["notifications"] = {connection_id}

            await connection_manager.disconnect(connection_id)
            assert "notifications" not in connection_manager.topic_subscribers


class TestAuthenticate:
    """Test WebSocket authenticate method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_authenticate_nonexistent_connection(self, connection_manager):
        """Test authenticate with nonexistent connection returns False."""
        result = await connection_manager.authenticate("nonexistent", "token", MagicMock())
        assert result is False

    async def test_authenticate_invalid_token(self, connection_manager, mock_websocket):
        """Test authenticate with invalid token returns False."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        mock_db = MagicMock()
        with patch("app.services.websocket_manager.AuthService") as MockAuthService:
            mock_auth = AsyncMock()
            mock_auth.verify_token = AsyncMock(return_value=None)
            MockAuthService.return_value = mock_auth

            result = await connection_manager.authenticate(connection_id, "invalid-token", mock_db)

        assert result is False
        # Check that failure message was sent
        calls = mock_websocket.send_json.call_args_list
        auth_failed_sent = any(
            call[0][0].get("type") == EventType.AUTHENTICATION and
            call[0][0].get("data", {}).get("status") == "failed"
            for call in calls
        )
        assert auth_failed_sent

    async def test_authenticate_valid_token(self, connection_manager, mock_websocket):
        """Test authenticate with valid token returns True."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-456"
        mock_user.email = "test@example.com"
        mock_user.tenant_id = "tenant-789"

        with patch("app.services.websocket_manager.AuthService") as MockAuthService:
            mock_auth = AsyncMock()
            mock_auth.verify_token = AsyncMock(return_value=mock_user)
            MockAuthService.return_value = mock_auth

            result = await connection_manager.authenticate(connection_id, "valid-token", mock_db)

        assert result is True
        connection = connection_manager.active_connections[connection_id]
        assert connection["authenticated"] is True
        assert connection["user_id"] == "user-456"
        assert connection["user_email"] == "test@example.com"

    async def test_authenticate_updates_user_connections(self, connection_manager, mock_websocket):
        """Test authenticate adds connection to user_connections."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-456"
        mock_user.email = "test@example.com"
        mock_user.tenant_id = "tenant-789"

        with patch("app.services.websocket_manager.AuthService") as MockAuthService:
            mock_auth = AsyncMock()
            mock_auth.verify_token = AsyncMock(return_value=mock_user)
            MockAuthService.return_value = mock_auth

            await connection_manager.authenticate(connection_id, "valid-token", mock_db)

        assert "user-456" in connection_manager.user_connections
        assert connection_id in connection_manager.user_connections["user-456"]


class TestSubscribe:
    """Test WebSocket subscribe method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_subscribe_nonexistent_connection(self, connection_manager):
        """Test subscribe with nonexistent connection returns False."""
        result = await connection_manager.subscribe("nonexistent", "organization", "org-1")
        assert result is False

    async def test_subscribe_unauthenticated(self, connection_manager, mock_websocket):
        """Test subscribe without authentication returns False."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        result = await connection_manager.subscribe(connection_id, "organization", "org-1")
        assert result is False

    async def test_subscribe_organization_success(self, connection_manager, mock_websocket):
        """Test subscribe to organization succeeds."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        result = await connection_manager.subscribe(connection_id, "organization", "org-1")
        assert result is True
        assert "org-1" in connection_manager.organization_subscribers
        assert connection_id in connection_manager.organization_subscribers["org-1"]

    async def test_subscribe_topic_success(self, connection_manager, mock_websocket):
        """Test subscribe to topic succeeds."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        result = await connection_manager.subscribe(connection_id, "topic", "notifications")
        assert result is True
        assert "notifications" in connection_manager.topic_subscribers
        assert connection_id in connection_manager.topic_subscribers["notifications"]

    async def test_subscribe_unknown_type(self, connection_manager, mock_websocket):
        """Test subscribe with unknown type returns False."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        result = await connection_manager.subscribe(connection_id, "unknown", "target-1")
        assert result is False

    async def test_subscribe_sends_confirmation(self, connection_manager, mock_websocket):
        """Test subscribe sends confirmation message."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        await connection_manager.subscribe(connection_id, "organization", "org-1")

        calls = mock_websocket.send_json.call_args_list
        subscription_sent = any(
            call[0][0].get("type") == EventType.SUBSCRIPTION and
            call[0][0].get("data", {}).get("status") == "subscribed"
            for call in calls
        )
        assert subscription_sent


class TestUnsubscribe:
    """Test WebSocket unsubscribe method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_unsubscribe_nonexistent_connection(self, connection_manager):
        """Test unsubscribe with nonexistent connection returns False."""
        result = await connection_manager.unsubscribe("nonexistent", "organization", "org-1")
        assert result is False

    async def test_unsubscribe_organization(self, connection_manager, mock_websocket):
        """Test unsubscribe from organization."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "organization", "org-1")

        result = await connection_manager.unsubscribe(connection_id, "organization", "org-1")
        assert result is True

    async def test_unsubscribe_topic(self, connection_manager, mock_websocket):
        """Test unsubscribe from topic."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "topic", "notifications")

        result = await connection_manager.unsubscribe(connection_id, "topic", "notifications")
        assert result is True

    async def test_unsubscribe_sends_confirmation(self, connection_manager, mock_websocket):
        """Test unsubscribe sends confirmation message."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "organization", "org-1")

        await connection_manager.unsubscribe(connection_id, "organization", "org-1")

        calls = mock_websocket.send_json.call_args_list
        unsubscription_sent = any(
            call[0][0].get("type") == EventType.UNSUBSCRIPTION and
            call[0][0].get("data", {}).get("status") == "unsubscribed"
            for call in calls
        )
        assert unsubscription_sent


class TestSendToConnection:
    """Test send_to_connection method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_send_to_nonexistent_connection(self, connection_manager):
        """Test send to nonexistent connection does nothing."""
        # Should not raise
        await connection_manager.send_to_connection("nonexistent", {"test": "message"})

    async def test_send_to_connection_success(self, connection_manager, mock_websocket):
        """Test send to connection calls send_json."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)
            mock_websocket.send_json.reset_mock()

        await connection_manager.send_to_connection(connection_id, {"test": "message"})
        mock_websocket.send_json.assert_called_with({"test": "message"})

    async def test_send_to_connection_error_disconnects(self, connection_manager, mock_websocket):
        """Test send error disconnects the connection."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        # Make send_json raise an exception
        mock_websocket.send_json.side_effect = Exception("Send failed")

        await connection_manager.send_to_connection(connection_id, {"test": "message"})
        assert connection_id not in connection_manager.active_connections


class TestSendToUser:
    """Test send_to_user method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_send_to_nonexistent_user(self, connection_manager):
        """Test send to nonexistent user does nothing."""
        # Should not raise
        await connection_manager.send_to_user("nonexistent-user", {"test": "message"})

    async def test_send_to_user_success(self, connection_manager, mock_websocket):
        """Test send to user sends to all user connections."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            mock_websocket.send_json.reset_mock()

        await connection_manager.send_to_user("user-123", {"test": "message"})
        mock_websocket.send_json.assert_called_with({"test": "message"})


class TestBroadcastToOrganization:
    """Test broadcast_to_organization method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_broadcast_to_nonexistent_organization(self, connection_manager):
        """Test broadcast to nonexistent organization does nothing."""
        # Should not raise
        await connection_manager.broadcast_to_organization("nonexistent-org", {"test": "message"})

    async def test_broadcast_to_organization_success(self, connection_manager, mock_websocket):
        """Test broadcast to organization sends to all subscribers."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "organization", "org-1")
            mock_websocket.send_json.reset_mock()

        await connection_manager.broadcast_to_organization("org-1", {"test": "message"})
        mock_websocket.send_json.assert_called_with({"test": "message"})

    async def test_broadcast_excludes_connection(self, connection_manager, mock_websocket):
        """Test broadcast can exclude a connection."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "organization", "org-1")
            mock_websocket.send_json.reset_mock()

        await connection_manager.broadcast_to_organization(
            "org-1", {"test": "message"}, exclude_connection=connection_id
        )
        # Should not have received the message due to exclusion
        assert mock_websocket.send_json.call_count == 0


class TestBroadcastToTopic:
    """Test broadcast_to_topic method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_broadcast_to_nonexistent_topic(self, connection_manager):
        """Test broadcast to nonexistent topic does nothing."""
        # Should not raise
        await connection_manager.broadcast_to_topic("nonexistent-topic", {"test": "message"})

    async def test_broadcast_to_topic_success(self, connection_manager, mock_websocket):
        """Test broadcast to topic sends to all subscribers."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "topic", "notifications")
            mock_websocket.send_json.reset_mock()

        await connection_manager.broadcast_to_topic("notifications", {"test": "message"})
        mock_websocket.send_json.assert_called_with({"test": "message"})


class TestBroadcastToAll:
    """Test broadcast_to_all method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_broadcast_to_all_authenticated_only(self, connection_manager, mock_websocket):
        """Test broadcast to all only reaches authenticated connections."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            # Unauthenticated connection
            await connection_manager.connect(mock_websocket)
            mock_websocket.send_json.reset_mock()

        await connection_manager.broadcast_to_all({"test": "message"}, authenticated_only=True)
        # Should not have received message as not authenticated
        assert mock_websocket.send_json.call_count == 0

    async def test_broadcast_to_all_includes_unauthenticated(self, connection_manager, mock_websocket):
        """Test broadcast to all can include unauthenticated."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            await connection_manager.connect(mock_websocket)
            mock_websocket.send_json.reset_mock()

        await connection_manager.broadcast_to_all({"test": "message"}, authenticated_only=False)
        mock_websocket.send_json.assert_called_with({"test": "message"})


class TestHandleMessage:
    """Test handle_message method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_handle_ping_message(self, connection_manager, mock_websocket):
        """Test handle_message responds to ping with pong."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)
            mock_websocket.send_json.reset_mock()

        await connection_manager.handle_message(
            connection_id, {"type": EventType.PING}, MagicMock()
        )

        # Check pong was sent
        calls = mock_websocket.send_json.call_args_list
        pong_sent = any(call[0][0].get("type") == EventType.PONG for call in calls)
        assert pong_sent

    async def test_handle_authentication_message(self, connection_manager, mock_websocket):
        """Test handle_message processes authentication."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)

        mock_db = MagicMock()
        with patch("app.services.websocket_manager.AuthService") as MockAuthService:
            mock_auth = AsyncMock()
            mock_auth.verify_token = AsyncMock(return_value=None)
            MockAuthService.return_value = mock_auth

            await connection_manager.handle_message(
                connection_id,
                {"type": EventType.AUTHENTICATION, "data": {"token": "test-token"}},
                mock_db,
            )

        MockAuthService.assert_called_with(mock_db)

    async def test_handle_subscription_message(self, connection_manager, mock_websocket):
        """Test handle_message processes subscription."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        await connection_manager.handle_message(
            connection_id,
            {
                "type": EventType.SUBSCRIPTION,
                "data": {"subscription_type": "organization", "target_id": "org-1"},
            },
            MagicMock(),
        )

        assert "org-1" in connection_manager.organization_subscribers

    async def test_handle_unsubscription_message(self, connection_manager, mock_websocket):
        """Test handle_message processes unsubscription."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "organization", "org-1")

        await connection_manager.handle_message(
            connection_id,
            {
                "type": EventType.UNSUBSCRIPTION,
                "data": {"subscription_type": "organization", "target_id": "org-1"},
            },
            MagicMock(),
        )

        # Connection should be removed from org subscribers
        connection = connection_manager.active_connections[connection_id]
        assert "org:org-1" not in connection["subscriptions"]

    async def test_handle_unknown_message_type(self, connection_manager, mock_websocket):
        """Test handle_message sends error for unknown type."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)
            mock_websocket.send_json.reset_mock()

        await connection_manager.handle_message(
            connection_id, {"type": "unknown_type"}, MagicMock()
        )

        calls = mock_websocket.send_json.call_args_list
        error_sent = any(
            call[0][0].get("type") == EventType.ERROR and
            "Unknown message type" in call[0][0].get("data", {}).get("error", "")
            for call in calls
        )
        assert error_sent


class TestHandleCustomMessage:
    """Test _handle_custom_message method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    async def test_handle_custom_message_unauthenticated(self, connection_manager, mock_websocket):
        """Test custom message requires authentication."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket)
            mock_websocket.send_json.reset_mock()

        await connection_manager._handle_custom_message(
            connection_id, {"message": "test"}, MagicMock()
        )

        calls = mock_websocket.send_json.call_args_list
        error_sent = any(
            call[0][0].get("type") == EventType.ERROR and
            "Authentication required" in call[0][0].get("data", {}).get("error", "")
            for call in calls
        )
        assert error_sent


class TestGetConnectionInfo:
    """Test get_connection_info method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    def test_get_info_nonexistent_connection(self, connection_manager):
        """Test get_connection_info for nonexistent connection returns None."""
        result = connection_manager.get_connection_info("nonexistent")
        assert result is None

    async def test_get_info_success(self, connection_manager, mock_websocket):
        """Test get_connection_info returns connection details."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")

        info = connection_manager.get_connection_info(connection_id)

        assert info is not None
        assert info["connection_id"] == connection_id
        assert info["user_id"] == "user-123"
        assert info["authenticated"] is True
        assert isinstance(info["subscriptions"], list)
        assert info["connected_at"] is not None


class TestGetStats:
    """Test get_stats method."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    def test_get_stats_empty(self, connection_manager):
        """Test get_stats with no connections."""
        stats = connection_manager.get_stats()

        assert stats["total_connections"] == 0
        assert stats["authenticated_connections"] == 0
        assert stats["unique_users"] == 0
        assert stats["organization_topics"] == 0
        assert stats["custom_topics"] == 0
        assert stats["total_subscriptions"] == 0

    async def test_get_stats_with_connections(self, connection_manager, mock_websocket):
        """Test get_stats with active connections."""
        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            mock_task.return_value.add_done_callback = MagicMock()

            # Create authenticated connection
            connection_id = await connection_manager.connect(mock_websocket, user_id="user-123")
            await connection_manager.subscribe(connection_id, "organization", "org-1")

        stats = connection_manager.get_stats()

        assert stats["total_connections"] == 1
        assert stats["authenticated_connections"] == 1
        assert stats["unique_users"] == 1
        assert stats["organization_topics"] == 1
        assert stats["total_subscriptions"] == 1


class TestServiceMethodExistence:
    """Test service method existence and signatures."""

    @pytest.fixture
    def connection_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    def test_has_connect(self, connection_manager):
        """Test manager has connect method."""
        assert hasattr(connection_manager, "connect")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.connect)

    def test_has_disconnect(self, connection_manager):
        """Test manager has disconnect method."""
        assert hasattr(connection_manager, "disconnect")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.disconnect)

    def test_has_authenticate(self, connection_manager):
        """Test manager has authenticate method."""
        assert hasattr(connection_manager, "authenticate")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.authenticate)

    def test_has_subscribe(self, connection_manager):
        """Test manager has subscribe method."""
        assert hasattr(connection_manager, "subscribe")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.subscribe)

    def test_has_unsubscribe(self, connection_manager):
        """Test manager has unsubscribe method."""
        assert hasattr(connection_manager, "unsubscribe")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.unsubscribe)

    def test_has_send_to_connection(self, connection_manager):
        """Test manager has send_to_connection method."""
        assert hasattr(connection_manager, "send_to_connection")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.send_to_connection)

    def test_has_send_to_user(self, connection_manager):
        """Test manager has send_to_user method."""
        assert hasattr(connection_manager, "send_to_user")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.send_to_user)

    def test_has_broadcast_to_organization(self, connection_manager):
        """Test manager has broadcast_to_organization method."""
        assert hasattr(connection_manager, "broadcast_to_organization")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.broadcast_to_organization)

    def test_has_broadcast_to_topic(self, connection_manager):
        """Test manager has broadcast_to_topic method."""
        assert hasattr(connection_manager, "broadcast_to_topic")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.broadcast_to_topic)

    def test_has_broadcast_to_all(self, connection_manager):
        """Test manager has broadcast_to_all method."""
        assert hasattr(connection_manager, "broadcast_to_all")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.broadcast_to_all)

    def test_has_handle_message(self, connection_manager):
        """Test manager has handle_message method."""
        assert hasattr(connection_manager, "handle_message")
        import asyncio
        assert asyncio.iscoroutinefunction(connection_manager.handle_message)

    def test_has_get_connection_info(self, connection_manager):
        """Test manager has get_connection_info method."""
        assert hasattr(connection_manager, "get_connection_info")
        assert callable(connection_manager.get_connection_info)

    def test_has_get_stats(self, connection_manager):
        """Test manager has get_stats method."""
        assert hasattr(connection_manager, "get_stats")
        assert callable(connection_manager.get_stats)
