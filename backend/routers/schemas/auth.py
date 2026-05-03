"""Authentication-related Pydantic schemas."""

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: EmailStr
    password: str  # Will be validated for strength in the router


class LoginRequest(BaseModel):
    """Request body for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information in API responses."""
    id: int
    email: str
    github_username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    has_github_token: bool = False

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Response after successful login."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GitHubCallbackRequest(BaseModel):
    """Request body for GitHub OAuth callback."""
    code: str
    state: str


class UpdateGitHubTokenRequest(BaseModel):
    """Request body for updating GitHub token."""
    github_token: str


class UpdateProfileRequest(BaseModel):
    """Request body for updating user profile."""
    display_name: str | None = None
    avatar_url: str | None = None
