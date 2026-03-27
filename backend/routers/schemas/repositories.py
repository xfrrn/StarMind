from pydantic import BaseModel


class RepoOut(BaseModel):
    id: str
    name: str
    description: str
    stars: int
    language: str
    tags: list[str]
    category: str
    aiReason: str | None = None
    hasUI: bool = False
    hasAPI: bool = False
    activityLevel: str = "Medium"
    lastUpdated: str = ""
    updatedAt: str | None = None
    readme: str = ""
    url: str = ""

    class Config:
        from_attributes = True


class RepoListResponse(BaseModel):
    repositories: list[RepoOut]
    total: int
    page: int
    limit: int


class StatsResponse(BaseModel):
    total: int
    languages: dict[str, int]
    categories: dict[str, int]
