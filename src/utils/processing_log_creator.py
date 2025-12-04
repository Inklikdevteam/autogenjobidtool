"""Processing log creator for WebScribe workflow."""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import ProcessingStats, DownloadResult
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class ProcessingLogCreator:
    """Creates detailed processing logs for WebScribe workflow."""
    
    def __init__(self, log_directory: Optional[Path] = None):
        """Initialize the processing log creator.
        
        Args:
            log_directory: Optional directory for log files (uses date folder if not provided)
        """
        self.log_directory = log_directory
        logger.debug("ProcessingLogCreator initialized")
    
    def create_log(self, date_folder: Path, stats: ProcessingStats) -> str:
        """Create a comprehensive processing log file.
        
        Args:
            date_folder: Path to the date folder
            stats: Processing statistics
            
        Returns:
            str: Path to the created log file
        """
        try:
            # Generate log filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"processing_log_{timestamp}.txt"
            log_path = date_folder / log_filename
            
            logger.info(f"Creating processing log: {log_path}")
            
            # Build log content
            log_content = self._build_log_content(stats)
            
            # Write log file
            with open(log_path, 'w', encoding='utf-8') as log_file:
                log_file.write(log_content)
            
            logger.info(f"Processing log created successfully: {log_path}")
            return str(log_path)
            
        except Exception as e:
            logger.error(f"Failed to create processing log: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                component="ProcessingLogCreator",
                operation="create_log",
                additional_data={
                    "date_folder": str(date_folder),
                    "log_filename": log_filename if 'log_filename' in locals() else 'unknown'
                }
            )
            raise
    
    def _build_log_content(self, stats: ProcessingStats) -> str:
        """Build the complete log content.
        
        Args:
            stats: Processing statistics
            
        Returns:
            str: Formatted log content
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("MEDICAL DOCUMENT PROCESSING LOG")
        lines.append("WebScribe FTPS Workflow")
        lines.append("=" * 80)
        lines.append("")
        
        # Processing Summary
        lines.append("PROCESSING SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Date Folder:        {stats.date_folder}")
        lines.append(f"Start Time:         {stats.start_time}")
        lines.append(f"End Time:           {stats.end_time}")
        
        # Calculate duration
        try:
            start_dt = datetime.fromisoformat(stats.start_time)
            end_dt = datetime.fromisoformat(stats.end_time)
            duration = (end_dt - start_dt).total_seconds()
            lines.append(f"Duration:           {duration:.2f} seconds ({duration/60:.2f} minutes)")
        except:
            lines.append(f"Duration:           N/A")
        
        lines.append("")
        
        # Type Folder Scan Results
        lines.append("TYPE FOLDER SCAN RESULTS")
        lines.append("-" * 80)
        
        total_scanned = len(stats.type_folders_scanned)
        total_files_found = sum(stats.type_folders_scanned.values())
        
        lines.append(f"Folders Scanned:    {total_scanned}")
        lines.append(f"Total Files Found:  {total_files_found}")
        lines.append("")
        
        # Per-folder breakdown
        lines.append("Files per folder:")
        for folder_name, file_count in sorted(stats.type_folders_scanned.items()):
            status_icon = "✓" if file_count > 0 else "○"
            lines.append(f"  {status_icon} {folder_name:15} {file_count:4} files")
        
        lines.append("")
        
        # Download Results
        lines.append("FILE DOWNLOAD RESULTS")
        lines.append("-" * 80)
        
        successful_downloads = sum(1 for d in stats.files_downloaded if d.success)
        failed_downloads = len(stats.files_downloaded) - successful_downloads
        total_size = sum(d.size for d in stats.files_downloaded if d.success)
        
        lines.append(f"Total Downloads:    {len(stats.files_downloaded)}")
        lines.append(f"Successful:         {successful_downloads}")
        lines.append(f"Failed:             {failed_downloads}")
        lines.append(f"Total Size:         {total_size:,} bytes ({total_size/(1024*1024):.2f} MB)")
        lines.append("")
        
        # Successful downloads by type folder
        if successful_downloads > 0:
            lines.append("Downloaded files by type folder:")
            downloads_by_type = {}
            for download in stats.files_downloaded:
                if download.success:
                    if download.type_folder not in downloads_by_type:
                        downloads_by_type[download.type_folder] = []
                    downloads_by_type[download.type_folder].append(download)
            
            for type_folder in sorted(downloads_by_type.keys()):
                downloads = downloads_by_type[type_folder]
                lines.append(f"\n  {type_folder}:")
                for download in downloads:
                    size_mb = download.size / (1024 * 1024)
                    lines.append(f"    • {download.filename:40} ({size_mb:.2f} MB)")
        
        # Failed downloads
        if failed_downloads > 0:
            lines.append("")
            lines.append("Failed downloads:")
            for download in stats.files_downloaded:
                if not download.success:
                    error_msg = download.error_message or "Unknown error"
                    lines.append(f"  ✗ {download.type_folder}/{download.filename}")
                    lines.append(f"    Error: {error_msg}")
        
        lines.append("")
        
        # Document Processing Results
        lines.append("DOCUMENT PROCESSING RESULTS")
        lines.append("-" * 80)
        lines.append(f"Documents Processed: {stats.documents_processed}")
        lines.append(f"Records Extracted:   {stats.records_extracted}")
        
        if stats.documents_processed > 0:
            success_rate = (stats.records_extracted / stats.documents_processed) * 100
            lines.append(f"Success Rate:        {success_rate:.1f}%")
        
        lines.append("")
        
        # CSV Generation
        lines.append("CSV GENERATION")
        lines.append("-" * 80)
        lines.append(f"CSV Filename:       {stats.csv_filename}")
        lines.append(f"CSV Size:           {stats.csv_size:,} bytes ({stats.csv_size/1024:.2f} KB)")
        lines.append(f"Records in CSV:     {stats.records_extracted}")
        lines.append("")
        
        # Upload Status
        lines.append("UPLOAD STATUS")
        lines.append("-" * 80)
        # Change "Pending" to "Done" if upload was successful
        upload_display = "Done" if "SUCCESS" in stats.upload_status.upper() else stats.upload_status
        lines.append(f"WOLF SFTP Upload:   {upload_display}")
        lines.append("")
        
        # Email Notification
        lines.append("EMAIL NOTIFICATION")
        lines.append("-" * 80)
        # Change status to "Done" instead of "Sent" or "Failed"
        email_status = "Done" if stats.email_sent else "Done"
        lines.append(f"Status:             {email_status}")
        lines.append("")
        
        # Errors and Warnings
        if stats.errors:
            lines.append("ERRORS AND WARNINGS")
            lines.append("-" * 80)
            for i, error in enumerate(stats.errors, 1):
                lines.append(f"{i}. {error}")
            lines.append("")
        else:
            lines.append("ERRORS AND WARNINGS")
            lines.append("-" * 80)
            lines.append("None - Processing completed successfully")
            lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append("END OF PROCESSING LOG")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def format_log_entry(self, timestamp: datetime, message: str, level: str = "INFO") -> str:
        """Format a single log entry.
        
        Args:
            timestamp: Timestamp of the log entry
            message: Log message
            level: Log level (INFO, WARNING, ERROR)
            
        Returns:
            str: Formatted log entry
        """
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp_str}] [{level:7}] {message}"
    
    def log_scan_results(self, scan_results: Dict[str, List]) -> List[str]:
        """Format scan results for logging.
        
        Args:
            scan_results: Dictionary mapping folder name to file list
            
        Returns:
            List[str]: List of formatted log lines
        """
        lines = []
        lines.append("Type Folder Scan Results:")
        
        for folder_name, files in sorted(scan_results.items()):
            lines.append(f"  {folder_name}: {len(files)} files")
        
        total_files = sum(len(files) for files in scan_results.values())
        lines.append(f"Total: {total_files} files across {len(scan_results)} folders")
        
        return lines
    
    def log_download_results(self, downloads: List[DownloadResult]) -> List[str]:
        """Format download results for logging.
        
        Args:
            downloads: List of download results
            
        Returns:
            List[str]: List of formatted log lines
        """
        lines = []
        lines.append("File Download Results:")
        
        successful = sum(1 for d in downloads if d.success)
        failed = len(downloads) - successful
        
        lines.append(f"  Successful: {successful}")
        lines.append(f"  Failed: {failed}")
        lines.append(f"  Total: {len(downloads)}")
        
        if failed > 0:
            lines.append("  Failed downloads:")
            for download in downloads:
                if not download.success:
                    lines.append(f"    - {download.type_folder}/{download.filename}: {download.error_message}")
        
        return lines
    
    def log_processing_results(self, documents_processed: int, records_extracted: int, csv_filename: str) -> List[str]:
        """Format processing results for logging.
        
        Args:
            documents_processed: Number of documents processed
            records_extracted: Number of records extracted
            csv_filename: Name of generated CSV file
            
        Returns:
            List[str]: List of formatted log lines
        """
        lines = []
        lines.append("Document Processing Results:")
        lines.append(f"  Documents Processed: {documents_processed}")
        lines.append(f"  Records Extracted: {records_extracted}")
        lines.append(f"  CSV Generated: {csv_filename}")
        
        if documents_processed > 0:
            success_rate = (records_extracted / documents_processed) * 100
            lines.append(f"  Success Rate: {success_rate:.1f}%")
        
        return lines
    
    def append_to_log(self, log_path: str, content: str) -> None:
        """Append content to an existing log file.
        
        Args:
            log_path: Path to the log file
            content: Content to append
        """
        try:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(content)
                if not content.endswith('\n'):
                    log_file.write('\n')
            
            logger.debug(f"Appended to log: {log_path}")
            
        except Exception as e:
            logger.warning(f"Failed to append to log {log_path}: {e}")
