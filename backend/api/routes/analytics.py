from fastapi import APIRouter, Depends
from typing import Optional

from ..middleware.auth_middleware import get_current_user
from ...db.analytics_store import AnalyticsStore
from ...db.document_store import DocumentStore
from ...db.dynamodb_client import dynamodb_manager

router = APIRouter()
analytics_store = AnalyticsStore(dynamodb_manager)
document_store = DocumentStore(dynamodb_manager)

@router.get("/summary")
async def get_summary(days: int = 7, user: dict = Depends(get_current_user)):
    # In a real system, you'd check user['isAdmin'] here.
    return await analytics_store.get_analytics_summary(days)

@router.get("/documents")
def get_documents(user: dict = Depends(get_current_user)):
    return document_store.list_documents()
