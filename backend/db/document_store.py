import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .dynamodb_client import DynamoDBClient
from config import settings

class DocumentStore:
    def __init__(self, dynamodb_manager: DynamoDBClient):
        self.db = dynamodb_manager
        self.table_name = f"{settings.dynamodb_table_prefix}documents"

    def add_document(self, filename: str, source_authority: str, chunk_count: int, qdrant_ids: List[str]) -> str:
        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        item = {
            "doc_id": doc_id,
            "filename": filename,
            "source_authority": source_authority,
            "upload_date": now,
            "chunk_count": chunk_count,
            "status": "complete",
            "qdrant_ids": qdrant_ids
        }
        
        table = self.db.get_table(self.table_name)
        table.put_item(Item=item)
        return doc_id

    def list_documents(self) -> List[Dict[str, Any]]:
        table = self.db.get_table(self.table_name)
        response = table.scan()
        return response.get('Items', [])
