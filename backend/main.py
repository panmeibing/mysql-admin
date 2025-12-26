"""Main FastAPI application with global error handling."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.dependencies.auth import verify_admin_key
from backend.config import get_settings
from backend.database import db_manager
from backend.exceptions.global_exc import configure_exception
from backend.routers import auth, databases, tables, data, query, health
from backend.utils.logging_utils import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    logger.info("Starting MySQL-Admin application...")
    await db_manager.initialize()

    # Test the connection
    if await db_manager.test_connection():
        logger.info("Database connection established successfully")
    else:
        logger.warning("Database connection test failed")

    yield

    # Shutdown
    try:
        logger.info("Shutting down MySQL-Admin application...")
        await db_manager.close_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Configure CORS
def configure_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Register Routers
def configure_router(app: FastAPI):
    # Root redirect to login page
    @app.get("/")
    async def redirect_to_login():
        """Redirect root to login page."""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login.html")

    # Root endpoint (for testing)
    @app.get("/api")
    async def root():
        """Root API endpoint."""
        return {
            "name": settings.server_name,
            "version": settings.server_version,
            "env": settings.server_env,
            "status": "running"
        }

    # Auth router (no authentication required)
    app.include_router(auth.router)
    # Protected routers (require authentication)
    app.include_router(databases.router, dependencies=[Depends(verify_admin_key)])
    app.include_router(tables.router, dependencies=[Depends(verify_admin_key)])
    app.include_router(data.router, dependencies=[Depends(verify_admin_key)])
    app.include_router(query.router, dependencies=[Depends(verify_admin_key)])
    app.include_router(health.router, dependencies=[Depends(verify_admin_key)])


# Serve static files (frontend)
def configure_static_path(app: FastAPI):
    # This should be last to avoid conflicts with API routes
    try:
        app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
        logger.info("Static files middleware configured for frontend")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")


def create_app() -> FastAPI:
    init_config = {
        "title": settings.server_name,
        "description": "A web-based database management tool for MySQL with a modern interface.",
        "version": settings.server_version,
        "lifespan": lifespan,
        "docs_url": None,
        "redoc_url": None
    }
    if settings.server_env == 'dev':
        init_config.pop("docs_url", None)
        init_config.pop("redoc_url", None)
    app = FastAPI(**init_config)
    configure_middleware(app)
    configure_exception(app)
    configure_router(app)
    configure_static_path(app)  # 静态文件必须最后挂载
    return app


app = create_app()
