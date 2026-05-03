"""Dashboard schemas."""

from pydantic import BaseModel


class DistributionItem(BaseModel):
    name: str
    count: int


class DashboardResponse(BaseModel):
    total_repos: int
    total_collections: int
    languages: list[DistributionItem]
    categories: list[DistributionItem]
    activity_levels: list[DistributionItem]
    stars_distribution: list[DistributionItem]
