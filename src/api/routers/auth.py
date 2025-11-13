"""Authentication endpoints for user registration, login, and password reset."""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db_session
from src.models.database import Customer, PasswordReset, User
from src.utils.auth import (
    create_access_token,
    decode_access_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str | None = Field(None, description="User's full name")
    company_name: str | None = Field(None, description="Company name (optional)")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginResponse(BaseModel):
    """Login response with access token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: uuid.UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str | None = Field(None, description="User's full name")


class UserResponse(BaseModel):
    """User profile response."""

    user_id: uuid.UUID
    email: str
    full_name: str | None
    email_verified: bool
    is_active: bool
    created_at: datetime


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="Email address for password reset")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# ============================================================================
# DEPENDENCY: GET CURRENT USER FROM JWT
# ============================================================================


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    return user


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    """Register a new user account.

    Creates both a User and Customer record. The Customer starts on the free tier.

    Args:
        request: Registration request with email, password, etc.
        db: Database session

    Returns:
        LoginResponse with access token

    Raises:
        HTTPException: If email already exists
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = User(
        user_id=uuid.uuid4(),
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        email_verified=False,  # TODO: Implement email verification flow
        email_verification_token=generate_email_verification_token(),
        email_verification_sent_at=datetime.utcnow(),
    )

    db.add(user)
    await db.flush()  # Get user_id

    # Create customer on free tier
    customer = Customer(
        customer_id=uuid.uuid4(),
        user_id=user.user_id,
        email=user.email,
        company_name=request.company_name,
        tier="free",
        rate_limit_rpm=settings.rate_limit_free_rpm,
        rate_limit_rpd=settings.rate_limit_free_rpd,
        monthly_quota=settings.rate_limit_free_monthly,
    )

    db.add(customer)
    await db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": str(user.user_id)})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    """Login with email and password.

    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session

    Returns:
        LoginResponse with access token

    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": str(user.user_id)})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user's profile.

    Args:
        current_user: Current authenticated user from JWT

    Returns:
        UserResponse with profile information
    """
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Request password reset email.

    Creates a password reset token that expires in 1 hour.

    Args:
        request: Password reset request with email
        db: Database session

    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    # Get user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        reset_token = generate_password_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # Store reset token
        password_reset = PasswordReset(
            user_id=user.user_id,
            token=reset_token,
            expires_at=expires_at,
        )

        db.add(password_reset)
        await db.commit()

        # TODO: Send email with reset link
        # For now, just log the token (in production, send email)
        print(f"Password reset token for {user.email}: {reset_token}")

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Reset password using reset token.

    Args:
        request: Password reset confirmation with token and new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid or expired
    """
    # Get reset token
    result = await db.execute(
        select(PasswordReset)
        .where(PasswordReset.token == request.token)
        .where(PasswordReset.used_at.is_(None))
    )
    password_reset = result.scalar_one_or_none()

    if not password_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset token"
        )

    # Check if expired
    if password_reset.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Get user
    result = await db.execute(
        select(User).where(User.user_id == password_reset.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.hashed_password = hash_password(request.new_password)
    password_reset.used_at = datetime.utcnow()

    await db.commit()

    return MessageResponse(message="Password has been reset successfully")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Logout current user.

    Note: Since we're using stateless JWT tokens, this is mostly a placeholder.
    In production, you might want to implement token blacklisting.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # TODO: Implement token blacklisting if needed
    return MessageResponse(message="Successfully logged out")
