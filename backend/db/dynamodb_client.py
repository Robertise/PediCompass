"""
DynamoDB client — auto-creates all 4 tables on startup.

Uses aioboto3-style pattern but with synchronous boto3 wrapped in
asyncio's run_in_executor so FastAPI async routes are not blocked.
"""

import asyncio
import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import settings
from db.schemas import TABLE_SCHEMAS

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """
    Thin async wrapper around boto3 DynamoDB resource.

    All mutating calls are run in a thread executor to avoid blocking
    the FastAPI event loop.
    """

    def __init__(self) -> None:
        self._resource = boto3.resource(
            "dynamodb",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self._client = boto3.client(
            "dynamodb",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        logger.info("DynamoDBClient initialised (region=%s)", settings.aws_region)

    def get_table(self, table_name: str) -> Any:
        """Return a boto3 Table resource for the given table name."""
        return self._resource.Table(table_name)

    async def ensure_tables_exist(self) -> None:
        """
        Create all 4 PediCompass tables if they do not already exist.
        Idempotent — safe to call every startup.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ensure_tables_sync)

    def _ensure_tables_sync(self) -> None:
        """Synchronous implementation called from the thread executor."""
        for schema in TABLE_SCHEMAS:
            table_name = schema["TableName"]
            ttl_attr = schema.pop("_ttl_attribute", None)

            table = self._resource.Table(table_name)
            try:
                table.load()
                logger.info("Table '%s' already exists.", table_name)
                # Re-add the private key before continuing
                schema["_ttl_attribute"] = ttl_attr
                continue
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ResourceNotFoundException":
                    logger.exception("Failed to check if table '%s' exists: %s", table_name, exc)
                    raise

            # Build create_table kwargs (exclude private _ttl_attribute key)
            create_kwargs = {k: v for k, v in schema.items() if not k.startswith("_")}

            try:
                logger.info("Creating DynamoDB table '%s'…", table_name)
                table = self._resource.create_table(**create_kwargs)
                table.wait_until_exists()
                logger.info("Table '%s' created.", table_name)

                # Enable TTL if applicable
                if ttl_attr:
                    self._client.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification={
                            "Enabled": True,
                            "AttributeName": ttl_attr,
                        },
                    )
                    logger.info(
                        "TTL enabled on '%s' (attribute: %s).", table_name, ttl_attr
                    )
            except ClientError as exc:
                error_code = exc.response["Error"]["Code"]
                if error_code == "ResourceInUseException":
                    logger.warning("Table '%s' already being created.", table_name)
                else:
                    logger.exception("Failed to create table '%s': %s", table_name, exc)
                    raise
            finally:
                # Restore private key for future calls
                schema["_ttl_attribute"] = ttl_attr

    async def put_item(self, table_name: str, item: dict) -> None:
        """Put an item into DynamoDB asynchronously."""
        loop = asyncio.get_event_loop()
        table = self.get_table(table_name)
        await loop.run_in_executor(None, lambda: table.put_item(Item=item))

    async def get_item(self, table_name: str, key: dict) -> dict | None:
        """Get an item from DynamoDB by key. Returns None if not found."""
        loop = asyncio.get_event_loop()
        table = self.get_table(table_name)
        response = await loop.run_in_executor(
            None, lambda: table.get_item(Key=key)
        )
        return response.get("Item")

    async def update_item(
        self,
        table_name: str,
        key: dict,
        update_expression: str,
        expression_values: dict,
        expression_names: dict | None = None,
    ) -> None:
        """Update an item using an UpdateExpression."""
        loop = asyncio.get_event_loop()
        table = self.get_table(table_name)
        kwargs: dict = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
        }
        if expression_names:
            kwargs["ExpressionAttributeNames"] = expression_names

        await loop.run_in_executor(None, lambda: table.update_item(**kwargs))

    async def delete_item(self, table_name: str, key: dict) -> None:
        """Delete an item by key."""
        loop = asyncio.get_event_loop()
        table = self.get_table(table_name)
        await loop.run_in_executor(None, lambda: table.delete_item(Key=key))

    async def query(
        self,
        table_name: str,
        key_condition_expression: Any,
        index_name: str | None = None,
        filter_expression: Any = None,
        expression_values: dict | None = None,
    ) -> list[dict]:
        """Query a table or GSI."""
        loop = asyncio.get_event_loop()
        table = self.get_table(table_name)

        def _query() -> list[dict]:
            kwargs: dict = {
                "KeyConditionExpression": key_condition_expression,
            }
            if index_name:
                kwargs["IndexName"] = index_name
            if filter_expression is not None:
                kwargs["FilterExpression"] = filter_expression
            if expression_values:
                kwargs["ExpressionAttributeValues"] = expression_values
            resp = table.query(**kwargs)
            return resp.get("Items", [])

        return await loop.run_in_executor(None, _query)

    async def scan(
        self,
        table_name: str,
        filter_expression: Any = None,
    ) -> list[dict]:
        """Scan a full table (use sparingly)."""
        loop = asyncio.get_event_loop()
        table = self.get_table(table_name)

        def _scan() -> list[dict]:
            kwargs: dict = {}
            if filter_expression is not None:
                kwargs["FilterExpression"] = filter_expression
            resp = table.scan(**kwargs)
            return resp.get("Items", [])

        return await loop.run_in_executor(None, _scan)


@lru_cache(maxsize=1)
def get_dynamodb_client() -> DynamoDBClient:
    """Singleton DynamoDB client — instantiated once per process."""
    return DynamoDBClient()


dynamodb_manager = get_dynamodb_client()
