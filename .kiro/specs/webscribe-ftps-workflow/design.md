# Design Document

## Overview

This design document describes the architecture and implementation approach for the WebScribe FTPS workflow modification to the Medical Document Processing System. The new workflow replaces the ZIP-based processing with a date-folder-based approach that scans multiple type folders on an FTPS server.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESSING CYCLE                             │
│                                                                   │
│  1. Create Date Folder (YYYY-MM-DD)                             │
│  2. Connect to WebScribe FTPS                                    │
│  3. Scan Type Folders (type3, type6, ..., type24)              │
│  4. Download Files to Date Folder                               │
│  5. Run AutoJob Processing                                       │
│  6. Parallel Actions:                                            │
│     ├─ Upload CSV to WOLF SFTP                                  │
│     ├─ Create Processing Log                                     │
│     └─ Send Email Notification                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌──────────────────────┐
│   Main Controller    │
│  (Orchestration)     │
└──────────┬───────────┘
           │
           ├─────────────────────────────────────────────────┐
           │                                                   │
┌──────────▼───────────┐  ┌──────────────────┐  ┌───────────▼──────────┐
│  Date Folder Manager │  │  FTPS Manager    │  │  Document Parser     │
│  - Create folders    │  │  - Connect       │  │  - Extract text      │
│  - Organize files    │  │  - List files    │  │  - Parse fields      │
└──────────────────────┘  │  - Download      │  └──────────────────────┘
                          │  - Upload        │
                          └──────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
┌──────────▼───────────┐  ┌───────▼────────┐  ┌──────────▼───────────┐
│  CSV Generator       │  │  Log Creator   │  │  Email Notifier      │
│  - Generate CSV      │  │  - Create log  │  │  - Send notification │
│  - Format records    │  │  - Track stats │  │  - Format HTML       │
└──────────────────────┘  └────────────────┘  └──────────────────────┘
```

## Components and Interfaces

### 1. Date Folder Manager

**Purpose:** Manages creation and organization of date-based folders.

**Interface:**
```python
class DateFolderManager:
    def create_date_folder(self, base_path: str, date: datetime) -> Path
    def get_folder_name(self, date: datetime) -> str
    def get_yesterday_date(self) -> datetime
    def get_last_modified_date(self, files: List[FileInfo]) -> Optional[datetime]
    def organize_by_type(self, date_folder: Path, type_name: str) -> Path
```

**Key Methods:**
- `create_date_folder()`: Creates YYYY-MM-DD folder in base path
- `get_folder_name()`: Formats date as YYYY-MM-DD string
- `get_yesterday_date()`: Returns yesterday's date
- `get_last_modified_date()`: Finds most recent modification date from file list
- `organize_by_type()`: Creates type-specific subdirectories

### 2. FTPS Manager (Enhanced)

**Purpose:** Handles FTPS connections with TLS support.

**Interface:**
```python
class FTPSManager:
    def connect_ftps(self, config: SFTPConfig) -> FTPSClient
    def list_type_folders(self, client: FTPSClient, base_path: str) -> List[str]
    def list_files_in_folder(self, client: FTPSClient, folder_path: str) -> List[FileInfo]
    def download_file(self, client: FTPSClient, remote_path: str, local_path: str) -> bool
    def scan_all_type_folders(self, client: FTPSClient, type_folders: List[str]) -> Dict[str, List[FileInfo]]
```

**Key Methods:**
- `connect_ftps()`: Establishes FTPS connection with TLS
- `list_type_folders()`: Lists all type folders (type3, type6, etc.)
- `list_files_in_folder()`: Lists files directly in a folder (no subdirectories)
- `download_file()`: Downloads file with verification
- `scan_all_type_folders()`: Scans all type folders and returns file lists

**FTPS vs SFTP:**
- FTPS uses FTP protocol with TLS/SSL encryption
- Different from SFTP (SSH File Transfer Protocol)
- Requires `ftplib` with TLS support instead of `paramiko`

### 3. Type Folder Scanner

**Purpose:** Scans and processes multiple type folders.

**Interface:**
```python
class TypeFolderScanner:
    def __init__(self, type_folders: List[str])
    def scan_folders(self, ftps_client: FTPSClient, base_path: str) -> Dict[str, List[FileInfo]]
    def get_all_files(self, scan_results: Dict[str, List[FileInfo]]) -> List[Tuple[str, FileInfo]]
    def filter_document_files(self, files: List[FileInfo]) -> List[FileInfo]
```

**Key Methods:**
- `scan_folders()`: Scans all configured type folders
- `get_all_files()`: Flattens scan results into single list with type info
- `filter_document_files()`: Filters for .doc, .docx, .zip files

**Type Folders:**
- type3, type6, type7, type16, type18, type19, type20, type21, type22, type23, type24
- Configurable via TYPE_FOLDERS environment variable

### 4. Processing Log Creator

**Purpose:** Creates detailed processing logs.

**Interface:**
```python
class ProcessingLogCreator:
    def create_log(self, date_folder: Path, stats: ProcessingStats) -> str
    def format_log_entry(self, timestamp: datetime, message: str, level: str) -> str
    def log_scan_results(self, scan_results: Dict[str, List[FileInfo]]) -> None
    def log_download_results(self, downloads: List[DownloadResult]) -> None
    def log_processing_results(self, results: ProcessingResult) -> None
```

**Log Format:**
```
Processing Log - YYYYMMDD_HHMMSS
=====================================
Start Time: YYYY-MM-DD HH:MM:SS
Date Folder: YYYY-MM-DD

Type Folder Scan Results:
- type3: 5 files
- type6: 3 files
- type7: 0 files
...

Downloaded Files:
- type3/document1.docx (1.2 MB)
- type3/document2.doc (850 KB)
...

Processing Results:
- Documents Processed: 15
- Records Extracted: 15
- CSV Generated: 20251124_output.csv (45 KB)

Upload Status:
- WOLF SFTP Upload: SUCCESS

End Time: YYYY-MM-DD HH:MM:SS
Duration: 45.3 seconds

Errors/Warnings:
- None
```

### 5. Parallel Action Executor

**Purpose:** Executes CSV upload, log creation, and email notification in parallel.

**Interface:**
```python
class ParallelActionExecutor:
    def execute_parallel(self, actions: List[Callable]) -> List[ActionResult]
    def upload_csv_action(self, csv_path: str, sftp_config: SFTPConfig) -> ActionResult
    def create_log_action(self, date_folder: Path, stats: ProcessingStats) -> ActionResult
    def send_email_action(self, stats: ProcessingStats, email_config: EmailConfig) -> ActionResult
```

**Implementation:**
- Uses Python's `concurrent.futures.ThreadPoolExecutor`
- Executes three actions simultaneously
- Waits for all actions to complete
- Returns results for each action

### 6. Main Controller (Modified)

**Purpose:** Orchestrates the new workflow.

**New Workflow:**
```python
def run_processing_cycle(self) -> ProcessingResult:
    # Step 1: Create date folder
    date = self.date_folder_manager.get_yesterday_date()
    date_folder = self.date_folder_manager.create_date_folder(self.storage_config.local_storage_path, date)
    
    # Step 2: Connect to WebScribe FTPS
    with self.ftps_manager.connect_ftps(self.source_ftps_config) as ftps_client:
        
        # Step 3: Scan type folders
        scan_results = self.type_folder_scanner.scan_folders(ftps_client, self.source_ftps_config.remote_path)
        
        # Step 4: Download files to date folder
        downloads = self._download_files_to_date_folder(ftps_client, scan_results, date_folder)
    
    # Step 5: Run AutoJob processing
    medical_records = self.document_parser.process_date_folder(date_folder)
    csv_path = self.csv_generator.generate_csv(medical_records, date_folder)
    
    # Step 6: Execute parallel actions
    stats = self._build_processing_stats(scan_results, downloads, medical_records, csv_path)
    
    actions = [
        lambda: self._upload_csv_to_wolf(csv_path),
        lambda: self._create_processing_log(date_folder, stats),
        lambda: self._send_email_notification(stats)
    ]
    
    results = self.parallel_executor.execute_parallel(actions)
    
    return self._build_processing_result(stats, results)
```

## Data Models

### ProcessingStats
```python
@dataclass
class ProcessingStats:
    date_folder: str
    start_time: datetime
    end_time: datetime
    type_folders_scanned: Dict[str, int]  # folder_name -> file_count
    files_downloaded: List[DownloadResult]
    documents_processed: int
    records_extracted: int
    csv_filename: str
    csv_size: int
    upload_status: str
    log_filename: str
    email_sent: bool
    errors: List[str]
```

### DownloadResult
```python
@dataclass
class DownloadResult:
    type_folder: str
    filename: str
    size: int
    success: bool
    error_message: Optional[str] = None
```

### ActionResult
```python
@dataclass
class ActionResult:
    action_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None
```

## Configuration Changes

### New Environment Variables

```bash
# WebScribe FTPS Configuration (replaces SOURCE_SFTP_*)
SOURCE_FTPS_HOST=webscribe.example.com
SOURCE_FTPS_PORT=21
SOURCE_FTPS_USERNAME=ftps_user
SOURCE_FTPS_PASSWORD=ftps_password
SOURCE_FTPS_PATH=/medical_documents
SOURCE_FTPS_USE_TLS=true

# WOLF SFTP Configuration (replaces DEST_SFTP_*)
DEST_SFTP_HOST=195.179.229.73
DEST_SFTP_PORT=22
DEST_SFTP_USERNAME=test817483
DEST_SFTP_PASSWORD=wolf_password
DEST_SFTP_PATH=/home/test817483/sites/test8.inkliksites.com/destination-folder-2

# Type Folders Configuration
TYPE_FOLDERS=type3,type6,type7,type16,type18,type19,type20,type21,type22,type23,type24

# Date Folder Configuration
USE_YESTERDAY_DATE=true
DATE_FOLDER_BASE_PATH=./data/processing
```

### Modified Configuration Models

```python
@dataclass
class FTPSConfig:
    host: str
    port: int
    username: str
    password: str
    remote_path: str
    use_tls: bool = True

@dataclass
class TypeFolderConfig:
    folders: List[str]
    base_path: str
```

## Error Handling

### Error Categories

1. **FTPS Connection Errors**
   - Retry up to 3 times with exponential backoff
   - Send failure notification if all retries fail
   - Log detailed connection error information

2. **File Download Errors**
   - Log error and continue with remaining files
   - Track failed downloads in processing stats
   - Include failed downloads in email notification

3. **Document Parsing Errors**
   - Log error and continue with remaining documents
   - Track failed parses in processing stats
   - Include parsing errors in processing log

4. **Parallel Action Errors**
   - Each action has independent error handling
   - Log errors for failed actions
   - Processing cycle succeeds if at least CSV upload succeeds
   - Email notification includes status of all actions

### Retry Policies

| Operation | Max Retries | Delay | Backoff |
|-----------|-------------|-------|---------|
| FTPS Connection | 3 | 2s | Exponential |
| File Download | 3 | 1s | Exponential |
| CSV Upload | 3 | 1s | Exponential |
| Email Send | 3 | 2s | Exponential |

## Testing Strategy

### Unit Tests

1. **DateFolderManager Tests**
   - Test date folder creation
   - Test date formatting
   - Test yesterday date calculation
   - Test last modified date extraction

2. **FTPSManager Tests**
   - Test FTPS connection with TLS
   - Test folder listing
   - Test file download
   - Test error handling

3. **TypeFolderScanner Tests**
   - Test scanning multiple folders
   - Test file filtering
   - Test result aggregation

4. **ParallelActionExecutor Tests**
   - Test parallel execution
   - Test error handling in parallel actions
   - Test result collection

### Integration Tests

1. **End-to-End Workflow Test**
   - Mock FTPS server with test files
   - Verify date folder creation
   - Verify file downloads
   - Verify CSV generation
   - Verify parallel actions

2. **FTPS Connection Test**
   - Test connection to real FTPS server
   - Test TLS negotiation
   - Test authentication

3. **WOLF SFTP Upload Test**
   - Test connection to WOLF SFTP
   - Test file upload
   - Test path creation

## Migration Strategy

### Phase 1: Add New Components (No Breaking Changes)
- Add DateFolderManager
- Add FTPSManager (alongside existing SFTPManager)
- Add TypeFolderScanner
- Add ProcessingLogCreator
- Add ParallelActionExecutor

### Phase 2: Update Main Controller
- Add new workflow method `run_webscribe_workflow()`
- Keep existing `run_processing_cycle()` for backward compatibility
- Add configuration flag to switch between workflows

### Phase 3: Configuration Migration
- Add new environment variables
- Keep old variables for backward compatibility
- Add validation for new configuration

### Phase 4: Testing and Validation
- Test new workflow in development
- Test new workflow in staging
- Validate parallel actions
- Validate FTPS/SFTP connections

### Phase 5: Production Deployment
- Deploy with feature flag
- Monitor processing cycles
- Gradually migrate to new workflow
- Remove old workflow code after validation

## Performance Considerations

### Parallel Execution
- CSV upload, log creation, and email notification run in parallel
- Expected time savings: 30-50% compared to sequential execution
- Thread pool size: 3 (one per action)

### File Download Optimization
- Download files in batches if needed
- Consider parallel downloads for large file counts
- Implement progress tracking for long downloads

### Memory Management
- Process documents in batches if memory usage is high
- Clean up temporary files after processing
- Monitor memory usage during parallel actions

## Security Considerations

### FTPS Security
- Use TLS 1.2 or higher
- Verify server certificates
- Use secure password storage
- Implement connection timeout

### SFTP Security
- Use SSH key authentication if possible
- Implement connection timeout
- Verify host keys
- Use secure password storage

### Data Protection
- Encrypt sensitive data in logs
- Sanitize file paths in logs
- Implement secure file deletion
- Use secure temporary directories

## Monitoring and Logging

### Key Metrics to Monitor
- Processing cycle duration
- File download success rate
- Document parsing success rate
- CSV upload success rate
- Email delivery rate
- Parallel action completion time

### Log Levels
- DEBUG: Detailed operation logs
- INFO: Processing milestones
- WARNING: Recoverable errors
- ERROR: Failed operations
- CRITICAL: System failures

### Alerts
- FTPS connection failures
- CSV upload failures
- High error rates in document parsing
- Email delivery failures
- Disk space warnings
