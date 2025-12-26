"""Data service layer for row-level CRUD operations."""
import re
from typing import Dict, Any

import aiomysql

from backend.database import db_manager
from backend.utils.logging_utils import logger


class DataService:
    """Handles row-level CRUD operations."""
    
    # Valid identifier pattern: alphanumeric and underscore, 1-64 characters
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')
    
    @staticmethod
    def _validate_identifier(name: str, identifier_type: str = "identifier") -> None:
        """
        Validate database/table/column name according to MySQL naming rules.
        
        Args:
            name: Identifier to validate
            identifier_type: Type of identifier (for error messages)
            
        Raises:
            ValueError: If the name is invalid
        """
        if not name:
            raise ValueError(f"{identifier_type} cannot be empty")
        
        if not DataService.IDENTIFIER_PATTERN.match(name):
            raise ValueError(
                f"{identifier_type} must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )
    
    @staticmethod
    def _sanitize_value(value: Any) -> Any:
        """
        Sanitize input value for database insertion.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        # aiomysql handles parameterization, so we just need basic type checking
        # Convert None to NULL, keep other types as-is
        if value is None:
            return None
        return value
    
    async def insert_row(
        self, 
        database: str, 
        table: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        Insert a new row into a table.
        
        Args:
            database: Name of the database
            table: Name of the table
            data: Dictionary of column names to values
            
        Raises:
            ValueError: If database/table name is invalid or data is empty
            Exception: If the insertion fails
        """
        self._validate_identifier(database, "Database name")
        self._validate_identifier(table, "Table name")
        
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Validate column names
        for column in data.keys():
            self._validate_identifier(column, "Column name")
        
        connection = None
        try:
            connection = await db_manager.get_connection()
            
            # Build parameterized INSERT query
            columns = list(data.keys())
            values = [self._sanitize_value(data[col]) for col in columns]
            
            # Create column list and placeholder list
            column_list = ", ".join([f"`{col}`" for col in columns])
            placeholders = ", ".join(["%s"] * len(columns))
            
            query = f"INSERT INTO `{database}`.`{table}` ({column_list}) VALUES ({placeholders})"
            
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                logger.info(f"Inserted row into table '{database}.{table}'")
                
        except aiomysql.Error as e:
            # Check for table doesn't exist error (error code 1146)
            if e.args[0] == 1146:
                raise ValueError(f"Table '{table}' does not exist in database '{database}'")
            # Check for database doesn't exist error (error code 1049)
            if e.args[0] == 1049:
                raise ValueError(f"Database '{database}' does not exist")
            # Check for unknown column error (error code 1054)
            if e.args[0] == 1054:
                raise ValueError(f"Unknown column in table '{table}': {e.args[1]}")
            # Check for constraint violations (error codes 1062, 1048, 1364, 1452, etc.)
            if e.args[0] in (1062, 1048, 1364, 1452, 1406, 1264):
                raise ValueError(f"Data validation failed: {e.args[1]}")
            logger.error(f"Failed to insert row into table '{database}.{table}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to insert row into table '{database}.{table}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)
    
    async def update_row(
        self,
        database: str,
        table: str,
        pk_column: str,
        pk_value: Any,
        data: Dict[str, Any]
    ) -> None:
        """
        Update an existing row in a table identified by primary key.
        
        Args:
            database: Name of the database
            table: Name of the table
            pk_column: Name of the primary key column
            pk_value: Value of the primary key to identify the row
            data: Dictionary of column names to new values
            
        Raises:
            ValueError: If database/table/column name is invalid or data is empty
            Exception: If the update fails
        """
        self._validate_identifier(database, "Database name")
        self._validate_identifier(table, "Table name")
        self._validate_identifier(pk_column, "Primary key column name")
        
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Validate column names
        for column in data.keys():
            self._validate_identifier(column, "Column name")
        
        connection = None
        try:
            connection = await db_manager.get_connection()
            
            # Build parameterized UPDATE query
            columns = list(data.keys())
            values = [self._sanitize_value(data[col]) for col in columns]
            
            # Create SET clause
            set_clause = ", ".join([f"`{col}` = %s" for col in columns])
            
            query = f"UPDATE `{database}`.`{table}` SET {set_clause} WHERE `{pk_column}` = %s"
            
            # Append pk_value to the values list
            values.append(self._sanitize_value(pk_value))
            
            async with connection.cursor() as cursor:
                affected_rows = await cursor.execute(query, values)
                
                if affected_rows == 0:
                    logger.warning(
                        f"No rows updated in table '{database}.{table}' "
                        f"with {pk_column}={pk_value}"
                    )
                else:
                    logger.info(
                        f"Updated {affected_rows} row(s) in table '{database}.{table}' "
                        f"with {pk_column}={pk_value}"
                    )
                
        except aiomysql.Error as e:
            # Check for table doesn't exist error (error code 1146)
            if e.args[0] == 1146:
                raise ValueError(f"Table '{table}' does not exist in database '{database}'")
            # Check for database doesn't exist error (error code 1049)
            if e.args[0] == 1049:
                raise ValueError(f"Database '{database}' does not exist")
            # Check for unknown column error (error code 1054)
            if e.args[0] == 1054:
                raise ValueError(f"Unknown column in table '{table}': {e.args[1]}")
            # Check for constraint violations
            if e.args[0] in (1062, 1048, 1452, 1406, 1264):
                raise ValueError(f"Data validation failed: {e.args[1]}")
            logger.error(f"Failed to update row in table '{database}.{table}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to update row in table '{database}.{table}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)
    
    async def delete_row(
        self,
        database: str,
        table: str,
        pk_column: str,
        pk_value: Any
    ) -> None:
        """
        Delete a row from a table identified by primary key.
        
        Args:
            database: Name of the database
            table: Name of the table
            pk_column: Name of the primary key column
            pk_value: Value of the primary key to identify the row
            
        Raises:
            ValueError: If database/table/column name is invalid
            Exception: If the deletion fails
        """
        self._validate_identifier(database, "Database name")
        self._validate_identifier(table, "Table name")
        self._validate_identifier(pk_column, "Primary key column name")
        
        connection = None
        try:
            connection = await db_manager.get_connection()
            
            # Build parameterized DELETE query
            query = f"DELETE FROM `{database}`.`{table}` WHERE `{pk_column}` = %s"
            
            async with connection.cursor() as cursor:
                affected_rows = await cursor.execute(query, [self._sanitize_value(pk_value)])
                
                if affected_rows == 0:
                    logger.warning(
                        f"No rows deleted from table '{database}.{table}' "
                        f"with {pk_column}={pk_value}"
                    )
                else:
                    logger.info(
                        f"Deleted {affected_rows} row(s) from table '{database}.{table}' "
                        f"with {pk_column}={pk_value}"
                    )
                
        except aiomysql.Error as e:
            # Check for table doesn't exist error (error code 1146)
            if e.args[0] == 1146:
                raise ValueError(f"Table '{table}' does not exist in database '{database}'")
            # Check for database doesn't exist error (error code 1049)
            if e.args[0] == 1049:
                raise ValueError(f"Database '{database}' does not exist")
            # Check for unknown column error (error code 1054)
            if e.args[0] == 1054:
                raise ValueError(f"Unknown column '{pk_column}' in table '{table}': {e.args[1]}")
            # Check for foreign key constraint violations (error code 1451)
            if e.args[0] == 1451:
                raise ValueError(f"Cannot delete row: foreign key constraint violation: {e.args[1]}")
            logger.error(f"Failed to delete row from table '{database}.{table}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete row from table '{database}.{table}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)


# Global data service instance
data_service = DataService()
