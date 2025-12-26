"""Database connection manager for MySQL-Admin."""
from typing import Optional

import aiomysql

from backend.config import settings
from backend.utils.logging_utils import logger


class DatabaseManager:
    """Manages MySQL connection pool and provides connection lifecycle management."""

    def __init__(self):
        """Initialize the DatabaseManager."""
        self._pool: Optional[aiomysql.Pool] = None

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            logger.warning("Connection pool already initialized")
            return

        try:
            self._pool = await aiomysql.create_pool(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                minsize=settings.mysql_pool_min,
                maxsize=settings.mysql_pool_max,
                autocommit=True,
            )
            logger.info(
                f"Database connection pool initialized (min={settings.mysql_pool_min}, max={settings.mysql_pool_max})")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    async def get_connection(self) -> aiomysql.Connection:
        """
        Get a connection from the pool.
        
        Returns:
            aiomysql.Connection: A database connection from the pool
            
        Raises:
            RuntimeError: If the pool is not initialized
            Exception: If connection acquisition fails
        """
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized. Call initialize() first.")

        try:
            connection = await self._pool.acquire()
            return connection
        except Exception as e:
            logger.error(f"Failed to acquire connection: {e}")
            raise

    async def release_connection(self, connection: aiomysql.Connection) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            connection: The connection to release
        """
        if self._pool is None:
            logger.warning("Cannot release connection: pool not initialized")
            return

        try:
            self._pool.release(connection)
        except Exception as e:
            logger.error(f"Failed to release connection: {e}")

    async def close_pool(self) -> None:
        """Close the connection pool and all connections."""
        if self._pool is None:
            logger.warning("Connection pool not initialized, nothing to close")
            return

        try:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("Connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
            raise

    async def test_connection(self) -> bool:
        """
        Test the database connection health.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if self._pool is None:
            logger.warning("Connection pool not initialized")
            return False

        connection = None
        try:
            connection = await self.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
                return result == (1,)
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            return False
        finally:
            if connection:
                await self.release_connection(connection)


# Global database manager instance
db_manager = DatabaseManager()
