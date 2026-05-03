"""Dashboard router - statistics and analytics endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.repository import Repository
from models.collection import Collection
from models.user import User
from routers.deps import get_current_user
from routers.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive dashboard statistics."""
    user_id = current_user.id

    # Total repositories
    total_result = await db.execute(
        select(func.count(Repository.id)).where(Repository.user_id == user_id)
    )
    total_repos = total_result.scalar() or 0

    # Language distribution
    lang_result = await db.execute(
        select(Repository.language, func.count(Repository.id))
        .where(Repository.user_id == user_id)
        .where(Repository.language != "")
        .group_by(Repository.language)
        .order_by(func.count(Repository.id).desc())
        .limit(10)
    )
    languages = [{"name": row[0], "count": row[1]} for row in lang_result.all()]

    # Category distribution
    cat_result = await db.execute(
        select(Repository.category, func.count(Repository.id))
        .where(Repository.user_id == user_id)
        .where(Repository.category != "")
        .group_by(Repository.category)
        .order_by(func.count(Repository.id).desc())
    )
    categories = [{"name": row[0], "count": row[1]} for row in cat_result.all()]

    # Activity level distribution
    activity_result = await db.execute(
        select(Repository.activity_level, func.count(Repository.id))
        .where(Repository.user_id == user_id)
        .where(Repository.activity_level != "")
        .group_by(Repository.activity_level)
    )
    activity_levels = [{"name": row[0], "count": row[1]} for row in activity_result.all()]

    # Stars distribution (buckets: 0-100, 100-1k, 1k-5k, 5k-10k, 10k+)
    stars_buckets = [
        {"name": "0-100", "min": 0, "max": 100},
        {"name": "100-1k", "min": 100, "max": 1000},
        {"name": "1k-5k", "min": 1000, "max": 5000},
        {"name": "5k-10k", "min": 5000, "max": 10000},
        {"name": "10k+", "min": 10000, "max": None},
    ]
    stars_distribution = []
    for bucket in stars_buckets:
        if bucket["max"] is None:
            count_result = await db.execute(
                select(func.count(Repository.id))
                .where(Repository.user_id == user_id)
                .where(Repository.stars >= bucket["min"])
            )
        else:
            count_result = await db.execute(
                select(func.count(Repository.id))
                .where(Repository.user_id == user_id)
                .where(Repository.stars >= bucket["min"])
                .where(Repository.stars < bucket["max"])
            )
        count = count_result.scalar() or 0
        stars_distribution.append({"name": bucket["name"], "count": count})

    # Total collections (user's own collections only)
    collections_result = await db.execute(
        select(func.count(Collection.id)).where(Collection.user_id == user_id)
    )
    total_collections = collections_result.scalar() or 0

    return {
        "total_repos": total_repos,
        "total_collections": total_collections,
        "languages": languages,
        "categories": categories,
        "activity_levels": activity_levels,
        "stars_distribution": stars_distribution,
    }
