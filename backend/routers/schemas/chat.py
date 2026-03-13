from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str


class RepositoryResponse(BaseModel):
    id: str
    name: str
    description: str
    stars: int
    language: str
    tags: list[str]
    category: str
    aiReason: str | None = None
    has_ui: bool = False  # noqa: N815
    hasUI: bool = False  # noqa: N815
    has_api: bool = False  # noqa: N815
    hasAPI: bool = False  # noqa: N815
    activityLevel: str = "Medium"
    lastUpdated: str = ""
    readme: str = ""
    url: str = ""


class ChatResponse(BaseModel):
    answer: str
    repositories: list[RepositoryResponse]
