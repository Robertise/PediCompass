import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.models import Session, SessionMessage


@pytest.mark.asyncio
async def test_session_ownership_get_history_authorization():
    """Verify get_history restricts access to session owner or admin."""
    from api.routes.chat import get_history

    # Mock session owned by user_a
    mock_session_a = Session(
        session_id="sess_123",
        user_id="user_a",
        messages=[SessionMessage(role="user", content="Hello")],
        created_at="2026-07-23T00:00:00Z",
        ttl=1700000000,
    )

    with patch("api.routes.chat.session_store.get_session", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_session_a

        # 1. Owner user_a accesses -> 200 OK
        user_a = {"user_id": "user_a", "email": "a@test.com", "isAdmin": False}
        res_a = await get_history("sess_123", user=user_a)
        assert len(res_a["messages"]) == 1

        # 2. Admin user_admin accesses -> 200 OK
        user_admin = {"user_id": "admin_x", "email": "admin@test.com", "isAdmin": True}
        res_admin = await get_history("sess_123", user=user_admin)
        assert len(res_admin["messages"]) == 1

        # 3. Non-owner user_b accesses -> 403 Forbidden
        user_b = {"user_id": "user_b", "email": "b@test.com", "isAdmin": False}
        with pytest.raises(HTTPException) as exc_info:
            await get_history("sess_123", user=user_b)
        assert exc_info.value.status_code == 403
        assert "You do not own this chat session" in exc_info.value.detail

        # 4. Unauthenticated user (None) accesses -> 403 Forbidden
        with pytest.raises(HTTPException) as exc_info_anon:
            await get_history("sess_123", user=None)
        assert exc_info_anon.value.status_code == 403
        assert "You do not own this chat session" in exc_info_anon.value.detail


@pytest.mark.asyncio
async def test_session_ownership_anonymous_session_accessible():
    """Verify anonymous sessions can be accessed by any user."""
    from api.routes.chat import get_history

    mock_anon_session = Session(
        session_id="sess_anon",
        user_id="anonymous",
        messages=[SessionMessage(role="user", content="Hi")],
        created_at="2026-07-23T00:00:00Z",
        ttl=1700000000,
    )

    with patch("api.routes.chat.session_store.get_session", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_anon_session

        # Anonymous caller -> allowed
        res1 = await get_history("sess_anon", user=None)
        assert len(res1["messages"]) == 1

        # Authenticated user_b caller -> allowed
        user_b = {"user_id": "user_b", "email": "b@test.com", "isAdmin": False}
        res2 = await get_history("sess_anon", user=user_b)
        assert len(res2["messages"]) == 1


@pytest.mark.asyncio
async def test_send_message_ownership_authorization():
    """Verify send_message rejects requests targeting another user's session."""
    from api.routes.chat import send_message, MessageRequest

    mock_session_a = Session(
        session_id="sess_456",
        user_id="user_a",
        messages=[],
        created_at="2026-07-23T00:00:00Z",
        ttl=1700000000,
    )

    req = MessageRequest(session_id="sess_456", message="Testing message injection")
    user_b = {"user_id": "user_b", "email": "b@test.com", "isAdmin": False}

    with patch("api.routes.chat.session_store.get_session", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_session_a

        with pytest.raises(HTTPException) as exc_info:
            await send_message(req, user=user_b)
        assert exc_info.value.status_code == 403
        assert "Cannot send messages to a session owned by another user" in exc_info.value.detail
