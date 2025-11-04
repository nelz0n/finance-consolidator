"""Date parsing utilities."""

from datetime import datetime
from typing import Union, Optional
from dateutil import parser as dateutil_parser
from src.utils.logger import get_logger

logger = get_logger()


def parse_date(
    date_str: Union[str, datetime],
    date_format: Optional[str] = None,
    timezone: str = "Europe/Prague"
) -> Optional[datetime]:
    """
    Parse date string to datetime object.
    
    Args:
        date_str: Date string or datetime object
        date_format: Expected format (e.g., "%d.%m.%Y")
        timezone: Timezone name (not used yet, for future)
        
    Returns:
        Datetime object or None if parsing fails
    """
    if isinstance(date_str, datetime):
        return date_str
    
    if not date_str or str(date_str).strip() == "":
        return None
    
    date_str = str(date_str).strip()
    
    try:
        if date_format:
            # Use specific format
            return datetime.strptime(date_str, date_format)
        else:
            # Try automatic parsing
            return dateutil_parser.parse(date_str, dayfirst=True)
    except Exception as e:
        logger.error(f"Failed to parse date '{date_str}': {e}")
        return None


def format_date(date: datetime, format_str: str = "%Y-%m-%d") -> str:
    """
    Format datetime to string.
    
    Args:
        date: Datetime object
        format_str: Output format
        
    Returns:
        Formatted date string
    """
    if not date:
        return ""
    
    try:
        return date.strftime(format_str)
    except Exception as e:
        logger.error(f"Failed to format date {date}: {e}")
        return ""


def parse_czech_date(date_str: str) -> Optional[datetime]:
    """
    Parse Czech date format variations.
    
    Common formats:
    - "31.10.2025"
    - "31. 10. 2025"
    - "1. 10. 2025"
    
    Args:
        date_str: Date string
        
    Returns:
        Datetime object or None
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Try with dots and spaces
    formats = [
        "%d.%m.%Y",      # 31.10.2025
        "%d. %m. %Y",    # 31. 10. 2025
        "%d.%m.%y",      # 31.10.25
        "%d. %m. %y",    # 31. 10. 25
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try automatic parsing as fallback
    try:
        return dateutil_parser.parse(date_str, dayfirst=True)
    except Exception:
        logger.warning(f"Could not parse Czech date: {date_str}")
        return None


def get_date_range(from_date: Optional[str] = None, to_date: Optional[str] = None):
    """
    Get date range from strings.
    
    Args:
        from_date: Start date string
        to_date: End date string
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start = parse_date(from_date) if from_date else None
    end = parse_date(to_date) if to_date else None
    
    return start, end
