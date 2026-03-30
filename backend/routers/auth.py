"""Authentication router for user registration, login, and OAuth."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.user import User, UserSetting
from routers.deps import get_current_user
from routers.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    GitHubCallbackRequest,
    UpdateGitHubTokenRequest,
    UpdateProfileRequest,
)
from services.auth import hash_password, verify_password, create_access_token
from services.github_oauth import (
    generate_oauth_state,
    validate_oauth_state,
    get_github_oauth_url,
    exchange_code_for_token,
    get_github_user_info,
    get_github_user_emails,
)
from utils.crypto import encrypt_value
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse."""
    return UserResponse(
        id=user.id,
        email=user.email,
        github_username=user.github_username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        has_github_token=bool(user.github_token),
    )


@router.post("/register", response_model=LoginResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email and password."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate password strength
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    await db.flush()  # Get user.id

    # Create default user settings
    settings = UserSetting(user_id=user.id)
    db.add(settings)

    await db.commit()
    await db.refresh(user)

    # Generate token (sub must be a string per JWT spec)
    access_token = create_access_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        user=_user_to_response(user),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Generate token (sub must be a string per JWT spec)
    access_token = create_access_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        user=_user_to_response(user),
    )


@router.get("/github")
async def github_oauth_redirect(
    db: AsyncSession = Depends(get_db),
):
    """Redirect to GitHub OAuth authorization page."""
    settings = get_settings()

    if not settings.github_oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured"
        )

    state = await generate_oauth_state(db)
    oauth_url = get_github_oauth_url(state)

    # Return the state and URL for frontend to handle redirect
    return {"oauth_url": oauth_url, "state": state}


@router.post("/github/callback", response_model=LoginResponse)
async def github_oauth_callback(
    request: GitHubCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth callback and create/login user."""
    # Validate state
    if not await validate_oauth_state(db, request.state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state"
        )

    try:
        # Exchange code for token
        token_data = await exchange_code_for_token(request.code)
        github_token = token_data.get("access_token")

        if not github_token:
            raise ValueError("No access token in GitHub response")

        # Get GitHub user info
        github_user = await get_github_user_info(github_token)
        github_id = str(github_user.get("id"))
        github_username = github_user.get("login")
        display_name = github_user.get("name")
        avatar_url = github_user.get("avatar_url")

        # Get primary email
        emails = await get_github_user_emails(github_token)
        primary_email = None
        for email_info in emails:
            if email_info.get("primary"):
                primary_email = email_info.get("email")
                break

        # Fallback to public email from user profile
        if not primary_email:
            primary_email = github_user.get("email")

        if not primary_email:
            logger.warning(
                "No email found for GitHub user %s. "
                "Please ensure your GitHub account has a public email or grant email access.",
                github_username
            )
            raise ValueError(
                "No email found. Please add a public email to your GitHub profile "
                "or re-authorize with email access."
            )

        # Find or create user
        result = await db.execute(
            select(User).where(User.github_id == github_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Update existing user
            user.github_token = encrypt_value(github_token)
            user.github_username = github_username
            if display_name:
                user.display_name = display_name
            if avatar_url:
                user.avatar_url = avatar_url
        else:
            # Check if email already registered
            result = await db.execute(
                select(User).where(User.email == primary_email)
            )
            user = result.scalar_one_or_none()

            if user:
                # Link GitHub to existing account
                user.github_id = github_id
                user.github_token = encrypt_value(github_token)
                user.github_username = github_username
                if display_name:
                    user.display_name = display_name
                if avatar_url:
                    user.avatar_url = avatar_url
            else:
                # Check for default migration user to claim
                result = await db.execute(
                    select(User).where(User.email == "default@starmind.local", User.github_id.is_(None))
                )
                default_user = result.scalar_one_or_none()

                if default_user:
                    # Claim the default user - migrate to this GitHub account
                    logger.info(f"Migrating default user {default_user.id} to GitHub account {github_username}")
                    default_user.email = primary_email
                    default_user.github_id = github_id
                    default_user.github_token = encrypt_value(github_token)
                    default_user.github_username = github_username
                    if display_name:
                        default_user.display_name = display_name
                    if avatar_url:
                        default_user.avatar_url = avatar_url
                    user = default_user
                else:
                    # Create new user
                    user = User(
                        email=primary_email,
                        github_id=github_id,
                        github_token=encrypt_value(github_token),
                        github_username=github_username,
                        display_name=display_name,
                        avatar_url=avatar_url,
                    )
                    db.add(user)
                    await db.flush()

                    # Create default user settings
                    settings = UserSetting(user_id=user.id)
                    db.add(settings)

        await db.commit()
        await db.refresh(user)

        # Generate token
        access_token = create_access_token(data={"sub": user.id})

        return LoginResponse(
            access_token=access_token,
            user=_user_to_response(user),
        )

    except Exception as e:
        logger.error("GitHub OAuth error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user's information."""
    return _user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    if request.display_name is not None:
        current_user.display_name = request.display_name
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    await db.commit()
    await db.refresh(current_user)

    return _user_to_response(current_user)


@router.put("/github-token", response_model=UserResponse)
async def update_github_token(
    request: UpdateGitHubTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's GitHub personal access token."""
    # Encrypt the token before storing
    current_user.github_token = encrypt_value(request.github_token)

    # Also update github_username if possible
    try:
        user_info = await get_github_user_info(request.github_token)
        if user_info:
            current_user.github_username = user_info.get("login")
    except Exception as e:
        logger.warning("Could not fetch GitHub user info: %s", e)

    await db.commit()
    await db.refresh(current_user)

    return _user_to_response(current_user)


@router.delete("/github-token")
async def remove_github_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove user's GitHub personal access token."""
    current_user.github_token = None
    await db.commit()

    return {"message": "GitHub token removed"}
