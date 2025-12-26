"""API router for authentication endpoints."""
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel

from backend.config import settings
from backend.utils.ip_utils import IpUtil
from backend.utils.logging_utils import login_logger, logger
from backend.utils.rate_limiter import rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    """Authentication request model."""
    secret_key: str


class AuthResponse(BaseModel):
    """Authentication response model."""
    success: bool
    message: str


@router.post("/verify", response_model=AuthResponse)
async def verify_secret_key(auth: AuthRequest, request: Request):
    """
    Verify admin secret key with rate limiting.
    
    Rate limit: 3 attempts per minute per IP address.
    
    Args:
        auth: Authentication request with secret key
        request: FastAPI request object to get client IP
        
    Returns:
        AuthResponse: Success status and message
        
    Raises:
        HTTPException: 429 if rate limit exceeded
        HTTPException: 401 if key is invalid
    """
    # Get client IP address
    client_ip = IpUtil.get_real_client_ip(request)

    # Check rate limit
    is_allowed, attempts_used, seconds_until_reset = rate_limiter.check_rate_limit(
        ip=client_ip,
        max_attempts=settings.max_try_login_time,
        window_seconds=settings.window_seconds,
    )

    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for IP {client_ip}: "
            f"{attempts_used} attempts, reset in {seconds_until_reset}s"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录尝试次数过多，请在 {seconds_until_reset} 秒后重试"
        )

    # Verify secret key
    if auth.secret_key == settings.admin_secret_key:
        # Successful login - reset rate limit for this IP
        rate_limiter.reset_ip(client_ip)

        # Log successful login
        login_logger.log_login_attempt(client_ip, "success")

        logger.info(f"Admin authentication successful from IP {client_ip}")
        return AuthResponse(
            success=True,
            message="Authentication successful"
        )
    else:
        # Failed login - record attempt
        rate_limiter.record_attempt(client_ip)
        remaining_attempts = settings.max_try_login_time - rate_limiter.get_attempts(
            client_ip, window_seconds=settings.window_seconds)

        # Log failed login
        login_logger.log_login_attempt(client_ip, "failed")

        logger.warning(
            f"Admin authentication failed from IP {client_ip}: invalid key "
            f"({remaining_attempts} attempts remaining)"
        )

        if remaining_attempts > 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"管理密钥错误，剩余尝试次数：{remaining_attempts}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录尝试次数过多，请在 {settings.window_seconds} 秒后重试"
            )
