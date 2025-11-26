"""Configuration data models for the medical document processing system."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SFTPConfig:
    """Configuration for SFTP server connection."""
    host: str
    port: int
    username: str
    password: str
    remote_path: str


@dataclass
class FTPSConfig:
    """Configuration for FTPS server connection (FTP with TLS/SSL)."""
    host: str
    port: int
    username: str
    password: str
    remote_path: str
    use_tls: bool = True
    passive_mode: bool = True


@dataclass
class TypeFolderConfig:
    """Configuration for type folders to scan."""
    folders: List[str]
    base_path: str = "/"


@dataclass
class EmailConfig:
    """Configuration for email notifications."""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    admin_email: str
    admin_emails: List[str] = None  # Support for multiple emails
    smtp_from: Optional[str] = None  # From email address (optional, defaults to smtp_username)


@dataclass
class ScheduleConfig:
    """Configuration for scheduling system."""
    poll_interval_seconds: int = 60
    poll_cron: Optional[str] = None
    timezone: str = "UTC"


@dataclass
class StorageConfig:
    """Configuration for local storage paths."""
    local_storage_path: str
    temp_path: str
    zip_backup_path: str


@dataclass
class RetentionConfig:
    """Configuration for file retention policies.
    
    Set any retention value to 0 to disable automatic cleanup for that file type.
    """
    csv_retention_days: int = 0  # 0 = disabled
    log_retention_days: int = 0  # 0 = disabled
    error_log_retention_days: int = 0  # 0 = disabled
    processing_records_retention_days: int = 0  # 0 = disabled
    zip_backup_retention_days: int = 0  # 0 = disabled


@dataclass
class MedicalRecord:
    """Data model for extracted medical record information."""
    source_file: str
    first_name: str = ""
    last_name: str = ""
    date_of_birth: str = ""
    record_number: str = ""
    case_number: str = ""
    accident_date: str = ""
    provider_first: str = ""
    provider_last: str = ""
    exam_date: str = ""
    exam_place: str = ""
    transcriptionist: str = ""
    dd_date: str = ""
    transcription_date: str = ""
    job_number: str = ""
    case_code: str = ""


@dataclass
class ProcessingResult:
    """Data model for tracking processing outcomes."""
    zip_filename: str
    total_documents: int
    successful_extractions: int
    failed_extractions: int
    csv_filename: str
    processing_time: float
    errors: List[str]


@dataclass
class ProcessingRecord:
    """Data model for file processing history record."""
    filename: str
    modification_time: str  # ISO format datetime string
    processed_time: str     # ISO format datetime string
    status: str  # 'success', 'failed', 'partial'
    csv_filename: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DownloadResult:
    """Data model for file download results."""
    type_folder: str
    filename: str
    size: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class ActionResult:
    """Data model for parallel action execution results."""
    action_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None


@dataclass
class ProcessingStats:
    """Data model for WebScribe workflow processing statistics."""
    date_folder: str
    start_time: str  # ISO format datetime string
    end_time: str  # ISO format datetime string
    type_folders_scanned: dict  # folder_name -> file_count
    files_downloaded: List[DownloadResult]
    documents_processed: int
    records_extracted: int
    csv_filename: str
    csv_size: int
    upload_status: str
    log_filename: str
    email_sent: bool
    errors: List[str]