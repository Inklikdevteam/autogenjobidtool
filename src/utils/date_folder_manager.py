"""Date folder management for WebScribe workflow."""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class DateFolderManager:
    """Manages creation and organization of date-based folders for WebScribe workflow."""
    
    def __init__(self, base_path: str, use_yesterday_date: bool = True):
        """Initialize the date folder manager.
        
        Args:
            base_path: Base path where date folders will be created
            use_yesterday_date: If True, use yesterday's date; otherwise use today's date
        """
        self.base_path = Path(base_path)
        self.use_yesterday_date = use_yesterday_date
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"DateFolderManager initialized with base path: {self.base_path}")
    
    def get_yesterday_date(self) -> datetime:
        """Get yesterday's date.
        
        Returns:
            datetime: Yesterday's date at midnight
        """
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_today_date(self) -> datetime:
        """Get today's date.
        
        Returns:
            datetime: Today's date at midnight
        """
        today = datetime.now()
        return today.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_folder_name(self, date: datetime) -> str:
        """Format date as folder name (YYYY-MM-DD).
        
        Args:
            date: Date to format
            
        Returns:
            str: Formatted date string (YYYY-MM-DD)
        """
        return date.strftime("%Y-%m-%d")
    
    def get_last_modified_date(self, files: List) -> Optional[datetime]:
        """Extract the most recent modification date from a list of files.
        
        Args:
            files: List of FileInfo objects with mtime attribute
            
        Returns:
            datetime: Most recent modification date, or None if no files
        """
        if not files:
            return None
        
        try:
            # Find the file with the most recent modification time
            most_recent = max(files, key=lambda f: f.mtime if hasattr(f, 'mtime') else datetime.min)
            
            if hasattr(most_recent, 'mtime') and most_recent.mtime:
                logger.debug(f"Last modified date from files: {most_recent.mtime}")
                return most_recent.mtime
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting last modified date: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                component="DateFolderManager",
                operation="get_last_modified_date"
            )
            return None
    
    def create_date_folder(self, base_path: Optional[str] = None, date: Optional[datetime] = None) -> Path:
        """Create a date-based folder.
        
        Args:
            base_path: Optional base path (uses instance base_path if not provided)
            date: Optional date to use (uses yesterday/today based on config if not provided)
            
        Returns:
            Path: Path to the created date folder
            
        Raises:
            OSError: If folder creation fails
        """
        # Use provided base path or instance base path
        folder_base = Path(base_path) if base_path else self.base_path
        
        # Determine date to use
        if date is None:
            date = self.get_yesterday_date() if self.use_yesterday_date else self.get_today_date()
        
        # Generate folder name
        folder_name = self.get_folder_name(date)
        date_folder = folder_base / folder_name
        
        try:
            # Create the folder
            date_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created date folder: {date_folder}")
            
            # Verify folder was created
            if not date_folder.exists():
                raise OSError(f"Date folder was not created: {date_folder}")
            
            # Verify folder is writable
            if not os.access(date_folder, os.W_OK):
                raise OSError(f"Date folder is not writable: {date_folder}")
            
            return date_folder
            
        except OSError as e:
            logger.error(f"Failed to create date folder {date_folder}: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.HIGH,
                component="DateFolderManager",
                operation="create_date_folder",
                additional_data={
                    "folder_path": str(date_folder),
                    "date": date.isoformat()
                }
            )
            raise
    
    def organize_by_type(self, date_folder: Path, type_name: str) -> Path:
        """Create a type-specific subdirectory within the date folder.
        
        Args:
            date_folder: Path to the date folder
            type_name: Name of the type folder (e.g., 'type3', 'type6')
            
        Returns:
            Path: Path to the type subdirectory
            
        Raises:
            OSError: If subdirectory creation fails
        """
        type_folder = date_folder / type_name
        
        try:
            type_folder.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created type folder: {type_folder}")
            return type_folder
            
        except OSError as e:
            logger.error(f"Failed to create type folder {type_folder}: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.MEDIUM,
                component="DateFolderManager",
                operation="organize_by_type",
                additional_data={
                    "date_folder": str(date_folder),
                    "type_name": type_name
                }
            )
            raise
    
    def get_date_from_folder_name(self, folder_name: str) -> Optional[datetime]:
        """Parse date from folder name (YYYY-MM-DD format).
        
        Args:
            folder_name: Folder name in YYYY-MM-DD format
            
        Returns:
            datetime: Parsed date, or None if parsing fails
        """
        try:
            return datetime.strptime(folder_name, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Could not parse date from folder name: {folder_name}")
            return None
    
    def list_date_folders(self, base_path: Optional[str] = None) -> List[Path]:
        """List all date folders in the base path.
        
        Args:
            base_path: Optional base path (uses instance base_path if not provided)
            
        Returns:
            List[Path]: List of date folder paths, sorted by date (newest first)
        """
        folder_base = Path(base_path) if base_path else self.base_path
        
        if not folder_base.exists():
            return []
        
        date_folders = []
        
        try:
            for item in folder_base.iterdir():
                if item.is_dir():
                    # Try to parse as date folder
                    date = self.get_date_from_folder_name(item.name)
                    if date:
                        date_folders.append(item)
            
            # Sort by date (newest first)
            date_folders.sort(key=lambda p: self.get_date_from_folder_name(p.name), reverse=True)
            
            logger.debug(f"Found {len(date_folders)} date folders in {folder_base}")
            return date_folders
            
        except Exception as e:
            logger.error(f"Error listing date folders: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.LOW,
                component="DateFolderManager",
                operation="list_date_folders"
            )
            return []
    
    def get_folder_size(self, folder_path: Path) -> int:
        """Calculate total size of all files in a folder.
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            int: Total size in bytes
        """
        total_size = 0
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.warning(f"Error calculating folder size for {folder_path}: {e}")
            return 0
    
    def cleanup_old_date_folders(self, days_to_keep: int = 30) -> int:
        """Clean up date folders older than specified days.
        
        Args:
            days_to_keep: Number of days to keep folders
            
        Returns:
            int: Number of folders cleaned up
        """
        if days_to_keep <= 0:
            logger.info("Date folder cleanup is disabled (days_to_keep <= 0)")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        try:
            date_folders = self.list_date_folders()
            
            for folder in date_folders:
                folder_date = self.get_date_from_folder_name(folder.name)
                
                if folder_date and folder_date < cutoff_date:
                    try:
                        # Remove the entire folder and its contents
                        import shutil
                        shutil.rmtree(folder)
                        logger.info(f"Removed old date folder: {folder}")
                        cleaned_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to remove date folder {folder}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old date folders (older than {days_to_keep} days)")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during date folder cleanup: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.LOW,
                component="DateFolderManager",
                operation="cleanup_old_date_folders"
            )
            return 0
