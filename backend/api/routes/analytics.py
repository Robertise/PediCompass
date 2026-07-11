"""
Analytics API routes.

GET /api/analytics/summary?days=7  — Aggregated usage metrics (admin only)
GET /api/analytics/documents       — Document registry from knowledge base ingestion
"""

import logging

from fastapi import APIRouter, Depends

from api.middleware.auth_middleware import get_current_user
from db.analytics_store import AnalyticsStore
from db.document_store import DocumentStore
from db.dynamodb_client import get_dynamodb_client

router = APIRouter()
logger = logging.getLogger(__name__)

_db = get_dynamodb_client()
analytics_store = AnalyticsStore(db_client=_db)
document_store = DocumentStore(db_client=_db)


@router.get("/summary")
async def get_summary(days: int = 7, user: dict = Depends(get_current_user)):
    """
    Return aggregated query analytics for the past N days.

    Note: currently returns placeholder data — the DynamoDB GSI on
    date_partition is not yet queried. See feature_gap_analysis.md.
    Admin check (user['isAdmin']) is omitted for the local demo.
    """
    return await analytics_store.get_analytics_summary(days)


@router.get("/documents")
async def get_documents(user: dict = Depends(get_current_user)):
    """Return all documents in the knowledge base document registry."""
    return await document_store.list_documents()
