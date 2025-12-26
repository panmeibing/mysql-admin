"""API router for table management endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from backend.models.schemas import (
    TableList,
    TableData,
    TableStructure,
    DeleteResponse
)
from backend.services.table_service import table_service
from backend.utils.logging_utils import logger

router = APIRouter(prefix="/api/databases", tags=["tables"])


@router.get("/{db}/tables", response_model=TableList)
async def list_tables(db: str):
    """
    List all tables in a database.
    
    Args:
        db: Name of the database
        
    Returns:
        TableList: List of table names
        
    Raises:
        HTTPException: 400 if database name is invalid or doesn't exist
        HTTPException: 503 if database connection fails
    """
    try:
        tables = await table_service.list_tables(db)
        return TableList(tables=tables)
    except ValueError as e:
        logger.warning(f"Invalid request to list tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to list tables in database '{db}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list tables: {str(e)}"
        )


@router.delete("/{db}/tables/{table}", response_model=DeleteResponse)
async def delete_table(db: str, table: str):
    """
    Delete a table from a database.
    
    Args:
        db: Name of the database
        table: Name of the table to delete
        
    Returns:
        DeleteResponse: Success message
        
    Raises:
        HTTPException: 400 if database/table name is invalid or doesn't exist
        HTTPException: 503 if database connection fails
    """
    try:
        await table_service.drop_table(db, table)
        return DeleteResponse(
            success=True,
            message=f"Table '{table}' deleted successfully from database '{db}'"
        )
    except ValueError as e:
        logger.warning(f"Invalid table deletion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete table '{table}' from database '{db}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to delete table: {str(e)}"
        )


@router.get("/{db}/tables/{table}/data", response_model=TableData)
async def get_table_data(
    db: str, 
    table: str,
    filter: Optional[str] = Query(None, description="WHERE clause condition (without WHERE keyword)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of rows per page")
):
    """
    Get data from a table with optional filter condition and pagination.
    
    Args:
        db: Name of the database
        table: Name of the table
        filter: Optional WHERE clause condition (without the WHERE keyword)
                Example: "age > 25 AND name LIKE '%John%'"
        page: Page number (1-based, default: 1)
        page_size: Number of rows per page (default: 50, max: 1000)
        
    Returns:
        TableData: Table data with columns, rows, and pagination info
        
    Raises:
        HTTPException: 400 if database/table name is invalid, doesn't exist, or filter is invalid
        HTTPException: 503 if database connection fails
    """
    try:
        data = await table_service.get_table_data(db, table, filter, page, page_size)
        return TableData(**data)
    except ValueError as e:
        logger.warning(f"Invalid request to get table data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get data from table '{db}.{table}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get table data: {str(e)}"
        )


@router.get("/{db}/tables/{table}/structure", response_model=TableStructure)
async def get_table_structure(db: str, table: str):
    """
    Get the structure (column information) of a table.
    
    Args:
        db: Name of the database
        table: Name of the table
        
    Returns:
        TableStructure: Column information for the table
        
    Raises:
        HTTPException: 400 if database/table name is invalid or doesn't exist
        HTTPException: 503 if database connection fails
    """
    try:
        columns = await table_service.get_table_structure(db, table)
        return TableStructure(columns=columns)
    except ValueError as e:
        logger.warning(f"Invalid request to get table structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get structure for table '{db}.{table}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get table structure: {str(e)}"
        )
