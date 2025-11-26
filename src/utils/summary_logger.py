"""Summary logging utility for generating email-style processing reports in text format."""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import ProcessingResult, StorageConfig


logger = logging.getLogger(__name__)


class SummaryLogger:
    """Generates and saves email-style processing summaries to text files."""
    
    def __init__(self, storage_config: StorageConfig):
        """Initialize the summary logger.
        
        Args:
            storage_config: Configuration for storage paths
        """
        self.storage_config = storage_config
        
        # Create main-logs directory
        self.main_logs_path = Path(storage_config.local_storage_path) / "logs" / "main-logs"
        self.main_logs_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SummaryLogger initialized with path: {self.main_logs_path}")
    
    def generate_processing_summary(self, results: List[ProcessingResult]) -> str:
        """Generate a text-based processing summary similar to email format.
        
        Args:
            results: List of processing results to summarize
            
        Returns:
            str: Formatted summary text
        """
        if not results:
            return self._generate_no_files_summary()
        
        # Calculate overall statistics
        total_files = len(results)
        total_documents = sum(r.total_documents for r in results)
        total_successful = sum(r.successful_extractions for r in results)
        total_failed = sum(r.failed_extractions for r in results)
        total_time = sum(r.processing_time for r in results)
        success_rate = (total_successful / total_documents * 100) if total_documents > 0 else 0
        
        # Generate summary text
        summary_lines = [
            "Medical Document Processing Summary",
            "=" * 50,
            "",
            f"Processing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Overall Statistics",
            "-" * 20,
            "",
            f"• ZIP files processed: {total_files}",
            f"• Total documents: {total_documents}",
            f"• Successful extractions: {total_successful}",
            f"• Failed extractions: {total_failed}",
            f"• Success rate: {success_rate:.1f}% ({total_successful}/{total_documents})",
            f"• Total processing time: {total_time:.2f} seconds",
            "",
            "File Details",
            "-" * 15,
            ""
        ]
        
        # Add table header
        summary_lines.extend([
            f"{'ZIP File':<20} {'Documents':<12} {'Successful':<12} {'Failed':<8} {'CSV Output':<25} {'Processing Time':<15}",
            "-" * 100
        ])
        
        # Add file details
        for result in results:
            summary_lines.append(
                f"{result.zip_filename:<20} "
                f"{result.total_documents:<12} "
                f"{result.successful_extractions:<12} "
                f"{result.failed_extractions:<8} "
                f"{result.csv_filename:<25} "
                f"{result.processing_time:.2f}s"
            )
        
        # Add error details if any
        errors_found = [r for r in results if r.errors]
        if errors_found:
            summary_lines.extend([
                "",
                "Error Details",
                "-" * 15,
                ""
            ])
            for result in errors_found:
                if result.errors:
                    summary_lines.append(f"{result.zip_filename}:")
                    for error in result.errors:
                        summary_lines.append(f"  • {error}")
                    summary_lines.append("")
        
        summary_lines.extend([
            "",
            "-" * 50,
            "This is an automated summary from the Medical Document Processing System.",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        return "\n".join(summary_lines)
    
    def _generate_no_files_summary(self) -> str:
        """Generate summary when no files were processed."""
        summary_lines = [
            "Medical Document Processing Summary",
            "=" * 50,
            "",
            f"Processing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Overall Statistics",
            "-" * 20,
            "",
            "• ZIP files processed: 0",
            "• Total documents: 0",
            "• Successful extractions: 0",
            "• Failed extractions: 0",
            "• Success rate: N/A",
            "• Total processing time: 0.00 seconds",
            "",
            "Status: No new or modified ZIP files found for processing.",
            "",
            "-" * 50,
            "This is an automated summary from the Medical Document Processing System.",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        return "\n".join(summary_lines)
    
    def generate_failure_summary(self, zip_filename: str, error_message: str, 
                                document_name: Optional[str] = None) -> str:
        """Generate a failure summary report.
        
        Args:
            zip_filename: Name of the ZIP file that failed
            error_message: Description of the error
            document_name: Optional specific document that failed
            
        Returns:
            str: Formatted failure summary text
        """
        summary_lines = [
            "URGENT: Medical Document Processing Failure",
            "=" * 50,
            "",
            f"Failure occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Failure Details",
            "-" * 16,
            "",
            f"• ZIP File: {zip_filename}"
        ]
        
        if document_name:
            summary_lines.append(f"• Document: {document_name}")
        
        summary_lines.extend([
            f"• Error: {error_message}",
            "",
            "Recommended Actions",
            "-" * 20,
            "",
            "• Check the source ZIP file for corruption or invalid format",
            "• Verify document contents and structure",
            "• Review system logs for additional error details",
            "• Ensure SFTP connections are stable",
            "",
            "-" * 50,
            "This is an automated failure report from the Medical Document Processing System.",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        return "\n".join(summary_lines)
    
    def save_summary_to_file(self, summary_text: str, summary_type: str = "processing", 
                           zip_filename: Optional[str] = None, csv_filename: Optional[str] = None) -> str:
        """Save summary text to a file in the main-logs directory.
        
        Args:
            summary_text: The formatted summary text to save
            summary_type: Type of summary ('processing', 'failure', 'no_files')
            zip_filename: Original ZIP file name (for processing summaries)
            csv_filename: Generated CSV file name (for processing summaries)
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Generate filename with timestamp (YYYYMMDD_HHMM format - no seconds)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            
            # Create descriptive filename based on type
            if summary_type == "processing" and zip_filename and csv_filename:
                # For ZIP files, keep the original filename (without extension)
                zip_part = zip_filename.replace('.zip', '')
                # For CSV files, extract just the date part (remove _output)
                csv_part = self._extract_date_from_filename(csv_filename)
                filename = f"{timestamp}_{zip_part}_{csv_part}_summary.txt"
            elif summary_type == "failure" and zip_filename:
                # For failure summaries, include the ZIP file date
                zip_date = self._extract_date_from_filename(zip_filename)
                filename = f"{timestamp}_{zip_date}_failure_summary.txt"
            else:
                # Default naming for no_files and other types
                filename = f"{timestamp}_{summary_type}_summary.txt"
            
            file_path = self.main_logs_path / filename
            
            # Write summary to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            
            logger.info(f"Summary saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save summary to file: {e}")
            raise
    
    def _extract_date_from_filename(self, filename: str) -> str:
        """Extract date from filename (ZIP or CSV) and convert to YYYYMMDD format.
        
        Args:
            filename: Original filename (e.g., "11092025.zip" or "20251109_output.csv")
            
        Returns:
            str: Extracted date in YYYYMMDD format
        """
        if not filename:
            return "unknown"
        
        import re
        
        # Remove file extensions and common suffixes (including _output)
        base_name = filename.replace('.zip', '').replace('.csv', '').replace('_output', '')
        
        # Find 8-digit date pattern
        match = re.search(r'(\d{8})', base_name)
        if match:
            date_str = match.group(1)
            
            # Check if it's already YYYYMMDD format (year >= 2000)
            if date_str[:4] >= '2000':
                return date_str
            
            # Otherwise, assume it's MMDDYYYY format and convert
            if len(date_str) == 8:
                mm = date_str[:2]
                dd = date_str[2:4]
                yyyy = date_str[4:8]
                
                # Validate month and day ranges
                try:
                    if 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
                        return f"{yyyy}{mm}{dd}"
                except ValueError:
                    pass
        
        # If no valid date found, return the original base name (cleaned)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', base_name)
        return clean_name if clean_name else "unknown"
    
    def log_processing_summary(self, results: List[ProcessingResult]) -> str:
        """Generate and save a processing summary.
        
        Args:
            results: List of processing results
            
        Returns:
            str: Path to the saved summary file
        """
        try:
            summary_text = self.generate_processing_summary(results)
            
            if results:
                # For processing summaries with results, use the first result's filenames
                # (or combine multiple if needed)
                if len(results) == 1:
                    # Single ZIP file processed
                    zip_filename = results[0].zip_filename
                    csv_filename = results[0].csv_filename
                else:
                    # Multiple ZIP files processed - use a combined approach
                    zip_filename = f"multiple_{len(results)}_files"
                    csv_filename = f"multiple_{len(results)}_csvs"
                
                return self.save_summary_to_file(summary_text, "processing", zip_filename, csv_filename)
            else:
                # No files processed
                return self.save_summary_to_file(summary_text, "no_files")
            
        except Exception as e:
            logger.error(f"Failed to log processing summary: {e}")
            raise
    
    def log_failure_summary(self, zip_filename: str, error_message: str, 
                           document_name: Optional[str] = None) -> str:
        """Generate and save a failure summary.
        
        Args:
            zip_filename: Name of the ZIP file that failed
            error_message: Description of the error
            document_name: Optional specific document that failed
            
        Returns:
            str: Path to the saved summary file
        """
        try:
            summary_text = self.generate_failure_summary(zip_filename, error_message, document_name)
            return self.save_summary_to_file(summary_text, "failure", zip_filename)
            
        except Exception as e:
            logger.error(f"Failed to log failure summary: {e}")
            raise
    
    def cleanup_old_summaries(self, days_to_keep: int = 30) -> int:
        """Clean up old summary files.
        
        Args:
            days_to_keep: Number of days to keep summary files
            
        Returns:
            int: Number of files cleaned up
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleaned_count = 0
            
            for summary_file in self.main_logs_path.glob("*.txt"):
                try:
                    file_mtime = datetime.fromtimestamp(summary_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        summary_file.unlink()
                        logger.debug(f"Removed old summary file: {summary_file}")
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process summary file {summary_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old summary files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old summaries: {e}")
            return 0
    
    def get_summary_files_info(self) -> dict:
        """Get information about summary files.
        
        Returns:
            dict: Information about summary files
        """
        try:
            summary_files = list(self.main_logs_path.glob("*.txt"))
            
            if not summary_files:
                return {
                    "file_count": 0,
                    "total_size_mb": 0.0,
                    "oldest_file": None,
                    "newest_file": None
                }
            
            total_size = sum(f.stat().st_size for f in summary_files)
            file_times = [(f, datetime.fromtimestamp(f.stat().st_mtime)) for f in summary_files]
            
            oldest_file = min(file_times, key=lambda x: x[1])
            newest_file = max(file_times, key=lambda x: x[1])
            
            return {
                "file_count": len(summary_files),
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
            
        except Exception as e:
            logger.error(f"Failed to get summary files info: {e}")
            return {"error": str(e)}