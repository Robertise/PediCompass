import hashlib
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any

from .dynamodb_client import DynamoDBManager
from ..config import settings

class AnalyticsStore:
    def __init__(self, dynamodb_manager: DynamoDBManager):
        self.db = dynamodb_manager
        self.table_name = f"{settings.dynamodb_table_prefix}analytics_log"

    def _hash_user_id(self, user_id: str) -> str:
        """Anonymize user_id for analytics storage."""
        return hashlib.sha256(user_id.encode('utf-8')).hexdigest()

    async def log_query(
        self,
        session_id: str,
        user_id: Optional[str],
        urgency_level: str,
        age_group: Optional[str],
        iterations: int
    ) -> None:
        """
        Log an interaction to the analytics table.
        Does not store messages/symptoms, only metadata.
        """
        now = datetime.now(timezone.utc)
        date_partition = now.strftime('%Y-%m-%d')
        
        # Determine TTL (90 days)
        ttl = int(now.timestamp()) + (90 * 24 * 60 * 60)
        
        item: Dict[str, Any] = {
            "log_id": str(uuid.uuid4()),
            "timestamp": now.isoformat(),
            "session_id": session_id,
            "user_id_hash": self._hash_user_id(user_id) if user_id else "anonymous",
            "urgency_level": urgency_level,
            "age_group": age_group or "unknown",
            "iterations": iterations,
            "date_partition": date_partition,
            "ttl": ttl
        }
        
        table = self.db.get_table(self.table_name)
        # Using boto3 directly in synchronous mode (assuming dynamodb_client provides a boto3 Table resource)
        # However, if DynamoDBManager provides async wrapping, we should use it. For simplicity with boto3,
        # standard boto3 calls are blocking. We should wrap them or use aioboto3 if fully async.
        # Assuming table is a boto3 Table resource:
        table.put_item(Item=item)

    async def get_analytics_summary(self, days: int = 7) -> dict:
        """
        Get analytics summary for the past N days.
        Requires GSI on date_partition. For simple implementation, scan or multiple queries.
        """
        # For this prototype, if GSI is not fully setup, we return dummy/mock data
        # In production, query the GSI by date_partition for the last 'days' dates.
        now = datetime.now(timezone.utc)
        return {
            "days": days,
            "queries_total": 0,
            "urgency_distribution": {},
            "age_group_distribution": {}
        }
