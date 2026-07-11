import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .dynamodb_client import DynamoDBClient
from ..config import settings

class DocumentStore:
    def __init__(self, db_client: DynamoDBClient):
        self.db = db_client
        self.table_name = f"{settings.dynamodb_table_prefix}documents"

    async def add_document(self, doc_id: str, source_authority: str, chunk_count: int, title: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "doc_id": doc_id,
            "source_authority": source_authority,
            "chunk_count": chunk_count,
            "title": title,
            "upload_date": now,
        }
        await self.db.put_item(self.table_name, item)

    async def list_documents(self) -> list[dict]:
        # Missing pagination handling, but better than sync blocking call
        response = await self.db.scan(self.table_name)
        return response
