from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str
    message: str


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)


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


class RepoChatRequest(BaseModel):
    """Request for repository-specific chat."""

    message: str
    history: list[ChatTurn] = Field(default_factory=list)


class RepoChatResponse(BaseModel):
    """Response for repository-specific chat."""

    answer: str
    repo: RepositoryResponse


class RepoChatRequest(BaseModel):
    """Request for repository-specific chat."""

    message: str
    history: list[ChatTurn] = Field(default_factory=list)


class RepoChatResponse(BaseModel):
    """Response for repository-specific chat."""

    answer: str
    repo: RepositoryResponse
