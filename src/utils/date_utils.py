"""Date normalization utilities for medical document processing."""

import re
from datetime import datetime
from typing import Optional


def normalize_date(date_str: str) -> str:
    """
    Normalize various date formats to MM/DD/YYYY format.
    
    Args:
        date_str: Input date string in various formats
        
    Returns:
        Normalized date string in MM/DD/YYYY format, or empty string if parsing fails
    """
    if not date_str or not date_str.strip():
        return ""
    
    # Clean the input string
    date_str = date_str.strip()
    
    # Common date patterns to match
    patterns = [
        # MM/DD/YYYY, M/D/YYYY, MM/D/YYYY, M/DD/YYYY
        (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', lambda m: f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"),
        
        # MM-DD-YYYY, M-D-YYYY, MM-D-YYYY, M-DD-YYYY
        (r'^(\d{1,2})-(\d{1,2})-(\d{4})$', lambda m: f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"),
        
        # YYYY/MM/DD, YYYY/M/D
        (r'^(\d{4})/(\d{1,2})/(\d{1,2})$', lambda m: f"{int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(1)}"),
        
        # YYYY-MM-DD, YYYY-M-D
        (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', lambda m: f"{int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(1)}"),
        
        # DD/MM/YYYY (European format) - assuming day comes first when > 12
        (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', lambda m: f"{int(m.group(2)):02d}/{int(m.group(1)):02d}/{m.group(3)}" if int(m.group(1)) > 12 else f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"),
        
        # Month DD, YYYY or Month D, YYYY
        (r'^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$', _parse_month_day_year),
        
        # DD Month YYYY or D Month YYYY
        (r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$', _parse_day_month_year),
        
        # YYYYMMDD
        (r'^(\d{4})(\d{2})(\d{2})$', lambda m: f"{int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(1)}"),
        
        # MMDDYYYY
        (r'^(\d{2})(\d{2})(\d{4})$', lambda m: f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"),
    ]
    
    for pattern, formatter in patterns:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                result = formatter(match)
                # Validate the date by trying to parse it
                if _validate_date(result):
                    return result
            except (ValueError, AttributeError):
                continue
    
    # If no pattern matches, try to parse with datetime
    try:
        parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
        return parsed_date.strftime("%m/%d/%Y")
    except ValueError:
        pass
    
    # Return empty string if all parsing attempts fail
    return ""


def _parse_month_day_year(match) -> str:
    """Parse 'Month DD, YYYY' format."""
    month_name = match.group(1)
    day = int(match.group(2))
    year = match.group(3)
    
    month_num = _month_name_to_number(month_name)
    if month_num:
        return f"{month_num:02d}/{day:02d}/{year}"
    raise ValueError("Invalid month name")


def _parse_day_month_year(match) -> str:
    """Parse 'DD Month YYYY' format."""
    day = int(match.group(1))
    month_name = match.group(2)
    year = match.group(3)
    
    month_num = _month_name_to_number(month_name)
    if month_num:
        return f"{month_num:02d}/{day:02d}/{year}"
    raise ValueError("Invalid month name")


def _month_name_to_number(month_name: str) -> Optional[int]:
    """Convert month name to number."""
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    return months.get(month_name.lower())


def _validate_date(date_str: str) -> bool:
    """Validate that a date string in MM/DD/YYYY format represents a valid date."""
    try:
        datetime.strptime(date_str, "%m/%d/%Y")
        return True
    except ValueError:
        return False


def extract_date_from_text(text: str, field_name: str) -> str:
    """
    Extract a date value from text based on field name patterns.
    
    Args:
        text: The text to search for dates
        field_name: The name of the field to search for (e.g., 'date_of_birth', 'exam_date')
        
    Returns:
        Normalized date string in MM/DD/YYYY format, or empty string if not found
    """
    if not text or not field_name:
        return ""
    
    # Create search patterns based on field name
    field_patterns = {
        'date_of_birth': [r'date\s+of\s+birth[:\s]+([^\n\r]+)', r'dob[:\s]+([^\n\r]+)', r'birth\s+date[:\s]+([^\n\r]+)'],
        'accident_date': [r'accident\s+date[:\s]+([^\n\r]+)', r'date\s+of\s+accident[:\s]+([^\n\r]+)'],
        'exam_date': [r'exam\s+date[:\s]+([^\n\r]+)', r'examination\s+date[:\s]+([^\n\r]+)'],
        'dd_date': [r'dd\s+date[:\s]+([^\n\r]+)', r'dictation\s+date[:\s]+([^\n\r]+)'],
        'transcription_date': [r'transcription\s+date[:\s]+([^\n\r]+)', r'transcribed[:\s]+([^\n\r]+)']
    }
    
    patterns = field_patterns.get(field_name, [])
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_text = match.group(1).strip()
            normalized = normalize_date(date_text)
            if normalized:
                return normalized
    
    return ""