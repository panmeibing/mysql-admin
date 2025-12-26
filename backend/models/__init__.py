"""Models package."""

from backend.models.schemas import (
    # Database models
    DatabaseCreate,
    DatabaseInfo,
    DatabaseList,
    DatabaseDDL,
    # Table models
    TableInfo,
    TableList,
    ColumnInfo,
    TableStructure,
    TableData,
    # Data operation models
    RowInsert,
    RowUpdate,
    RowDelete,
    # Query models
    QueryRequest,
    QueryResponse,
    # Health check models
    HealthCheck,
    # Error models
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
    # Success response models
    SuccessResponse,
    DeleteResponse,
)

__all__ = [
    # Database models
    "DatabaseCreate",
    "DatabaseInfo",
    "DatabaseList",
    "DatabaseDDL",
    # Table models
    "TableInfo",
    "TableList",
    "ColumnInfo",
    "TableStructure",
    "TableData",
    # Data operation models
    "RowInsert",
    "RowUpdate",
    "RowDelete",
    # Query models
    "QueryRequest",
    "QueryResponse",
    # Health check models
    "HealthCheck",
    # Error models
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    # Success response models
    "SuccessResponse",
    "DeleteResponse",
]
