"""
Profile store — CRUD for child profiles.

Profiles are persistent (no TTL). They are scoped to authenticated users.
Each user can have multiple profiles (e.g. multiple children).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from agent.models import ChildProfile
from db.dynamodb_client import DynamoDBClient
from db.schemas import get_table_name

logger = logging.getLogger(__name__)

_TABLE = get_table_name("profiles")


class ProfileStore:
    """
    CRUD operations for child profiles in DynamoDB.

    Table key: user_id (PK) + profile_id (SK).
    """

    def __init__(self, db_client: DynamoDBClient) -> None:
        self.db = db_client

    async def create_profile(
        self, user_id: str, profile: ChildProfile
    ) -> ChildProfile:
        """
        Create or overwrite a child profile.

        Args:
            user_id: Authenticated user's ID.
            profile: ChildProfile object to persist.

        Returns:
            The persisted ChildProfile.
        """
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "user_id": user_id,
            "profile_id": profile.profile_id,
            "nickname": profile.nickname,
            "dob": profile.dob,
            "gender": profile.gender,
            "weight_kg": str(profile.weight_kg) if profile.weight_kg else None,
            "medical_conditions": profile.medical_conditions,
            "last_updated": now,
        }
        await self.db.put_item(_TABLE, item)
        logger.info("Profile %s created for user %s", profile.profile_id, user_id)
        return profile

    async def get_profile(
        self, user_id: str, profile_id: str
    ) -> Optional[ChildProfile]:
        """
        Retrieve a specific profile by user_id + profile_id.

        Returns None if the profile does not exist.
        """
        item = await self.db.get_item(
            _TABLE, {"user_id": user_id, "profile_id": profile_id}
        )
        if not item:
            return None
        return self._item_to_profile(item)

    async def list_profiles(self, user_id: str) -> list[ChildProfile]:
        """
        List all profiles for a user.

        Args:
            user_id: Authenticated user's ID.

        Returns:
            List of ChildProfile objects.
        """
        from boto3.dynamodb.conditions import Key

        items = await self.db.query(
            table_name=_TABLE,
            key_condition_expression=Key("user_id").eq(user_id),
        )
        return [self._item_to_profile(i) for i in items]

    async def update_profile(
        self, user_id: str, profile: ChildProfile
    ) -> Optional[ChildProfile]:
        """
        Update an existing profile. Returns None if not found.
        """
        existing = await self.get_profile(user_id, profile.profile_id)
        if not existing:
            return None
        return await self.create_profile(user_id, profile)

    async def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """
        Delete a profile. Returns True if deleted, False if not found.
        """
        existing = await self.get_profile(user_id, profile_id)
        if not existing:
            return False
        await self.db.delete_item(
            _TABLE, {"user_id": user_id, "profile_id": profile_id}
        )
        logger.info("Profile %s deleted for user %s", profile_id, user_id)
        return True

    # ── private helpers ───────────────────────────────────────────────────────

    def _item_to_profile(self, item: dict) -> ChildProfile:
        weight_str = item.get("weight_kg")
        weight_kg = float(weight_str) if weight_str else None
        return ChildProfile(
            profile_id=item["profile_id"],
            nickname=item.get("nickname", ""),
            dob=item.get("dob"),
            gender=item.get("gender"),
            weight_kg=weight_kg,
            medical_conditions=item.get("medical_conditions", []),
        )
