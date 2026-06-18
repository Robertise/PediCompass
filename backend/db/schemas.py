"""
DynamoDB table schemas for PediCompass.

Four tables:
  1. pedicompass_sessions       — Ephemeral, TTL 24h
  2. pedicompass_profiles       — Persistent, no TTL
  3. pedicompass_analytics_log  — TTL 90 days, GSI on date_partition
  4. pedicompass_documents      — Document registry, persistent

This module defines the boto3 create_table kwargs for each table.
Used by DynamoDBClient.ensure_tables_exist() on startup.
"""

from config import settings

_PREFIX = settings.dynamodb_table_prefix  # default: "pedicompass_"


def _table(suffix: str) -> str:
    return f"{_PREFIX}{suffix}"


TABLE_SCHEMAS: list[dict] = [
    # ── Sessions — TTL 24 hours ───────────────────────────────────────────────
    {
        "TableName": _table("sessions"),
        "KeySchema": [
            {"AttributeName": "session_id", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "session_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        # TTL attribute name (DynamoDB enables TTL separately via update_time_to_live)
        "_ttl_attribute": "ttl",
    },

    # ── Profiles — Persistent, no TTL ─────────────────────────────────────────
    {
        "TableName": _table("profiles"),
        "KeySchema": [
            {"AttributeName": "user_id",    "KeyType": "HASH"},
            {"AttributeName": "profile_id", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "user_id",    "AttributeType": "S"},
            {"AttributeName": "profile_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "_ttl_attribute": None,
    },

    # ── Analytics Log — TTL 90 days, GSI on date_partition ───────────────────
    {
        "TableName": _table("analytics_log"),
        "KeySchema": [
            {"AttributeName": "log_id",    "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "log_id",         "AttributeType": "S"},
            {"AttributeName": "timestamp",      "AttributeType": "S"},
            {"AttributeName": "date_partition", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "date_partition-index",
                "KeySchema": [
                    {"AttributeName": "date_partition", "KeyType": "HASH"},
                    {"AttributeName": "timestamp",      "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "_ttl_attribute": "ttl",
    },

    # ── Documents — Document registry, persistent ─────────────────────────────
    {
        "TableName": _table("documents"),
        "KeySchema": [
            {"AttributeName": "doc_id", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "doc_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "_ttl_attribute": None,
    },
]


def get_table_name(suffix: str) -> str:
    """Return the full DynamoDB table name for a given suffix."""
    return _table(suffix)
