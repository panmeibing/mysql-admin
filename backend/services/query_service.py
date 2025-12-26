"""Query service layer for SQL query execution."""
import re
from typing import Dict, Any

import aiomysql

from backend.database import db_manager
from backend.utils.logging_utils import logger


class QueryService:
    """Handles custom SQL query execution."""

    # Pattern to identify SELECT queries (case-insensitive)
    SELECT_PATTERN = re.compile(r'^\s*SELECT\s+', re.IGNORECASE)

    # Pattern to identify DML statements (INSERT, UPDATE, DELETE)
    DML_PATTERN = re.compile(r'^\s*(INSERT|UPDATE|DELETE)\s+', re.IGNORECASE)

    # Pattern to identify SHOW queries (case-insensitive)
    SHOW_PATTERN = re.compile(r'^\s*SHOW\s+', re.IGNORECASE)

    @staticmethod
    def _remove_comments(sql: str) -> str:
        """
        Remove SQL comments from the statement.
        
        Args:
            sql: SQL statement with possible comments
            
        Returns:
            str: SQL statement without comments
        """
        # Remove single-line comments (-- comment)
        lines = sql.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove -- comments
            comment_pos = line.find('--')
            if comment_pos >= 0:
                line = line[:comment_pos]
            # Keep non-empty lines
            if line.strip():
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @staticmethod
    def is_select_query(sql: str) -> bool:
        """
        Check if the SQL statement is a SELECT query.
        Ignores SQL comments when checking.
        
        Args:
            sql: SQL statement to check
            
        Returns:
            bool: True if it's a SELECT query, False otherwise
        """
        # Remove comments before checking
        cleaned_sql = QueryService._remove_comments(sql)
        return bool(QueryService.SELECT_PATTERN.match(cleaned_sql))

    @staticmethod
    def is_dml_statement(sql: str) -> bool:
        """
        Check if the SQL statement is a DML statement (INSERT, UPDATE, DELETE).
        Ignores SQL comments when checking.
        
        Args:
            sql: SQL statement to check
            
        Returns:
            bool: True if it's a DML statement, False otherwise
        """
        # Remove comments before checking
        cleaned_sql = QueryService._remove_comments(sql)
        return bool(QueryService.DML_PATTERN.match(cleaned_sql))

    @staticmethod
    def is_show_query(sql: str) -> bool:
        """
        Check if the SQL statement is a SHOW query.
        Ignores SQL comments when checking.

        Args:
            sql: SQL statement to check

        Returns:
            bool: True if it's a SHOW query, False otherwise
        """
        # Remove comments before checking
        cleaned_sql = QueryService._remove_comments(sql)
        return bool(QueryService.SHOW_PATTERN.match(cleaned_sql))

    @staticmethod
    def _validate_sql(sql: str) -> None:
        """
        Validate SQL statement.
        
        Args:
            sql: SQL statement to validate
            
        Raises:
            ValueError: If the SQL is invalid
        """
        if not sql or not sql.strip():
            raise ValueError("SQL statement cannot be empty")

    async def execute_query(self, sql: str) -> Dict[str, Any]:
        """
        Execute a SELECT query and return results.
        
        Args:
            sql: SELECT SQL statement to execute
            
        Returns:
            Dict containing:
                - success: True if query succeeded
                - columns: List of column names
                - rows: List of row data as dicts
                - error: None if successful
            
        Raises:
            ValueError: If the SQL is empty
            Exception: If the query execution fails
        """
        # Validate SQL
        self._validate_sql(sql)

        connection = None
        try:
            connection = await db_manager.get_connection()

            async with connection.cursor() as cursor:
                await cursor.execute(sql)
                results = await cursor.fetchall()

                # Get column names from cursor description
                columns = []
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]

                # Convert rows to list of dicts
                rows = []
                for row in results:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[columns[i]] = value
                    rows.append(row_dict)

                logger.info(f"Executed SELECT query, returned {len(rows)} rows")

                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "error": None
                }

        except aiomysql.Error as e:
            error_msg = f"MySQL error: {e.args[1] if len(e.args) > 1 else str(e)}"
            logger.error(f"Failed to execute query: {error_msg}")
            return {
                "success": False,
                "columns": None,
                "rows": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Query execution failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "columns": None,
                "rows": None,
                "error": error_msg
            }
        finally:
            if connection:
                await db_manager.release_connection(connection)

    async def execute_update(self, sql: str) -> Dict[str, Any]:
        """
        Execute a DML/DDL statement and return affected row count.
        
        Args:
            sql: SQL statement to execute
            
        Returns:
            Dict containing:
                - success: True if statement succeeded
                - affected_rows: Number of rows affected
                - error: None if successful
            
        Raises:
            ValueError: If the SQL is empty
            Exception: If the statement execution fails
        """
        # Validate SQL
        self._validate_sql(sql)

        connection = None
        try:
            connection = await db_manager.get_connection()

            async with connection.cursor() as cursor:
                affected_rows = await cursor.execute(sql)
                await connection.commit()  # Commit the transaction
                logger.info(f"Executed SQL statement, affected {affected_rows} rows")

                return {
                    "success": True,
                    "affected_rows": affected_rows,
                    "error": None
                }

        except aiomysql.Error as e:
            error_msg = f"MySQL error: {e.args[1] if len(e.args) > 1 else str(e)}"
            logger.error(f"Failed to execute SQL statement: {error_msg}")
            return {
                "success": False,
                "affected_rows": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"SQL execution failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "affected_rows": None,
                "error": error_msg
            }
        finally:
            if connection:
                await db_manager.release_connection(connection)


# Global query service instance
query_service = QueryService()
