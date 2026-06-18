"""
Session store — ephemeral chat session management.

Sessions are stored in DynamoDB with a 24-hour TTL.
They are ephemeral: no cross-session memory, no PII stored beyond
the conversation turn list.
"""

import logging
import time
from datetime import datetime, timezone

from agent.models import Session, SessionMessage
from db.dynamodb_client import DynamoDBClient
from db.schemas import get_table_name

logger = logging.getLogger(__name__)

_TABLE = get_table_name("sessions")
_TTL_SECONDS = 86_400  # 24 hours


class SessionStore:
    """
    CRUD operations for chat sessions in DynamoDB.
    """

    def __init__(self, db_client: DynamoDBClient) -> None:
        self.db = db_client

    async def create_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> Session:
        """
        Create a new empty session.

        Args:
            session_id: UUID string for the session.
            user_id: Authenticated user ID, or None for anonymous.

        Returns:
            The newly created Session object.
        """
        now = datetime.now(timezone.utc).isoformat()
        ttl = int(time.time()) + _TTL_SECONDS

        item = {
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "messages": [],
            "child_age_days": None,
            "created_at": now,
            "ttl": ttl,
        }
        await self.db.put_item(_TABLE, item)
        logger.info("Created session %s (user=%s)", session_id, user_id)

        return Session(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            created_at=now,
            ttl=ttl,
        )

    async def get_session(self, session_id: str) -> Session:
        """
        Retrieve a session by ID.

        Creates a new empty session if it does not exist
        (supports resumption from frontend-generated session IDs).

        Args:
            session_id: UUID of the session.

        Returns:
            Session object (possibly freshly created).
        """
        item = await self.db.get_item(_TABLE, {"session_id": session_id})
        if not item:
            logger.info("Session %s not found — creating new.", session_id)
            return await self.create_session(session_id)

        raw_messages = item.get("messages", [])
        messages = [
            SessionMessage(role=m["role"], content=m["content"])
            for m in raw_messages
        ]
        return Session(
            session_id=item["session_id"],
            user_id=item.get("user_id"),
            messages=messages,
            child_age_days=item.get("child_age_days"),
            created_at=item.get("created_at", ""),
            ttl=item.get("ttl", 0),
        )

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Append a message to the session's conversation history.

        Args:
            session_id: UUID of the session.
            role: "user" or "assistant".
            content: Message content text.
        """
        # Fetch current, append, put back (DynamoDB list_append via update expression)
        session = await self.get_session(session_id)
        new_message = {"role": role, "content": content}
        updated_messages = [
            {"role": m.role, "content": m.content} for m in session.messages
        ] + [new_message]

        # Refresh TTL on each message so active sessions don't expire mid-conversation
        new_ttl = int(time.time()) + _TTL_SECONDS

        await self.db.update_item(
            table_name=_TABLE,
            key={"session_id": session_id},
            update_expression="SET messages = :msgs, #t = :ttl",
            expression_values={":msgs": updated_messages, ":ttl": new_ttl},
            expression_names={"#t": "ttl"},
        )

    async def get_history(self, session_id: str) -> list[SessionMessage]:
        """Return the full conversation history for a session."""
        session = await self.get_session(session_id)
        return session.messages
