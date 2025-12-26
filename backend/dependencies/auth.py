"""Authentication dependency for admin access."""
from fastapi import Header, HTTPException, status

from backend.config import settings


async def verify_admin_key(x_admin_key: str = Header(None, alias="X-Admin-Key")):
    """
    Verify admin secret key from request header.
    
    Args:
        x_admin_key: Admin secret key from X-Admin-Key header
        
    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin key is required",
            headers={"WWW-Authenticate": "AdminKey"}
        )
    
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
            headers={"WWW-Authenticate": "AdminKey"}
        )
    
    return x_admin_key
