"""API router for SQL query execution endpoint."""
from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import (
    QueryRequest,
    QueryResponse
)
from backend.services.query_service import query_service
from backend.utils.logging_utils import logger

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def execute_query(query: QueryRequest):
    """
    Execute any SQL statement (SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, etc.).
    
    Args:
        query: SQL query request
        
    Returns:
        QueryResponse: Query results or affected row count
        
    Raises:
        HTTPException: 400 if SQL is invalid
        HTTPException: 500 if query execution fails
    """
    try:
        sql = query.sql

        # Determine if it's a SELECT query (returns rows) or other statement (returns affected rows)
        if query_service.is_select_query(sql):
            result = await query_service.execute_query(sql)
        elif query_service.is_show_query(sql):
            result = await query_service.execute_query(sql)
        else:
            # Execute as a non-SELECT statement (DML, DDL, etc.)
            result = await query_service.execute_update(sql)

        # If the service returned an error in the result, return it as-is
        # (this happens for SQL syntax errors caught by MySQL)
        if not result.get("success", False):
            return QueryResponse(
                success=False,
                columns=None,
                rows=None,
                affected_rows=None,
                error=result.get("error", "Query execution failed")
            )

        # Return successful result
        if "columns" in result and "rows" in result:
            # SELECT query result
            return QueryResponse(
                success=True,
                columns=result["columns"],
                rows=result["rows"],
                affected_rows=None,
                error=None
            )
        else:
            # DML statement result
            return QueryResponse(
                success=True,
                columns=None,
                rows=None,
                affected_rows=result.get("affected_rows", 0),
                error=None
            )

    except ValueError as e:
        logger.warning(f"Invalid query request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
