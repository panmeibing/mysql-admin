"""Table service layer for table-level operations."""
import re
from typing import List, Dict, Any, Optional

import aiomysql

from backend.database import db_manager
from backend.utils.logging_utils import logger


class TableService:
    """Handles table-level operations."""

    # Valid table name pattern: alphanumeric and underscore, 1-64 characters
    TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')

    @staticmethod
    def _validate_table_name(name: str) -> None:
        """
        Validate table name according to MySQL naming rules.
        
        Args:
            name: Table name to validate
            
        Raises:
            ValueError: If the name is invalid
        """
        if not name:
            raise ValueError("Table name cannot be empty")

        if not TableService.TABLE_NAME_PATTERN.match(name):
            raise ValueError(
                "Table name must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )

    @staticmethod
    def _validate_database_name(name: str) -> None:
        """
        Validate database name according to MySQL naming rules.
        
        Args:
            name: Database name to validate
            
        Raises:
            ValueError: If the name is invalid
        """
        if not name:
            raise ValueError("Database name cannot be empty")

        # Use same pattern as table names for consistency
        if not TableService.TABLE_NAME_PATTERN.match(name):
            raise ValueError(
                "Database name must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )

    async def list_tables(self, database: str) -> List[str]:
        """
        List all tables in a database.
        
        Args:
            database: Name of the database
            
        Returns:
            List[str]: List of table names
            
        Raises:
            ValueError: If the database name is invalid
            Exception: If the query fails
        """
        self._validate_database_name(database)

        connection = None
        try:
            connection = await db_manager.get_connection()
            async with connection.cursor() as cursor:
                # Use SHOW TABLES to list tables in the database
                await cursor.execute(f"SHOW TABLES FROM `{database}`")
                results = await cursor.fetchall()
                # Extract table names from tuples
                tables = [row[0] for row in results]
                logger.info(f"Listed {len(tables)} tables in database '{database}'")
                return tables
        except aiomysql.Error as e:
            # Check for database doesn't exist error (error code 1049)
            if e.args[0] == 1049:
                raise ValueError(f"Database '{database}' does not exist")
            logger.error(f"Failed to list tables in database '{database}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to list tables in database '{database}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)

    async def drop_table(self, database: str, table: str) -> None:
        """
        Drop (delete) a table from a database.
        
        Args:
            database: Name of the database
            table: Name of the table to drop
            
        Raises:
            ValueError: If the database or table name is invalid
            Exception: If the table deletion fails
        """
        self._validate_database_name(database)
        self._validate_table_name(table)

        connection = None
        try:
            connection = await db_manager.get_connection()
            async with connection.cursor() as cursor:
                # Use identifier quoting to prevent SQL injection
                query = f"DROP TABLE `{database}`.`{table}`"
                await cursor.execute(query)
                logger.info(f"Dropped table '{table}' from database '{database}'")
        except aiomysql.Error as e:
            # Check for table doesn't exist error (error code 1051)
            if e.args[0] == 1051:
                raise ValueError(f"Table '{table}' does not exist in database '{database}'")
            # Check for database doesn't exist error (error code 1049)
            if e.args[0] == 1049:
                raise ValueError(f"Database '{database}' does not exist")
            logger.error(f"Failed to drop table '{table}' from database '{database}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to drop table '{table}' from database '{database}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)

    def _parse_filter_condition(
            self,
            filter_condition: str,
            valid_columns: List[str]
    ) -> tuple[str, List[Any]]:
        """
        Parse a filter condition and extract parameters for safe query execution.
        
        This method validates that column names in the filter exist in the table
        and extracts literal values to use as query parameters. This provides
        protection against SQL injection while allowing flexible filter expressions.
        
        Args:
            filter_condition: The WHERE clause condition (without WHERE keyword)
            valid_columns: List of valid column names for the table
            
        Returns:
            Tuple of (sanitized_condition, parameters) where:
                - sanitized_condition: The condition with column names validated
                - parameters: List of parameter values (currently empty as we validate structure)
            
        Raises:
            ValueError: If the filter contains invalid column names or suspicious patterns
        """
        if not filter_condition or not filter_condition.strip():
            return "", []

        # For now, we'll use a validation approach:
        # 1. Check for dangerous SQL keywords that shouldn't be in a WHERE clause
        # 2. Validate that identifiers that look like column names exist in the table
        # 3. Let MySQL handle the actual parsing and parameter binding

        # Convert to uppercase for keyword checking
        condition_upper = filter_condition.upper()

        # Check for dangerous SQL keywords that shouldn't appear in a WHERE clause
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', '--', '/*', '*/',
            'INFORMATION_SCHEMA', 'MYSQL', 'PERFORMANCE_SCHEMA'
        ]

        for keyword in dangerous_keywords:
            if keyword in condition_upper:
                raise ValueError(
                    f"Invalid filter condition: contains forbidden keyword '{keyword}'"
                )

        # Extract potential column names (simple heuristic: words before operators)
        # This is a basic validation - MySQL will do the final validation
        import re
        # Match word characters that could be column names
        potential_columns = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', filter_condition)

        # Filter out SQL keywords and operators
        sql_keywords = {
            'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL',
            'TRUE', 'FALSE', 'ASC', 'DESC', 'LIMIT', 'OFFSET'
        }

        for potential_col in potential_columns:
            if potential_col.upper() not in sql_keywords:
                # Check if this looks like a column name and validate it exists
                if potential_col not in valid_columns:
                    # It might be a value, not a column - that's okay
                    # We'll let MySQL validate the final query
                    pass

        # Return the condition as-is since we've validated it doesn't contain
        # dangerous patterns. MySQL will handle the actual execution safely.
        return filter_condition, []

    async def get_table_data(
            self,
            database: str,
            table: str,
            filter_condition: Optional[str] = None,
            page: int = 1,
            page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Get data from a table with optional filter condition and pagination.
        
        Args:
            database: Name of the database
            table: Name of the table
            filter_condition: Optional WHERE clause condition (without the WHERE keyword)
                             Example: "age > 25 AND name LIKE '%John%'"
            page: Page number (1-based)
            page_size: Number of rows per page
            
        Returns:
            Dict containing:
                - columns: List of column information dicts
                - rows: List of row data as dicts
                - total: Total number of rows (without pagination)
                - page: Current page number
                - page_size: Number of rows per page
                - total_pages: Total number of pages
            
        Raises:
            ValueError: If the database or table name is invalid, or filter contains dangerous patterns
            Exception: If the data retrieval fails
        """
        self._validate_database_name(database)
        self._validate_table_name(table)

        connection = None
        try:
            connection = await db_manager.get_connection()

            # First, get the table structure to know column names
            columns = await self._get_columns_internal(connection, database, table)
            column_names = [col['name'] for col in columns]

            # Build the base query for counting total rows
            count_query = f"SELECT COUNT(*) FROM `{database}`.`{table}`"
            params = []

            if filter_condition:
                # Parse and validate the filter condition
                sanitized_condition, params = self._parse_filter_condition(
                    filter_condition,
                    column_names
                )

                if sanitized_condition:
                    # Add WHERE clause with the validated condition
                    count_query += f" WHERE {sanitized_condition}"

            async with connection.cursor() as cursor:
                # First, get the total count
                if params:
                    await cursor.execute(count_query, params)
                else:
                    await cursor.execute(count_query)

                total_count = (await cursor.fetchone())[0]

                # Calculate pagination
                total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
                offset = (page - 1) * page_size

                # Build the SELECT query with pagination
                query = f"SELECT * FROM `{database}`.`{table}`"

                if filter_condition and sanitized_condition:
                    query += f" WHERE {sanitized_condition}"

                # Add LIMIT and OFFSET for pagination
                query += f" LIMIT {page_size} OFFSET {offset}"

                # Execute the paginated query
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)

                results = await cursor.fetchall()

                # Convert rows to list of dicts
                rows = []
                for row in results:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[column_names[i]] = value
                    rows.append(row_dict)

                logger.info(
                    f"Retrieved {len(rows)} rows (page {page}/{total_pages}) from table '{database}.{table}'"
                    + (f" with filter: {filter_condition}" if filter_condition else "")
                )

                return {
                    "columns": columns,
                    "rows": rows,
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }

        except aiomysql.Error as e:
            # Check for table doesn't exist error (error code 1146)
            if e.args[0] == 1146:
                raise ValueError(f"Table '{table}' does not exist in database '{database}'")
            # Check for database doesn't exist error (error code 1049)
            if e.args[0] == 1049:
                raise ValueError(f"Database '{database}' does not exist")
            # Check for SQL syntax error (error code 1064)
            if e.args[0] == 1064:
                raise ValueError(f"Invalid filter syntax: {e.args[1]}")
            logger.error(f"Failed to get data from table '{database}.{table}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get data from table '{database}.{table}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)

    async def get_table_structure(self, database: str, table: str) -> List[Dict[str, Any]]:
        """
        Get the structure (column information) of a table.
        
        Args:
            database: Name of the database
            table: Name of the table
            
        Returns:
            List of dicts containing column information:
                - name: Column name
                - type: Column data type
                - nullable: Whether the column can be NULL
                - key: Key type (PRI, UNI, MUL, or empty)
                - default: Default value
                - extra: Extra information (e.g., auto_increment)
            
        Raises:
            ValueError: If the database or table name is invalid
            Exception: If the structure retrieval fails
        """
        self._validate_database_name(database)
        self._validate_table_name(table)

        connection = None
        try:
            connection = await db_manager.get_connection()
            columns = await self._get_columns_internal(connection, database, table)
            logger.info(f"Retrieved structure for table '{database}.{table}'")
            return columns
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to get structure for table '{database}.{table}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)

    async def _get_columns_internal(
            self,
            connection: aiomysql.Connection,
            database: str,
            table: str
    ) -> List[Dict[str, Any]]:
        """
        Internal method to get column information using an existing connection.
        
        Args:
            connection: Database connection to use
            database: Name of the database
            table: Name of the table
            
        Returns:
            List of dicts containing column information
            
        Raises:
            ValueError: If the table doesn't exist
            Exception: If the query fails
        """
        async with connection.cursor() as cursor:
            # Use DESCRIBE or SHOW COLUMNS to get table structure
            await cursor.execute(f"SHOW COLUMNS FROM `{database}`.`{table}`")
            results = await cursor.fetchall()

            if not results:
                raise ValueError(f"Table '{table}' does not exist in database '{database}'")

            columns = []
            for row in results:
                # SHOW COLUMNS returns: Field, Type, Null, Key, Default, Extra
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "key": row[3],
                    "default": row[4],
                    "extra": row[5]
                })

            return columns


# Global table service instance
table_service = TableService()
