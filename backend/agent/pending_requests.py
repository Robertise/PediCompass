"""
PendingRequestStore — in-memory dict mapping request_id → pending message payload.

Design notes:
  - Single EC2 instance deployment: in-memory is safe (no horizontal scaling).
  - TTL 60s: client must open EventSource within 60s of registering.
  - Cleanup runs on every access to keep memory bounded.
  - NOT suitable for multi-instance deployments (would need Redis/DynamoDB).
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class PendingRequest:
    session_id:    str
    message:       str
    profile_id:    Optional[str]
    user_id:       Optional[str]
    created_at:    float    # time.monotonic()


class PendingRequestStore:
    TTL_SECONDS = 60

    def __init__(self) -> None:
        self._store: dict[str, PendingRequest] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        session_id: str,
        message: str,
        profile_id: Optional[str],
        user_id: Optional[str],
    ) -> str:
        """Store message payload and return a one-time request_id (UUID4)."""
        async with self._lock:
            self._cleanup()
            request_id = str(uuid.uuid4())
            self._store[request_id] = PendingRequest(
                session_id=session_id,
                message=message,
                profile_id=profile_id,
                user_id=user_id,
                created_at=time.monotonic(),
            )
            return request_id

    async def consume(self, request_id: str) -> Optional[PendingRequest]:
        """Retrieve and delete a pending request (one-time use)."""
        async with self._lock:
            self._cleanup()
            return self._store.pop(request_id, None)

    def _cleanup(self) -> None:
        """Remove expired entries. Called on every access."""
        now = time.monotonic()
        expired = [
            k for k, v in self._store.items()
            if now - v.created_at > self.TTL_SECONDS
        ]
        for k in expired:
            del self._store[k]


# Module-level singleton — shared between register and stream routes
pending_requests = PendingRequestStore()
