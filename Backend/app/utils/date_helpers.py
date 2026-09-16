"""
Date helper utilities.
"""

from datetime import datetime


def parse_iso_date(date_string: str | None) -> datetime | None:
    """
    Parse an ISO 8601 date string into a datetime object.

    Args:
        date_string: ISO format date string (e.g., "2024-01-15T10:30:00Z")

    Returns:
        A datetime object, or None if parsing fails.
    """
    if not date_string:
        return None

    try:
        # Handle the "Z" timezone suffix
        cleaned = date_string.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def get_date_key(date: datetime) -> str:
    """
    Get the YYYY-MM-DD date key from a datetime object.

    Args:
        date: A datetime object.

    Returns:
        String in "YYYY-MM-DD" format.
    """
    return date.strftime("%Y-%m-%d")
