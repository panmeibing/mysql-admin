"""API router for database management endpoints."""
from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import (
    DatabaseCreate,
    DatabaseList,
    DatabaseDDL,
    DeleteResponse
)
from backend.services.database_service import database_service
from backend.utils.logging_utils import logger

router = APIRouter(prefix="/api/databases", tags=["databases"])


@router.get("", response_model=DatabaseList)
async def list_databases():
    """
    List all databases on the MySQL server.
    
    Returns:
        DatabaseList: List of database names
        
    Raises:
        HTTPException: 503 if database connection fails
    """
    try:
        databases = await database_service.list_databases()
        return DatabaseList(databases=databases)
    except Exception as e:
        logger.error(f"Failed to list databases: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list databases: {str(e)}"
        )


@router.post("", response_model=DeleteResponse, status_code=status.HTTP_201_CREATED)
async def create_database(database: DatabaseCreate):
    """
    Create a new database.
    
    Args:
        database: Database creation request with name
        
    Returns:
        DeleteResponse: Success message
        
    Raises:
        HTTPException: 400 if database name is invalid or already exists
        HTTPException: 503 if database connection fails
    """
    try:
        await database_service.create_database(database.name)
        return DeleteResponse(
            success=True,
            message=f"Database '{database.name}' created successfully"
        )
    except ValueError as e:
        logger.warning(f"Invalid database creation request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create database '{database.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to create database: {str(e)}"
        )


@router.delete("/{name}", response_model=DeleteResponse)
async def delete_database(name: str):
    """
    Delete a database.
    
    Args:
        name: Name of the database to delete
        
    Returns:
        DeleteResponse: Success message
        
    Raises:
        HTTPException: 400 if database name is invalid or doesn't exist
        HTTPException: 503 if database connection fails
    """
    try:
        await database_service.drop_database(name)
        return DeleteResponse(
            success=True,
            message=f"Database '{name}' deleted successfully"
        )
    except ValueError as e:
        logger.warning(f"Invalid database deletion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete database '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to delete database: {str(e)}"
        )


@router.get("/{name}/ddl", response_model=DatabaseDDL)
async def get_database_ddl(name: str):
    """
    Get the DDL (Data Definition Language) for a database.
    
    Args:
        name: Name of the database
        
    Returns:
        DatabaseDDL: DDL statements for the database
        
    Raises:
        HTTPException: 404 if database doesn't exist
        HTTPException: 503 if database connection fails
    """
    try:
        ddl = await database_service.get_database_ddl(name)
        return DatabaseDDL(ddl=ddl)
    except ValueError as e:
        logger.warning(f"Database not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get DDL for database '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get database DDL: {str(e)}"
        )
