"""Database service layer for database-level operations."""
import re
from typing import List

import aiomysql

from backend.database import db_manager
from backend.utils.logging_utils import logger


class DatabaseService:
    """Handles database-level operations."""
    
    # Valid database name pattern: alphanumeric and underscore, 1-64 characters
    DB_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')
    
    # System databases that should not be modified
    SYSTEM_DATABASES = {'information_schema', 'mysql', 'performance_schema', 'sys'}
    
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
        
        if not DatabaseService.DB_NAME_PATTERN.match(name):
            raise ValueError(
                "Database name must contain only alphanumeric characters and underscores, "
                "and be between 1 and 64 characters long"
            )
        
        if name.lower() in DatabaseService.SYSTEM_DATABASES:
            raise ValueError(f"Cannot modify system database: {name}")
    
    async def list_databases(self) -> List[str]:
        """
        List all databases on the MySQL server.
        
        Returns:
            List[str]: List of database names
            
        Raises:
            Exception: If the query fails
        """
        connection = None
        try:
            connection = await db_manager.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("SHOW DATABASES")
                results = await cursor.fetchall()
                # Extract database names from tuples
                databases = [row[0] for row in results]
                logger.info(f"Listed {len(databases)} databases")
                return databases
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)
    
    async def create_database(self, name: str) -> None:
        """
        Create a new database with the given name.
        
        Args:
            name: Name of the database to create
            
        Raises:
            ValueError: If the database name is invalid
            Exception: If the database creation fails
        """
        # Validate the database name
        self._validate_database_name(name)
        
        connection = None
        try:
            connection = await db_manager.get_connection()
            async with connection.cursor() as cursor:
                # Use identifier quoting to prevent SQL injection
                # Note: aiomysql doesn't support parameterized identifiers,
                # so we validate the name and use string formatting
                query = f"CREATE DATABASE `{name}`"
                await cursor.execute(query)
                logger.info(f"Created database: {name}")
        except aiomysql.Error as e:
            # Check for duplicate database error (error code 1007)
            if e.args[0] == 1007:
                raise ValueError(f"Database '{name}' already exists")
            logger.error(f"Failed to create database '{name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create database '{name}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)
    
    async def drop_database(self, name: str) -> None:
        """
        Drop (delete) a database.
        
        Args:
            name: Name of the database to drop
            
        Raises:
            ValueError: If the database name is invalid or is a system database
            Exception: If the database deletion fails
        """
        # Validate the database name
        self._validate_database_name(name)
        
        connection = None
        try:
            connection = await db_manager.get_connection()
            async with connection.cursor() as cursor:
                # Use identifier quoting to prevent SQL injection
                query = f"DROP DATABASE `{name}`"
                await cursor.execute(query)
                logger.info(f"Dropped database: {name}")
        except aiomysql.Error as e:
            # Check for database doesn't exist error (error code 1008)
            if e.args[0] == 1008:
                raise ValueError(f"Database '{name}' does not exist")
            logger.error(f"Failed to drop database '{name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to drop database '{name}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)
    
    async def get_database_ddl(self, name: str) -> str:
        """
        Get the DDL (Data Definition Language) for a database.
        This retrieves the CREATE statements for all tables in the database.
        
        Args:
            name: Name of the database
            
        Returns:
            str: DDL statements for the database
            
        Raises:
            ValueError: If the database doesn't exist
            Exception: If the DDL retrieval fails
        """
        connection = None
        try:
            connection = await db_manager.get_connection()
            
            # First, verify the database exists
            async with connection.cursor() as cursor:
                await cursor.execute("SHOW DATABASES")
                databases = [row[0] for row in await cursor.fetchall()]
                if name not in databases:
                    raise ValueError(f"Database '{name}' does not exist")
            
            # Get all tables in the database
            async with connection.cursor() as cursor:
                await cursor.execute(f"SHOW TABLES FROM `{name}`")
                tables = [row[0] for row in await cursor.fetchall()]
            
            # Build DDL string
            ddl_parts = [f"-- Database: {name}\n"]
            ddl_parts.append(f"CREATE DATABASE IF NOT EXISTS `{name}`;\n")
            ddl_parts.append(f"USE `{name}`;\n\n")
            
            # Get CREATE TABLE statement for each table
            for table in tables:
                async with connection.cursor() as cursor:
                    await cursor.execute(f"SHOW CREATE TABLE `{name}`.`{table}`")
                    result = await cursor.fetchone()
                    if result:
                        create_statement = result[1]
                        ddl_parts.append(f"-- Table: {table}\n")
                        ddl_parts.append(f"{create_statement};\n\n")
            
            ddl = "".join(ddl_parts)
            logger.info(f"Retrieved DDL for database: {name}")
            return ddl
            
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to get DDL for database '{name}': {e}")
            raise
        finally:
            if connection:
                await db_manager.release_connection(connection)


# Global database service instance
database_service = DatabaseService()
