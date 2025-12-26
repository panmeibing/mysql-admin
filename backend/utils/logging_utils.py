import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal

from backend.config import get_settings
from backend.utils.singleton_utils import singleton

settings = get_settings()
LoginResult = Literal["success", "failed"]


@singleton
def get_logger(logger_level: str = settings.logger_level, logger_name: str = settings.logger_name):
    """
    Configure logging for the application
    
    Args:
        logger_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Path to log file
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_path = log_dir / f"{logger_name}.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, logger_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set specific log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("tortoise").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("Logging configured successfully")

    return root_logger


logger = get_logger()


class LoginLogger:
    """Logger for login events."""

    def __init__(self, log_dir: str = "logs", log_file: str = "login.txt"):
        """
        Initialize login logger.

        Args:
            log_dir: Directory to store log files
            log_file: Name of the log file
        """
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / log_file

        # Create logs directory if it doesn't exist
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        """Create logs directory if it doesn't exist."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Login log directory ensured: {self.log_dir}")
        except Exception as e:
            logger.error(f"Failed to create log directory {self.log_dir}: {e}")

    def log_login_attempt(self, ip: str, result: LoginResult):
        """
        Log a login attempt.

        Args:
            ip: Client IP address
            result: Login result ("success" or "failed")
        """
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Format log entry
            log_entry = f"{timestamp}   {ip}   {result}\n"

            # Append to log file
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

            logger.info(f"Login attempt logged: {ip} - {result}")

        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")

    def get_recent_logs(self, limit: int = 100) -> list:
        """
        Get recent login logs.

        Args:
            limit: Maximum number of log entries to return

        Returns:
            List of log entries (most recent first)
        """
        try:
            if not self.log_file.exists():
                return []

            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Return most recent entries first
            return lines[-limit:][::-1]

        except Exception as e:
            logger.error(f"Failed to read login logs: {e}")
            return []

    def get_failed_attempts(self, ip: str = None, hours: int = 24) -> int:
        """
        Get number of failed login attempts.

        Args:
            ip: Filter by IP address (optional)
            hours: Time window in hours

        Returns:
            Number of failed attempts
        """
        try:
            if not self.log_file.exists():
                return 0

            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            failed_count = 0

            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        # Parse timestamp
                        timestamp_str = f"{parts[0]} {parts[1]}"
                        try:
                            log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                            # Check if within time window
                            if log_time.timestamp() < cutoff_time:
                                continue

                            # Check IP filter
                            log_ip = parts[2]
                            if ip and log_ip != ip:
                                continue

                            # Check if failed
                            result = parts[3]
                            if result == "failed":
                                failed_count += 1

                        except ValueError:
                            continue

            return failed_count

        except Exception as e:
            logger.error(f"Failed to count failed attempts: {e}")
            return 0


# Global login logger instance
login_logger = LoginLogger()
