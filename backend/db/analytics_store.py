import hashlib
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any

from db.dynamodb_client import DynamoDBClient
from config import settings

class AnalyticsStore:
    def __init__(self, db_client: DynamoDBClient):
        self.db = db_client
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
        iterations: int,
        intent_type: str = "triage",
        symptoms: Optional[str] = None
    ) -> None:
        """
        Log an interaction to the analytics table.
        Stores metadata and symptom summary for analytics.
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
            "intent_type": intent_type,
            "date_partition": date_partition,
            "ttl": ttl
        }
        if symptoms:
            item["symptoms"] = symptoms
        
        await self.db.put_item(self.table_name, item)

    async def get_analytics_summary(self, days: int = 7) -> dict:
        """
        Get analytics summary for the past N days.
        Queries the GSI by date_partition for the last 'days' dates in parallel.
        """
        from boto3.dynamodb.conditions import Key
        from datetime import timedelta
        import asyncio
        from collections import defaultdict
        
        now = datetime.now(timezone.utc)
        date_strings = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        
        # Query all N dates in parallel
        tasks = [
            self.db.query(
                table_name=self.table_name,
                key_condition_expression=Key("date_partition").eq(d),
                index_name="date_partition-index"
            )
            for d in date_strings
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Aggregate the results
        queries_total = 0
        urgency_dist = defaultdict(int)
        age_group_dist = defaultdict(int)
        intent_dist = defaultdict(int)
        symptom_dist = defaultdict(int)
        
        import re
        stop_words = {
            "and", "the", "a", "an", "has", "is", "with", "of", "in", "to", "for", "on", "my", "child",
            "he", "she", "it", "they", "been", "having", "some", "very", "but", "not", "about", "information",
            "definition", "approximately", "approx", "hours", "hour", "day", "days", "week", "weeks", "month",
            "months", "year", "years", "old", "age", "mild", "severe", "moderate", "tylenol", "ibuprofen",
            "paracetamol", "advil", "motrin", "medication", "medicine", "drug", "dose", "dosage", "giving",
            "give", "given", "take", "taking", "taken", "can", "what", "how", "when", "where", "why", "who",
            "does", "do", "did", "please", "help", "know", "want", "like", "need", "should", "would", "could",
            "treatment", "management", "use", "using", "used", "patient", "kid", "kids", "baby", "infant",
            "toddler", "preschool", "boy", "girl", "son", "daughter", "since", "yesterday", "today"
        }
        
        for items in results:
            for item in items:
                queries_total += 1
                if "urgency_level" in item:
                    urgency_dist[item["urgency_level"]] += 1
                if "age_group" in item:
                    age_group_dist[item["age_group"]] += 1
                if "intent_type" in item:
                    intent_dist[item["intent_type"]] += 1
                if "symptoms" in item and item["symptoms"]:
                    words = re.findall(r'\b[a-z]{3,}\b', item["symptoms"].lower())
                    for w in words:
                        if w not in stop_words:
                            symptom_dist[w] += 1
                            
        top_symptoms = dict(sorted(symptom_dist.items(), key=lambda x: x[1], reverse=True)[:10])
                    
        return {
            "days": days,
            "queries_total": queries_total,
            "urgency_distribution": dict(urgency_dist),
            "age_group_distribution": dict(age_group_dist),
            "intent_distribution": dict(intent_dist),
            "top_symptoms": top_symptoms
        }
