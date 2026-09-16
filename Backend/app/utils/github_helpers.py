"""
GitHub helper utilities.
Exact port of utils/githubHelpers.js.
"""

from datetime import datetime


def get_month_label(date: datetime) -> str:
    """
    Generate a month label in the format "Mon YY" (e.g., "Feb 25").

    Matches the Node.js implementation:
        const month = date.toLocaleString("default", { month: "short" });
        const year = String(date.getFullYear()).slice(-2);
        return `${month} ${year}`;

    Args:
        date: A datetime object.

    Returns:
        A string like "Feb 25" or empty string if date is invalid.
    """
    try:
        if not isinstance(date, datetime):
            return ""

        month = date.strftime("%b")  # Short month name (e.g., "Feb")
        year = str(date.year)[-2:]   # Last 2 digits of year

        return f"{month} {year}"
    except Exception:
        return ""
