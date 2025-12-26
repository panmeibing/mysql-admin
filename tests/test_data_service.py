"""Tests for DataService class."""
import pytest
import pytest_asyncio
from backend.database import db_manager
from backend.services.data_service import DataService


@pytest_asyncio.fixture(scope="function")
async def db_connection():
    """Fixture to provide an initialized database connection."""
    await db_manager.initialize()
    yield
    await db_manager.close_pool()


@pytest_asyncio.fixture(scope="function")
async def test_table(db_connection):
    """Fixture to create a test database and table."""
    connection = None
    test_db = "test_data_service_db"
    test_table = "test_users"
    
    try:
        connection = await db_manager.get_connection()
        async with connection.cursor() as cursor:
            # Create test database
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{test_db}`")
            
            # Create test table
            await cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{test_db}`.`{test_table}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE,
                    age INT
                )
            """)
            
            # Clear any existing data
            await cursor.execute(f"DELETE FROM `{test_db}`.`{test_table}`")
        
        yield (test_db, test_table)
        
    finally:
        # Cleanup
        if connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"DROP DATABASE IF EXISTS `{test_db}`")
            await db_manager.release_connection(connection)


@pytest.mark.asyncio
async def test_insert_row(test_table):
    """Test inserting a row into a table."""
    test_db, test_table_name = test_table
    service = DataService()
    
    # Insert a row
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    }
    await service.insert_row(test_db, test_table_name, data)
    
    # Verify the row was inserted
    connection = await db_manager.get_connection()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM `{test_db}`.`{test_table_name}` WHERE email = %s", ["john@example.com"])
            result = await cursor.fetchone()
            assert result is not None
            assert result[1] == "John Doe"  # name column
            assert result[2] == "john@example.com"  # email column
            assert result[3] == 30  # age column
    finally:
        await db_manager.release_connection(connection)


@pytest.mark.asyncio
async def test_insert_row_with_invalid_data(test_table):
    """Test that inserting invalid data raises an error."""
    test_db, test_table_name = test_table
    service = DataService()
    
    # Try to insert with missing required field (name is NOT NULL)
    data = {
        "email": "test@example.com",
        "age": 25
    }
    
    with pytest.raises(ValueError, match="validation failed"):
        await service.insert_row(test_db, test_table_name, data)


@pytest.mark.asyncio
async def test_update_row(test_table):
    """Test updating a row in a table."""
    test_db, test_table_name = test_table
    service = DataService()
    
    # First insert a row
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "age": 25
    }
    await service.insert_row(test_db, test_table_name, data)
    
    # Get the inserted row's ID
    connection = await db_manager.get_connection()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(f"SELECT id FROM `{test_db}`.`{test_table_name}` WHERE email = %s", ["jane@example.com"])
            result = await cursor.fetchone()
            row_id = result[0]
    finally:
        await db_manager.release_connection(connection)
    
    # Update the row
    update_data = {
        "name": "Jane Smith",
        "age": 26
    }
    await service.update_row(test_db, test_table_name, "id", row_id, update_data)
    
    # Verify the row was updated
    connection = await db_manager.get_connection()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM `{test_db}`.`{test_table_name}` WHERE id = %s", [row_id])
            result = await cursor.fetchone()
            assert result is not None
            assert result[1] == "Jane Smith"  # name was updated
            assert result[2] == "jane@example.com"  # email unchanged
            assert result[3] == 26  # age was updated
    finally:
        await db_manager.release_connection(connection)


@pytest.mark.asyncio
async def test_delete_row(test_table):
    """Test deleting a row from a table."""
    test_db, test_table_name = test_table
    service = DataService()
    
    # First insert a row
    data = {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "age": 35
    }
    await service.insert_row(test_db, test_table_name, data)
    
    # Get the inserted row's ID
    connection = await db_manager.get_connection()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(f"SELECT id FROM `{test_db}`.`{test_table_name}` WHERE email = %s", ["bob@example.com"])
            result = await cursor.fetchone()
            row_id = result[0]
    finally:
        await db_manager.release_connection(connection)
    
    # Delete the row
    await service.delete_row(test_db, test_table_name, "id", row_id)
    
    # Verify the row was deleted
    connection = await db_manager.get_connection()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM `{test_db}`.`{test_table_name}` WHERE id = %s", [row_id])
            result = await cursor.fetchone()
            assert result is None
    finally:
        await db_manager.release_connection(connection)


@pytest.mark.asyncio
async def test_validate_identifier():
    """Test identifier validation."""
    service = DataService()
    
    # Valid identifiers should not raise
    service._validate_identifier("test_table", "Table")
    service._validate_identifier("TestTable123", "Table")
    service._validate_identifier("_underscore", "Column")
    
    # Invalid identifiers should raise ValueError
    with pytest.raises(ValueError, match="cannot be empty"):
        service._validate_identifier("", "Table")
    
    with pytest.raises(ValueError, match="alphanumeric"):
        service._validate_identifier("test-table", "Table")
    
    with pytest.raises(ValueError, match="alphanumeric"):
        service._validate_identifier("test.table", "Table")
    
    with pytest.raises(ValueError, match="alphanumeric"):
        service._validate_identifier("test table", "Table")


@pytest.mark.asyncio
async def test_insert_empty_data(test_table):
    """Test that inserting empty data raises an error."""
    test_db, test_table_name = test_table
    service = DataService()
    
    with pytest.raises(ValueError, match="Data cannot be empty"):
        await service.insert_row(test_db, test_table_name, {})


@pytest.mark.asyncio
async def test_update_empty_data(test_table):
    """Test that updating with empty data raises an error."""
    test_db, test_table_name = test_table
    service = DataService()
    
    with pytest.raises(ValueError, match="Data cannot be empty"):
        await service.update_row(test_db, test_table_name, "id", 1, {})


@pytest.mark.asyncio
async def test_insert_into_nonexistent_table(db_connection):
    """Test that inserting into a non-existent table raises an error."""
    service = DataService()
    
    data = {"name": "Test"}
    with pytest.raises(ValueError, match="does not exist"):
        await service.insert_row("test_data_service_db", "nonexistent_table", data)
