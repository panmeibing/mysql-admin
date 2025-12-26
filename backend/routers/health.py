"""API router for health check endpoint."""
from fastapi import APIRouter

from backend.database import db_manager
from backend.models.schemas import HealthCheck
from backend.utils.logging_utils import logger

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Check the health status of the application and database connection.
    
    Returns:
        HealthCheck: Health status information
    """
    try:
        # Test database connection
        is_connected = await db_manager.test_connection()

        if is_connected:
            return HealthCheck(
                status="healthy",
                database_connected=True,
                message="Database connection is active"
            )
        else:
            return HealthCheck(
                status="unhealthy",
                database_connected=False,
                message="Database connection failed"
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            database_connected=False,
            message=f"Health check error: {str(e)}"
        )
