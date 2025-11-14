"""
Authentication and Authorization
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
import hashlib
from datetime import datetime, timedelta

from config.settings import settings
from common.models import User

# Security scheme
security = HTTPBearer()


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Verify API key from header"""
    if not x_api_key:
        return None

    # TODO: Verify API key against database
    # For now, simple validation
    if len(x_api_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    api_key: Optional[str] = Depends(verify_api_key)
) -> User:
    """Get current authenticated user"""

    # Try API key first
    if api_key:
        # TODO: Query user from database using API key
        return User(
            user_id="user_123",
            email="user@example.com",
            username="user123",
            role="user"
        )

    # Try JWT token
    if credentials:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # TODO: Query user from database
        return User(
            user_id=user_id,
            email=payload.get("email", "unknown@example.com"),
            username=payload.get("username", "unknown"),
            role=payload.get("role", "user")
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    # TODO: Use bcrypt or argon2
    import hashlib
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash password"""
    # TODO: Use bcrypt or argon2
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
