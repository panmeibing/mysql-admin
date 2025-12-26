"""API router for data operation endpoints."""

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import (
    RowInsert,
    RowUpdate,
    RowDelete,
    SuccessResponse,
    DeleteResponse
)
from backend.services.data_service import data_service
from backend.utils.logging_utils import logger

router = APIRouter(prefix="/api/databases", tags=["data"])


@router.post("/{db}/tables/{table}/rows", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def insert_row(db: str, table: str, row: RowInsert):
    """
    Insert a new row into a table.
    
    Args:
        db: Name of the database
        table: Name of the table
        row: Row data to insert
        
    Returns:
        SuccessResponse: Success message
        
    Raises:
        HTTPException: 400 if data is invalid or violates constraints
        HTTPException: 503 if database connection fails
    """
    try:
        await data_service.insert_row(db, table, row.data)
        return SuccessResponse(
            success=True,
            message=f"Row inserted successfully into table '{db}.{table}'"
        )
    except ValueError as e:
        logger.warning(f"Invalid row insertion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to insert row into table '{db}.{table}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to insert row: {str(e)}"
        )


@router.put("/{db}/tables/{table}/rows", response_model=SuccessResponse)
async def update_row(db: str, table: str, row: RowUpdate):
    """
    Update an existing row in a table.
    
    Args:
        db: Name of the database
        table: Name of the table
        row: Row update data with primary key identification
        
    Returns:
        SuccessResponse: Success message
        
    Raises:
        HTTPException: 400 if data is invalid or violates constraints
        HTTPException: 503 if database connection fails
    """
    try:
        await data_service.update_row(db, table, row.pk_column, row.pk_value, row.data)
        return SuccessResponse(
            success=True,
            message=f"Row updated successfully in table '{db}.{table}'"
        )
    except ValueError as e:
        logger.warning(f"Invalid row update request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update row in table '{db}.{table}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to update row: {str(e)}"
        )


@router.delete("/{db}/tables/{table}/rows", response_model=DeleteResponse)
async def delete_row(db: str, table: str, row: RowDelete):
    """
    Delete a row from a table.
    
    Args:
        db: Name of the database
        table: Name of the table
        row: Row deletion data with primary key identification
        
    Returns:
        DeleteResponse: Success message
        
    Raises:
        HTTPException: 400 if data is invalid
        HTTPException: 503 if database connection fails
    """
    try:
        await data_service.delete_row(db, table, row.pk_column, row.pk_value)
        return DeleteResponse(
            success=True,
            message=f"Row deleted successfully from table '{db}.{table}'"
        )
    except ValueError as e:
        logger.warning(f"Invalid row deletion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete row from table '{db}.{table}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to delete row: {str(e)}"
        )
