"""Collection schemas for API requests and responses."""

from pydantic import BaseModel, Field


class CollectionBase(BaseModel):
    """Base schema for collection data."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="folder")


class CollectionCreate(CollectionBase):
    """Schema for creating a new collection."""

    pass


class CollectionUpdate(BaseModel):
    """Schema for updating a collection."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = None


class CollectionResponse(BaseModel):
    """Schema for collection in API response."""

    id: str
    name: str
    description: str
    tags: list[str]
    color: str
    icon: str
    repo_count: int
    ai_introduction: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class CollectionListResponse(BaseModel):
    """Schema for collection list response."""

    collections: list[CollectionResponse]


class AddRepoToCollectionRequest(BaseModel):
    """Schema for adding a repo to a collection."""

    repo_id: int
    notes: str = Field(default="", max_length=500)


class CollectionRepoResponse(BaseModel):
    """Schema for a repository in a collection."""

    id: str
    name: str
    description: str
    language: str
    stars: int
    tags: list[str]
    repo_tags: list[str] = []  # Tags specific to this repo in this collection
    category: str
    url: str
    notes: str


class CollectionReposResponse(BaseModel):
    """Schema for collection repositories response."""

    repositories: list[CollectionRepoResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class UpdateCollectionOverview(BaseModel):
    """Schema for updating collection overview."""

    content: str


class UpdateRepoTagsRequest(BaseModel):
    """Schema for updating repo tags in a collection."""

    tags: list[str]


class GenerateOverviewRequest(BaseModel):
    """Schema for AI generating collection overview."""

    prompt: str = ""


class GenerateOverviewResponse(BaseModel):
    """Schema for AI generated overview response."""

    content: str
