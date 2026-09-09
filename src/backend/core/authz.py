"""Feature entitlements for mixed public / premium API access."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from backend.core.auth import UserProfile, get_current_user
from backend.data.postgres import is_db_connected
from backend.services.user_service import user_has_feature

PREMIUM_FEATURES = frozenset({"insights", "player_analytics", "draft_lab"})


def require_feature(feature: str):
    """FastAPI dependency factory: 401 if anonymous (prod), 403 if no entitlement."""

    async def _dep(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if feature not in PREMIUM_FEATURES:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown feature gate: {feature}",
            )
        if user.plan == "premium":
            return user
        if not is_db_connected():
            # Development mock / no Postgres: premium mock already returns plan=premium.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This feature requires a premium account.",
            )
        if await user_has_feature(user.id, feature):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a premium account.",
        )

    return _dep


require_insights = require_feature("insights")
require_player_analytics = require_feature("player_analytics")
require_draft_lab = require_feature("draft_lab")
