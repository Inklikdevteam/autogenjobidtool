"""Main processing controller for the WebScribe medical document processing system."""

import os
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import ConfigManager
from config.models import ProcessingStats, DownloadResult, ActionResult
from ftps.ftps_manager import FTPSManager, FTPSError
from sftp.manager import SFTPManager, SFTPError
from parser.document_parser import DocumentParser
from utils.csv_generator import CSVGenerator
from utils.date_folder_manager import DateFolderManager
from utils.type_folder_scanner import TypeFolderScanner
from utils.processing_log_creator import ProcessingLogCreator
from utils.parallel_action_executor import ParallelActionExecutor
from email_notifier.notifier import EmailNotifier
from utils.error_handler import (
    get_error_handler, handle_error, execute_with_retry,
    ErrorCategory, ErrorSeverity
)
from utils.logging_config import get_logging_manager


logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass


class MainController:
    """Main controller that orchestrates the WebScribe FTPS workflow."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the main controller with all required components.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        
        # Get configurations
        self.source_ftps_config = config_manager.get_source_ftps_config()
        self.dest_sftp_config = config_manager.get_dest_sftp_config()
        self.storage_config = config_manager.get_storage_config()
        self.retention_config = config_manager.get_retention_config()
        self.type_folder_config = config_manager.get_type_folder_config()
        self.date_folder_config = config_manager.get_date_folder_config()
        
        # Initialize components
        self.ftps_manager = FTPSManager()
        self.sftp_manager = SFTPManager()
        self.document_parser = DocumentParser()
        self.csv_generator = CSVGenerator(self.storage_config, self.retention_config)
        self.email_notifier = EmailNotifier(config_manager.get_email_config())
        
        # Initialize WebScribe workflow components
        self.date_folder_manager = DateFolderManager(
            base_path=self.date_folder_config['base_path'],
            use_yesterday_date=self.date_folder_config['use_yesterday_date']
        )
        self.type_folder_scanner = TypeFolderScanner(self.type_folder_config.folders)
        self.processing_log_creator = ProcessingLogCreator()
        self.parallel_executor = ParallelActionExecutor(max_workers=3)
        
        # Get performance logger
        self.logging_manager = get_logging_manager()
        self.performance_logger = self.logging_manager.get_performance_logger()
        
        # Initialize backup directory
        self.backup_path = Path(self.storage_config.local_storage_path) / "folder-backup"
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("MainController initialized successfully for WebScribe workflow")
        logger.info(f"Type folders configured: {', '.join(self.type_folder_config.folders)}")
        logger.info(f"Backup directory: {self.backup_path}")
    
    def run_processing_cycle(self) -> ProcessingStats:
        """Run a complete WebScribe processing cycle.
        
        Returns:
            ProcessingStats: Statistics for the processing cycle
            
        Raises:
            ProcessingError: If critical processing errors occur
        """
        cycle_start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("Starting WebScribe processing cycle")
        logger.info("=" * 80)
        
        try:
            # Step 1: Create date folder
            logger.info("Step 1: Creating date folder")
            date_folder = self._create_date_folder()
            logger.info(f"Date folder created: {date_folder}")
            
            # Step 2: Connect to WebScribe FTPS and scan type folders
            logger.info("Step 2: Connecting to WebScribe FTPS and scanning type folders")
            scan_results = self._scan_type_folders()
            
            total_files = sum(len(files) for files in scan_results.values())
            logger.info(f"Scan complete: {total_files} files found across {len(scan_results)} type folders")
            
            if total_files == 0:
                logger.info("No files found to process")
                return self._build_empty_stats(date_folder, cycle_start_time)
            
            # Step 3: Download files to date folder
            logger.info("Step 3: Downloading files to date folder")
            download_results = self._download_files_to_date_folder(scan_results, date_folder)
            
            successful_downloads = sum(1 for d in download_results if d.success)
            logger.info(f"Downloaded {successful_downloads}/{len(download_results)} files successfully")
            
            if successful_downloads == 0:
                logger.warning("No files downloaded successfully")
                return self._build_empty_stats(date_folder, cycle_start_time)
            
            # Step 4: Process documents and generate CSV
            logger.info("Step 4: Processing documents and generating CSV")
            medical_records, csv_path = self._process_documents_and_generate_csv(date_folder)
            
            logger.info(f"Processed {len(medical_records)} records, CSV generated: {csv_path}")
            
            # Step 5: Execute parallel actions (upload CSV, create log, send email)
            logger.info("Step 5: Executing parallel actions (CSV upload, log creation, email)")
            
            # Build processing stats
            stats = self._build_processing_stats(
                date_folder=date_folder,
                start_time=cycle_start_time,
                scan_results=scan_results,
                download_results=download_results,
                medical_records=medical_records,
                csv_path=csv_path
            )
            
            # Execute parallel actions
            action_results = self._execute_parallel_actions(date_folder, csv_path, stats)
            
            # Update stats with action results
            stats.upload_status = self._get_upload_status(action_results)
            stats.email_sent = self._get_email_status(action_results)
            stats.log_filename = self._get_log_filename(action_results, date_folder)
            stats.end_time = datetime.now().isoformat()
            
            # Log completion
            cycle_duration = (datetime.now() - cycle_start_time).total_seconds()
            logger.info("=" * 80)
            logger.info(f"Processing cycle completed successfully in {cycle_duration:.2f} seconds")
            logger.info(f"  • Files scanned: {total_files}")
            logger.info(f"  • Files downloaded: {successful_downloads}")
            logger.info(f"  • Records extracted: {len(medical_records)}")
            logger.info(f"  • CSV generated: {os.path.basename(csv_path)}")
            logger.info(f"  • Upload status: {stats.upload_status}")
            logger.info(f"  • Email sent: {stats.email_sent}")
            logger.info("=" * 80)
            
            # Step 6: Backup the date folder
            logger.info("Step 6: Backing up date folder")
            self._backup_date_folder(date_folder)
            
            # Log performance metrics
            if self.performance_logger:
                self.logging_manager.log_performance(
                    operation="webscribe_processing_cycle",
                    duration=cycle_duration,
                    additional_data={
                        "files_scanned": total_files,
                        "files_downloaded": successful_downloads,
                        "records_extracted": len(medical_records),
                        "csv_filename": os.path.basename(csv_path),
                        "upload_status": stats.upload_status
                    }
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"Critical error in processing cycle: {e}", exc_info=True)
            
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                component="MainController",
                operation="run_processing_cycle",
                additional_data={
                    "cycle_duration": (datetime.now() - cycle_start_time).total_seconds()
                }
            )
            
            # Send failure notification
            try:
                self.email_notifier.send_failure_notification(
                    zip_filename="WebScribe Processing Cycle",
                    error_message=f"Critical error: {str(e)}"
                )
            except Exception as email_error:
                logger.error(f"Failed to send failure notification: {email_error}")
            
            raise ProcessingError(f"Processing cycle failed: {e}")
    
    def _create_date_folder(self) -> Path:
        """Create date folder for processing.
        
        Returns:
            Path: Path to created date folder
        """
        try:
            date_folder = self.date_folder_manager.create_date_folder()
            logger.debug(f"Date folder created: {date_folder}")
            return date_folder
            
        except Exception as e:
            logger.error(f"Failed to create date folder: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                component="MainController",
                operation="create_date_folder"
            )
            raise
    
    def _scan_type_folders(self) -> dict:
        """Scan all type folders on WebScribe FTPS.
        
        Returns:
            dict: Scan results mapping folder name to file list (filtered for document files only)
        """
        try:
            with self.ftps_manager.connect_ftps(self.source_ftps_config) as ftps_client:
                scan_results = self.type_folder_scanner.scan_folders(
                    ftps_client,
                    self.source_ftps_config.remote_path
                )
                
                # Log statistics before filtering
                stats = self.type_folder_scanner.get_scan_statistics(scan_results)
                logger.info(f"Scan statistics (before filtering): {stats['total_files_found']} files, "
                          f"{stats['folders_with_files']} folders with files, "
                          f"{stats['total_size_mb']} MB total")
                
                # Filter for document files only (.doc, .docx)
                filtered_results = {}
                total_filtered = 0
                for type_folder, files in scan_results.items():
                    filtered_files = self.type_folder_scanner.filter_document_files(files)
                    filtered_results[type_folder] = filtered_files
                    total_filtered += len(filtered_files)
                    if len(files) != len(filtered_files):
                        logger.info(f"Filtered {type_folder}: {len(filtered_files)}/{len(files)} files are documents")
                
                logger.info(f"Total files after filtering: {total_filtered} document files")
                
                return filtered_results
                
        except Exception as e:
            logger.error(f"Failed to scan type folders: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SFTP_CONNECTION,
                severity=ErrorSeverity.CRITICAL,
                component="MainController",
                operation="scan_type_folders"
            )
            raise
    
    def _download_files_to_date_folder(self, scan_results: dict, date_folder: Path) -> List[DownloadResult]:
        """Download all files from scan results to date folder.
        
        Args:
            scan_results: Scan results from type folder scanner
            date_folder: Path to date folder
            
        Returns:
            List[DownloadResult]: Download results for each file
        """
        download_results = []
        
        # Extract target date from folder name (format: YYYY-MM-DD)
        folder_name = date_folder.name
        try:
            target_date = datetime.strptime(folder_name, '%Y-%m-%d').date()
            logger.info(f"Filtering files for date: {target_date}")
        except ValueError:
            logger.warning(f"Could not parse date from folder name '{folder_name}', downloading all files")
            target_date = None
        
        try:
            with self.ftps_manager.connect_ftps(self.source_ftps_config) as ftps_client:
                for type_folder, files in scan_results.items():
                    if not files:
                        continue
                    
                    # Filter files by modification date if target_date is set
                    if target_date:
                        filtered_files = []
                        for file_info in files:
                            file_date = file_info.mtime.date()
                            if file_date == target_date:
                                filtered_files.append(file_info)
                                logger.info(f"✓ File matches date: {file_info.filename} (modified: {file_info.mtime})")
                            else:
                                logger.info(f"✗ File skipped (wrong date): {file_info.filename} (modified: {file_info.mtime}, expected: {target_date})")
                        
                        files = filtered_files
                        logger.info(f"Filtered to {len(files)} files matching date {target_date} from {type_folder}")
                    
                    if not files:
                        logger.info(f"No files to download from {type_folder} for date {target_date}")
                        continue
                    
                    # Create type subfolder
                    type_subfolder = self.date_folder_manager.organize_by_type(date_folder, type_folder)
                    logger.info(f"Downloading {len(files)} files from {type_folder}")
                    
                    for file_info in files:
                        try:
                            # Download file
                            local_path = type_subfolder / file_info.filename
                            
                            self.ftps_manager.download_file(
                                ftps_client,
                                file_info.full_path,
                                str(local_path)
                            )
                            
                            download_results.append(DownloadResult(
                                type_folder=type_folder,
                                filename=file_info.filename,
                                size=file_info.size,
                                success=True,
                                error_message=None
                            ))
                            
                            logger.debug(f"✓ Downloaded: {type_folder}/{file_info.filename}")
                            
                        except Exception as e:
                            logger.warning(f"✗ Failed to download {type_folder}/{file_info.filename}: {e}")
                            
                            download_results.append(DownloadResult(
                                type_folder=type_folder,
                                filename=file_info.filename,
                                size=file_info.size if hasattr(file_info, 'size') else 0,
                                success=False,
                                error_message=str(e)
                            ))
                            
                            handle_error(
                                error=e,
                                category=ErrorCategory.SFTP_FILE_OPERATION,
                                severity=ErrorSeverity.MEDIUM,
                                component="MainController",
                                operation="download_file",
                                additional_data={
                                    "type_folder": type_folder,
                                    "filename": file_info.filename
                                }
                            )
            
            return download_results
            
        except Exception as e:
            logger.error(f"Failed during file downloads: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SFTP_CONNECTION,
                severity=ErrorSeverity.HIGH,
                component="MainController",
                operation="download_files_to_date_folder"
            )
            raise
    
    def _process_documents_and_generate_csv(self, date_folder: Path) -> tuple:
        """Process all documents in date folder and generate CSV.
        
        Args:
            date_folder: Path to date folder
            
        Returns:
            tuple: (list of medical records, path to CSV file)
        """
        try:
            # Process all documents in date folder
            logger.info("Processing documents from date folder")
            medical_records = []
            
            # Walk through all type subfolders
            for type_subfolder in date_folder.iterdir():
                if not type_subfolder.is_dir():
                    continue
                
                logger.debug(f"Processing documents from {type_subfolder.name}")
                
                # Process each document file
                for doc_file in type_subfolder.iterdir():
                    if doc_file.is_file() and doc_file.suffix.lower() in ['.doc', '.docx']:
                        try:
                            # Extract text
                            text = self.document_parser.extract_text_from_document(str(doc_file))
                            
                            # Parse medical fields (even if text is empty, to include all files in CSV)
                            record = self.document_parser.parse_medical_fields(text, doc_file.name)
                            medical_records.append(record)
                            logger.debug(f"✓ Processed: {doc_file.name}")
                            
                            if not text:
                                logger.warning(f"⚠ No text extracted from: {doc_file.name} (included in CSV with available fields)")
                                
                        except Exception as e:
                            logger.warning(f"✗ Failed to process {doc_file.name}: {e}")
                            handle_error(
                                error=e,
                                category=ErrorCategory.DOCUMENT_PARSING,
                                severity=ErrorSeverity.MEDIUM,
                                component="MainController",
                                operation="process_document",
                                additional_data={"filename": doc_file.name}
                            )
            
            logger.info(f"Extracted {len(medical_records)} medical records")
            
            # Generate CSV
            if medical_records:
                # Use date folder name for CSV filename (e.g., "2025-11-24" -> "20251124_output.csv")
                date_folder_name = date_folder.name.replace('-', '')
                csv_filename = f"{date_folder_name}_output.csv"
                csv_path = date_folder / csv_filename
                
                # Write CSV directly to date folder
                import csv
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.csv_generator.CSV_COLUMNS)
                    writer.writeheader()
                    
                    for record in medical_records:
                        row_data = {
                            'source_file': record.source_file,
                            'first_name': record.first_name,
                            'last_name': record.last_name,
                            'date_of_birth': record.date_of_birth,
                            'record_number': record.record_number,
                            'case_number': record.case_number,
                            'accident_date/Injury_date': record.accident_date,
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
                
                logger.info(f"CSV generated: {csv_path}")
                
                return medical_records, str(csv_path)
            else:
                logger.warning("No medical records extracted, creating empty CSV")
                # Create empty CSV with headers
                csv_filename = f"{date_folder.name.replace('-', '')}_output.csv"
                csv_path = date_folder / csv_filename
                
                import csv
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.csv_generator.CSV_COLUMNS)
                    writer.writeheader()
                
                return [], str(csv_path)
                
        except Exception as e:
            logger.error(f"Failed to process documents and generate CSV: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.HIGH,
                component="MainController",
                operation="process_documents_and_generate_csv"
            )
            raise
    
    def _execute_parallel_actions(self, date_folder: Path, csv_path: str, stats: ProcessingStats) -> List[ActionResult]:
        """Execute CSV upload, log creation, and email notification in parallel.
        
        Args:
            date_folder: Path to date folder
            csv_path: Path to CSV file
            stats: Processing statistics
            
        Returns:
            List[ActionResult]: Results of parallel actions
        """
        # First, execute upload and log creation in parallel
        initial_actions = [
            {
                'name': 'upload_csv',
                'function': lambda: self.parallel_executor.upload_csv_action(
                    csv_path, self.sftp_manager, self.dest_sftp_config
                )
            },
            {
                'name': 'create_log',
                'function': lambda: self.parallel_executor.create_log_action(
                    date_folder, stats, self.processing_log_creator
                )
            }
        ]
        
        initial_results = self.parallel_executor.execute_parallel(initial_actions)
        
        # Update stats with upload status and log filename before sending email
        stats.upload_status = self._get_upload_status(initial_results)
        stats.log_filename = self._get_log_filename(initial_results, date_folder)
        
        # Now send email with updated stats
        email_action = {
            'name': 'send_email',
            'function': lambda: self.parallel_executor.send_email_action(
                stats, self.email_notifier
            )
        }
        
        email_result = self.parallel_executor.execute_parallel([email_action])
        
        # Combine all results
        results = initial_results + email_result
        
        # Log summary
        summary = self.parallel_executor.get_execution_summary(results)
        logger.info(f"Parallel actions complete: {summary['successful']}/{summary['total_actions']} successful")
        
        return results
    
    def _build_processing_stats(self, date_folder: Path, start_time: datetime, 
                                scan_results: dict, download_results: List[DownloadResult],
                                medical_records: list, csv_path: str) -> ProcessingStats:
        """Build processing statistics object.
        
        Args:
            date_folder: Path to date folder
            start_time: Processing start time
            scan_results: Type folder scan results
            download_results: File download results
            medical_records: Extracted medical records
            csv_path: Path to generated CSV
            
        Returns:
            ProcessingStats: Processing statistics
        """
        # Calculate type folders scanned
        type_folders_scanned = {folder: len(files) for folder, files in scan_results.items()}
        
        # Get CSV size
        csv_size = os.path.getsize(csv_path) if os.path.exists(csv_path) else 0
        
        # Collect errors
        errors = []
        for download in download_results:
            if not download.success and download.error_message:
                errors.append(f"Download failed: {download.type_folder}/{download.filename} - {download.error_message}")
        
        stats = ProcessingStats(
            date_folder=str(date_folder.name),
            start_time=start_time.isoformat(),
            end_time=datetime.now().isoformat(),
            type_folders_scanned=type_folders_scanned,
            files_downloaded=download_results,
            documents_processed=len(download_results),
            records_extracted=len(medical_records),
            csv_filename=os.path.basename(csv_path),
            csv_size=csv_size,
            upload_status="Pending",
            log_filename="",
            email_sent=False,
            errors=errors
        )
        
        return stats
    
    def _build_empty_stats(self, date_folder: Path, start_time: datetime) -> ProcessingStats:
        """Build empty processing statistics when no files are processed.
        
        Args:
            date_folder: Path to date folder
            start_time: Processing start time
            
        Returns:
            ProcessingStats: Empty processing statistics
        """
        return ProcessingStats(
            date_folder=str(date_folder.name),
            start_time=start_time.isoformat(),
            end_time=datetime.now().isoformat(),
            type_folders_scanned={},
            files_downloaded=[],
            documents_processed=0,
            records_extracted=0,
            csv_filename="",
            csv_size=0,
            upload_status="N/A - No files",
            log_filename="",
            email_sent=False,
            errors=[]
        )
    
    def _get_upload_status(self, action_results: List[ActionResult]) -> str:
        """Get upload status from action results.
        
        Args:
            action_results: List of action results
            
        Returns:
            str: Upload status
        """
        for result in action_results:
            if result.action_name == 'upload_csv':
                return "SUCCESS" if result.success else f"FAILED: {result.error_message}"
        return "UNKNOWN"
    
    def _get_email_status(self, action_results: List[ActionResult]) -> bool:
        """Get email status from action results.
        
        Args:
            action_results: List of action results
            
        Returns:
            bool: True if email was sent successfully
        """
        for result in action_results:
            if result.action_name == 'send_email':
                return result.success
        return False
    
    def _get_log_filename(self, action_results: List[ActionResult], date_folder: Path) -> str:
        """Get log filename from action results.
        
        Args:
            action_results: List of action results
            date_folder: Path to date folder
            
        Returns:
            str: Log filename
        """
        for result in action_results:
            if result.action_name == 'create_log' and result.success:
                # Find the log file in date folder
                for file in date_folder.glob("processing_log_*.txt"):
                    return file.name
        return ""

    def _backup_date_folder(self, date_folder: Path) -> None:
        """Backup the date folder to folder-backup directory.
        
        Args:
            date_folder: Path to the date folder to backup
        """
        try:
            import shutil
            
            # Create backup folder name with timestamp
            folder_name = date_folder.name
            backup_folder = self.backup_path / folder_name
            
            # If backup already exists, remove it first
            if backup_folder.exists():
                shutil.rmtree(backup_folder)
                logger.debug(f"Removed existing backup: {backup_folder}")
            
            # Copy the entire date folder to backup
            shutil.copytree(date_folder, backup_folder)
            
            # Calculate backup size
            total_size = sum(f.stat().st_size for f in backup_folder.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            logger.info(f"✓ Backup created: {backup_folder} ({size_mb:.2f} MB)")
            
        except Exception as e:
            logger.warning(f"Failed to backup date folder {date_folder}: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.LOW,
                component="MainController",
                operation="backup_date_folder",
                additional_data={"date_folder": str(date_folder)}
            )
