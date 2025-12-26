"""Pydantic models for API request/response validation."""
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Validation patterns
DB_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')
TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')


# Database Models

class DatabaseCreate(BaseModel):
    """Request model for creating a new database."""
    name: str = Field(..., min_length=1, max_length=64, description="Database name")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate database name format."""
        if not DB_NAME_PATTERN.match(v):
            raise ValueError(
                "Database name must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )
        # Check for system databases
        system_databases = {'information_schema', 'mysql', 'performance_schema', 'sys'}
        if v.lower() in system_databases:
            raise ValueError(f"Cannot create system database: {v}")
        return v


class DatabaseInfo(BaseModel):
    """Response model for database information."""
    name: str = Field(..., description="Database name")


class DatabaseList(BaseModel):
    """Response model for list of databases."""
    databases: List[str] = Field(..., description="List of database names")


class DatabaseDDL(BaseModel):
    """Response model for database DDL."""
    ddl: str = Field(..., description="Database DDL statements")


# Table Models

class TableInfo(BaseModel):
    """Response model for table information."""
    name: str = Field(..., description="Table name")


class TableList(BaseModel):
    """Response model for list of tables."""
    tables: List[str] = Field(..., description="List of table names")


class ColumnInfo(BaseModel):
    """Response model for column information."""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    nullable: bool = Field(..., description="Whether the column can be NULL")
    key: str = Field(..., description="Key type (PRI, UNI, MUL, or empty)")
    default: Optional[Any] = Field(None, description="Default value")
    extra: str = Field(..., description="Extra information (e.g., auto_increment)")


class TableStructure(BaseModel):
    """Response model for table structure."""
    columns: List[ColumnInfo] = Field(..., description="List of column information")


class TableData(BaseModel):
    """Response model for table data with pagination."""
    columns: List[ColumnInfo] = Field(..., description="Column information")
    rows: List[Dict[str, Any]] = Field(..., description="Row data")
    total: int = Field(..., description="Total number of rows (without pagination)")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Number of rows per page")
    total_pages: int = Field(default=1, description="Total number of pages")


# Data Operation Models

class RowInsert(BaseModel):
    """Request model for inserting a row."""
    data: Dict[str, Any] = Field(..., description="Column names to values mapping")

    @field_validator('data')
    @classmethod
    def validate_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that data is not empty."""
        if not v:
            raise ValueError("Data cannot be empty")
        return v


class RowUpdate(BaseModel):
    """Request model for updating a row."""
    pk_column: str = Field(..., min_length=1, max_length=64, description="Primary key column name")
    pk_value: Any = Field(..., description="Primary key value to identify the row")
    data: Dict[str, Any] = Field(..., description="Column names to new values mapping")

    @field_validator('pk_column')
    @classmethod
    def validate_pk_column(cls, v: str) -> str:
        """Validate primary key column name format."""
        if not TABLE_NAME_PATTERN.match(v):
            raise ValueError(
                "Column name must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )
        return v

    @field_validator('data')
    @classmethod
    def validate_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that data is not empty."""
        if not v:
            raise ValueError("Data cannot be empty")
        return v


class RowDelete(BaseModel):
    """Request model for deleting a row."""
    pk_column: str = Field(..., min_length=1, max_length=64, description="Primary key column name")
    pk_value: Any = Field(..., description="Primary key value to identify the row")

    @field_validator('pk_column')
    @classmethod
    def validate_pk_column(cls, v: str) -> str:
        """Validate primary key column name format."""
        if not TABLE_NAME_PATTERN.match(v):
            raise ValueError(
                "Column name must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )
        return v


# Query Models

class QueryRequest(BaseModel):
    """Request model for SQL query execution."""
    sql: str = Field(..., min_length=1, description="SQL statement to execute")

    @field_validator('sql')
    @classmethod
    def validate_sql(cls, v: str) -> str:
        """Validate that SQL is not empty."""
        if not v.strip():
            raise ValueError("SQL statement cannot be empty")
        return v.strip()


class QueryResponse(BaseModel):
    """Response model for SQL query execution."""
    success: bool = Field(..., description="Whether the query succeeded")
    columns: Optional[List[str]] = Field(None, description="Column names (for SELECT queries)")
    rows: Optional[List[Dict[str, Any]]] = Field(None, description="Row data (for SELECT queries)")
    affected_rows: Optional[int] = Field(None, description="Number of affected rows (for DML statements)")
    error: Optional[str] = Field(None, description="Error message if query failed")


# Health Check Models

class HealthCheck(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    database_connected: bool = Field(..., description="Whether database connection is active")
    message: Optional[str] = Field(None, description="Additional status message")


# Error Models

class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class ValidationErrorDetail(BaseModel):
    """Model for validation error details."""
    loc: List[str] = Field(..., description="Location of the error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Response model for validation errors."""
    error: str = Field(default="Validation error", description="Error type")
    detail: List[ValidationErrorDetail] = Field(..., description="List of validation errors")


# Success Response Models

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(..., description="Success message")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""
    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(..., description="Success message")
