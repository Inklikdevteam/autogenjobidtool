"""CSV generation and file management utilities for medical document processing."""

import csv
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import MedicalRecord, StorageConfig, RetentionConfig


logger = logging.getLogger(__name__)


class CSVGenerator:
    """Handles CSV generation and file management for medical records."""
    
    # Exact column ordering as specified in requirements
    CSV_COLUMNS = [
        'source_file',
        'first_name', 
        'last_name',
        'date_of_birth',
        'record_number',
        'case_number',
        'accident_date/Injury_date',
        'provider_first',
        'provider_last',
        'exam_date',
        'exam_place',
        'transcriptionist',
        'dd_date',
        'transcription_date',
        'job_number',
        'case_code'
    ]
    
    def __init__(self, storage_config: StorageConfig, retention_config: Optional[RetentionConfig] = None):
        """Initialize CSV generator with storage configuration.
        
        Args:
            storage_config: Configuration for local storage paths
            retention_config: Configuration for file retention policies
        """
        self.storage_config = storage_config
        self.retention_config = retention_config or RetentionConfig()
        
        # Initialize ZIP backup directory
        self.zip_backup_path = Path(storage_config.zip_backup_path)
        self.zip_backup_path.mkdir(parents=True, exist_ok=True)
        self.local_storage_path = Path(storage_config.local_storage_path)
        self.temp_path = Path(storage_config.temp_path)
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directories exist: {self.local_storage_path}, {self.temp_path}")
    
    def _generate_csv_filename(self, zip_filename: str) -> str:
        """Generate CSV filename in format YYYYMMDD_output.csv based on ZIP filename.
        
        Args:
            zip_filename: Original ZIP filename (e.g., "11012025.zip" or "20251025.zip")
            
        Returns:
            str: CSV filename in format "YYYYMMDD_output.csv"
        """
        import re
        
        # Remove .zip extension and get base name
        base_name = Path(zip_filename).stem
        
        # Check if it's an 8-digit number
        if re.match(r'^\d{8}$', base_name):
            # Determine if it's YYYYMMDD or MMDDYYYY based on the first 4 digits
            first_four = base_name[:4]
            
            # If first 4 digits are >= 2000, it's likely YYYYMMDD
            if int(first_four) >= 2000:
                # YYYYMMDD format (e.g., "20251025")
                year = base_name[:4]
                month = base_name[4:6]
                day = base_name[6:8]
                
                # Validate month and day
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    return f"{year}{month}{day}_output.csv"
            
            # Otherwise, assume MMDDYYYY format (e.g., "11012025")
            month = base_name[:2]
            day = base_name[2:4]
            year = base_name[4:8]
            
            # Validate month and day
            if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                return f"{year}{month}{day}_output.csv"
        
        # If no valid date pattern matches, use current date with original filename
        current_date = datetime.now().strftime("%Y%m%d")
        logger.warning(f"Could not extract date from ZIP filename '{zip_filename}', using current date")
        return f"{current_date}_output_{base_name}.csv"
    
    def generate_csv(self, medical_records: List[MedicalRecord], zip_filename: str) -> str:
        """Generate CSV file from medical records with organized storage structure.
        
        Args:
            medical_records: List of medical records to write to CSV
            zip_filename: Original ZIP filename for naming the CSV
            
        Returns:
            str: Path to the generated CSV file
            
        Raises:
            IOError: If CSV file cannot be created
        """
        if not medical_records:
            logger.warning("No medical records provided for CSV generation")
            return ""
        
        # Extract date from ZIP filename and create CSV filename
        csv_filename = self._generate_csv_filename(zip_filename)
        
        # Create organized storage structure with date-based subdirectories
        date_folder = datetime.now().strftime("%Y-%m")
        csv_dir = self.local_storage_path / date_folder
        csv_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = csv_dir / csv_filename
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.CSV_COLUMNS)
                
                # Write header
                writer.writeheader()
                
                # Write medical records
                for record in medical_records:
                    # Convert dataclass to dict with exact column ordering
                    row_data = {
                        'source_file': record.source_file,
                        'first_name': record.first_name,
                        'last_name': record.last_name,
                        'date_of_birth': record.date_of_birth,
                        'record_number': record.record_number,
                        'case_number': record.case_number,
                        'accident_date/Injury_date': record.accident_date,  # Maps to accident_date field in MedicalRecord
                        'provider_first': record.provider_first,
                        'provider_last': record.provider_last,
                        'exam_date': record.exam_date,
                        'exam_place': record.exam_place,
                        'transcriptionist': record.transcriptionist,
                        'dd_date': record.dd_date,
                        'transcription_date': record.transcription_date,
                        'job_number': record.job_number,
                        'case_code': record.case_code
                    }
                    writer.writerow(row_data)
            
            logger.info(f"Generated CSV file: {csv_path} with {len(medical_records)} records")
            return str(csv_path)
            
        except IOError as e:
            logger.error(f"Failed to create CSV file {csv_path}: {e}")
            raise
    
    def cleanup_temp_files(self, temp_dir: Optional[str] = None) -> None:
        """Clean up temporary files after processing.
        
        Args:
            temp_dir: Specific temporary directory to clean up. If None, cleans default temp path.
        """
        cleanup_path = Path(temp_dir) if temp_dir else self.temp_path
        
        if not cleanup_path.exists():
            return
        
        try:
            # Remove all files and subdirectories in temp path
            for item in cleanup_path.iterdir():
                if item.is_file():
                    item.unlink()
                    logger.debug(f"Removed temp file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.debug(f"Removed temp directory: {item}")
            
            logger.info(f"Cleaned up temporary files in: {cleanup_path}")
            
        except OSError as e:
            logger.error(f"Failed to cleanup temporary files in {cleanup_path}: {e}")
    
    def backup_zip_file(self, zip_file_path: str, zip_filename: str) -> str:
        """Backup ZIP file to permanent storage before cleanup.
        
        Args:
            zip_file_path: Path to the temporary ZIP file
            zip_filename: Original ZIP filename
            
        Returns:
            str: Path to the backed up ZIP file
            
        Raises:
            OSError: If backup operation fails
        """
        try:
            # Create timestamped backup filename to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{timestamp}_{zip_filename}"
            backup_file_path = self.zip_backup_path / backup_filename
            
            # Copy ZIP file to backup location
            shutil.copy2(zip_file_path, backup_file_path)
            
            logger.info(f"Successfully backed up ZIP file: {zip_filename} -> {backup_file_path}")
            return str(backup_file_path)
            
        except Exception as e:
            logger.error(f"Failed to backup ZIP file {zip_filename}: {e}")
            raise OSError(f"ZIP backup failed: {e}")
    
    def cleanup_expired_files(self, retention_days: Optional[int] = None) -> int:
        """Clean up CSV files older than retention period.
        
        Args:
            retention_days: Number of days to retain files (uses config default if None)
            
        Returns:
            int: Number of files cleaned up
        """
        if not self.local_storage_path.exists():
            return 0
        
        # Use provided retention_days or fall back to config
        days_to_keep = retention_days if retention_days is not None else self.retention_config.csv_retention_days
        
        # If retention is disabled (0 days), skip cleanup
        if days_to_keep <= 0:
            logger.info("CSV file retention is disabled - skipping cleanup")
            return 0
            
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        try:
            # Walk through all subdirectories
            for csv_file in self.local_storage_path.rglob("*.csv"):
                if csv_file.is_file():
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        csv_file.unlink()
                        logger.debug(f"Removed expired CSV file: {csv_file}")
                        cleaned_count += 1
            
            # Clean up empty date directories
            for date_dir in self.local_storage_path.iterdir():
                if date_dir.is_dir() and not any(date_dir.iterdir()):
                    date_dir.rmdir()
                    logger.debug(f"Removed empty directory: {date_dir}")
            
            logger.info(f"Cleaned up {cleaned_count} expired CSV files (older than {retention_days} days)")
            return cleaned_count
            
        except OSError as e:
            logger.error(f"Failed to cleanup expired files: {e}")
            return 0
    
    def cleanup_expired_zip_backups(self, retention_days: Optional[int] = None) -> int:
        """Clean up ZIP backup files older than retention period.
        
        Args:
            retention_days: Number of days to retain ZIP backups (uses config default if None)
            
        Returns:
            int: Number of ZIP backup files cleaned up
        """
        if not self.zip_backup_path.exists():
            return 0
        
        # Use provided retention_days or fall back to config
        days_to_keep = retention_days if retention_days is not None else self.retention_config.zip_backup_retention_days
        
        # If retention is disabled (0 days), skip cleanup
        if days_to_keep <= 0:
            logger.info("ZIP backup retention is disabled - skipping cleanup")
            return 0
            
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        try:
            # Clean up ZIP backup files
            for zip_file in self.zip_backup_path.glob("*.zip"):
                try:
                    file_mtime = datetime.fromtimestamp(zip_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        zip_file.unlink()
                        logger.debug(f"Removed expired ZIP backup: {zip_file}")
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process ZIP backup file {zip_file}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} expired ZIP backup files (older than {days_to_keep} days)")
            return cleaned_count
            
        except OSError as e:
            logger.error(f"Failed to cleanup expired ZIP backups: {e}")
            return 0
    
    def get_csv_storage_info(self) -> dict:
        """Get information about CSV storage usage.
        
        Returns:
            dict: Storage information including file count and total size
        """
        if not self.local_storage_path.exists():
            return {"file_count": 0, "total_size_mb": 0.0, "oldest_file": None, "newest_file": None}
        
        csv_files = list(self.local_storage_path.rglob("*.csv"))
        
        if not csv_files:
            return {"file_count": 0, "total_size_mb": 0.0, "oldest_file": None, "newest_file": None}
        
        total_size = sum(f.stat().st_size for f in csv_files)
        file_times = [(f, datetime.fromtimestamp(f.stat().st_mtime)) for f in csv_files]
        
        oldest_file = min(file_times, key=lambda x: x[1])
        newest_file = max(file_times, key=lambda x: x[1])
        
        return {
            "file_count": len(csv_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file": {
                "path": str(oldest_file[0]),
                "date": oldest_file[1].isoformat()
            },
            "newest_file": {
                "path": str(newest_file[0]),
                "date": newest_file[1].isoformat()
            }
        }
    
    def create_temp_directory(self, prefix: str = "processing_") -> str:
        """Create a temporary directory for processing operations.
        
        Args:
            prefix: Prefix for the temporary directory name
            
        Returns:
            str: Path to the created temporary directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_dir = self.temp_path / f"{prefix}{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Created temporary directory: {temp_dir}")
        return str(temp_dir)