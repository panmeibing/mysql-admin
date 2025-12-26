import aiomysql
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.utils.logging_utils import logger

"""
Global Exception Handlers

These handlers provide centralized error handling for the application.
They catch exceptions that escape from the routers and convert them to
appropriate HTTP responses with structured error messages.

Error Handling Strategy:
1. Routers catch specific exceptions and raise HTTPException with appropriate status codes
2. Global handlers catch any exceptions that escape the routers
3. All errors are logged for debugging purposes
4. Error responses follow a consistent structure with "error" and "detail" fields

HTTP Status Code Mapping:
- 400 Bad Request: Invalid input, SQL syntax errors, constraint violations
- 404 Not Found: Resource not found (database, table, etc.)
- 422 Unprocessable Entity: Request validation errors
- 500 Internal Server Error: Unexpected errors
- 503 Service Unavailable: Database connection errors, service unavailable
"""


def configure_exception(app: FastAPI):
    @app.exception_handler(aiomysql.Error)
    async def mysql_error_handler(request: Request, exc: aiomysql.Error):
        """
        Handle MySQL database errors.

        Maps MySQL errors to appropriate HTTP status codes:
        - Connection errors: 503 Service Unavailable
        - SQL syntax errors: 400 Bad Request
        - Other database errors: 500 Internal Server Error
        """
        error_message = str(exc)
        logger.error(f"MySQL error on {request.url.path}: {error_message}")

        # Check for connection-related errors
        if isinstance(exc, (aiomysql.OperationalError, aiomysql.InterfaceError)):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Database connection error",
                    "detail": error_message
                }
            )

        # Check for SQL syntax errors
        if isinstance(exc, aiomysql.ProgrammingError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "SQL syntax error",
                    "detail": error_message
                }
            )

        # Check for integrity constraint violations
        if isinstance(exc, aiomysql.IntegrityError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Database integrity constraint violation",
                    "detail": error_message
                }
            )

        # Generic database error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database error",
                "detail": error_message
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """
        Handle Pydantic request validation errors.

        Returns HTTP 422 with detailed validation error information.
        """
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": [str(loc) for loc in error["loc"]],
                "msg": error["msg"],
                "type": error["type"]
            })

        logger.warning(f"Validation error on {request.url.path}: {errors}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": errors
            }
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        """
        Handle Pydantic model validation errors.

        Returns HTTP 422 with detailed validation error information.
        """
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": [str(loc) for loc in error["loc"]],
                "msg": error["msg"],
                "type": error["type"]
            })

        logger.warning(f"Pydantic validation error on {request.url.path}: {errors}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": errors
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """
        Handle ValueError exceptions.

        ValueError is used throughout the application to indicate:
        - Invalid input (400 Bad Request)
        - Resource not found (404 Not Found)

        The handler determines the appropriate status code based on the error message.
        """
        error_message = str(exc)
        logger.warning(f"ValueError on {request.url.path}: {error_message}")

        # Check if it's a "not found" error
        not_found_keywords = ["not found", "does not exist", "doesn't exist", "not exist"]
        if any(keyword in error_message.lower() for keyword in not_found_keywords):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Resource not found",
                    "detail": error_message
                }
            )

        # Otherwise, treat as bad request
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid input",
                "detail": error_message
            }
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        """
        Handle RuntimeError exceptions.

        RuntimeError is used for connection pool issues and other runtime problems.
        Returns HTTP 503 Service Unavailable.
        """
        error_message = str(exc)
        logger.error(f"RuntimeError on {request.url.path}: {error_message}")

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service unavailable",
                "detail": error_message
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """
        Handle all other unhandled exceptions.

        Returns HTTP 500 Internal Server Error with a generic error message.
        Logs the full exception for debugging.
        """
        logger.exception(f"Unhandled exception on {request.url.path}: {exc}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred. Please check the server logs."
            }
        )
