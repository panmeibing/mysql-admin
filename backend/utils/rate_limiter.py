"""Rate limiter for API endpoints."""
import time
from collections import defaultdict
from typing import Dict, Tuple

from backend.utils.logging_utils import logger


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        # Store: {ip: [(timestamp, count), ...]}
        self._attempts: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 300  # Clean up old entries every 5 minutes
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self):
        """Remove entries older than 1 hour to prevent memory leak."""
        current_time = time.time()

        # Only cleanup periodically
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff_time = current_time - 3600  # 1 hour ago

        for ip in list(self._attempts.keys()):
            # Remove old attempts
            self._attempts[ip] = [
                (timestamp, count)
                for timestamp, count in self._attempts[ip]
                if timestamp > cutoff_time
            ]

            # Remove IP if no attempts left
            if not self._attempts[ip]:
                del self._attempts[ip]

        self._last_cleanup = current_time
        logger.info(f"Rate limiter cleanup completed. Active IPs: {len(self._attempts)}")

    def check_rate_limit(
            self,
            ip: str,
            max_attempts: int = 3,
            window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Check if an IP has exceeded the rate limit.
        
        Args:
            ip: Client IP address
            max_attempts: Maximum number of attempts allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, attempts_used, seconds_until_reset)
        """
        self._cleanup_old_entries()

        current_time = time.time()
        cutoff_time = current_time - window_seconds

        # Get attempts within the time window
        recent_attempts = [
            (timestamp, count)
            for timestamp, count in self._attempts[ip]
            if timestamp > cutoff_time
        ]

        # Calculate total attempts
        total_attempts = sum(count for _, count in recent_attempts)

        # Check if limit exceeded
        if total_attempts >= max_attempts:
            # Calculate when the oldest attempt will expire
            if recent_attempts:
                oldest_timestamp = min(timestamp for timestamp, _ in recent_attempts)
                seconds_until_reset = int(window_seconds - (current_time - oldest_timestamp)) + 1
            else:
                seconds_until_reset = 0

            logger.warning(
                f"Rate limit exceeded for IP {ip}: "
                f"{total_attempts}/{max_attempts} attempts in {window_seconds}s"
            )
            return False, total_attempts, seconds_until_reset

        return True, total_attempts, 0

    def record_attempt(self, ip: str, count: int = 1):
        """
        Record an attempt for an IP.
        
        Args:
            ip: Client IP address
            count: Number of attempts to record (default: 1)
        """
        current_time = time.time()
        self._attempts[ip].append((current_time, count))
        logger.debug(f"Recorded {count} attempt(s) for IP {ip}")

    def reset_ip(self, ip: str):
        """
        Reset attempts for an IP (e.g., after successful login).
        
        Args:
            ip: Client IP address
        """
        if ip in self._attempts:
            del self._attempts[ip]
            logger.info(f"Reset rate limit for IP {ip}")

    def get_attempts(self, ip: str, window_seconds: int = 60) -> int:
        """
        Get the number of attempts for an IP within the time window.
        
        Args:
            ip: Client IP address
            window_seconds: Time window in seconds
            
        Returns:
            Number of attempts
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        recent_attempts = [
            count
            for timestamp, count in self._attempts[ip]
            if timestamp > cutoff_time
        ]

        return sum(recent_attempts)


# Global rate limiter instance
rate_limiter = RateLimiter()
