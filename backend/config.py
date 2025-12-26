"""Configuration management for MySQL connection parameters."""

from functools import lru_cache

from pydantic_settings import BaseSettings

"""
Configuration class for MySQL-Admin application.
"""


class Settings(BaseSettings):
    server_name: str = "MySQL-Admin API"
    server_version: str = "1.0.0"
    server_env: str = "dev"
    server_ip: str = "127.0.0.1"
    server_port: int = 8000

    # MySQL connection parameters
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"

    # Connection pool settings
    mysql_pool_min: int = 1
    mysql_pool_max: int = 10

    # Admin authentication
    admin_secret_key: str = "admin123"
    max_try_login_time: int = 3
    window_seconds: int = 60

    # Logging
    logger_level: str = "INFO"
    logger_name: str = "mysql-admin"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
