# Requirements Document

## Introduction

This document specifies the requirements for modifying the Medical Document Processing System to implement a new workflow that connects to WebScribe FTPS server, processes files from multiple folder types, and uploads results to WOLF SFTP server.

## Glossary

- **WebScribe FTPS**: The source FTPS server containing medical documents organized in type-specific folders
- **WOLF SFTP**: The destination SFTP server (195.179.229.73) where processed CSV files are uploaded
- **Date Folder**: A local directory named with format YYYY-MM-DD based on yesterday's date or last modified date from FTP
- **Type Folders**: Specific folders on WebScribe FTPS (type3, type6, type7, type16, type18, type19, type20, type21, type22, type23, type24)
- **AutoJob Program**: The existing document parsing and CSV generation logic
- **Processing Log**: A detailed log file documenting the processing cycle

## Requirements

### Requirement 1: Date Folder Creation

**User Story:** As a system operator, I want the system to create a date-based folder locally so that files are organized by processing date.

#### Acceptance Criteria

1. WHEN the processing cycle starts, THE System SHALL create a local directory with name format "YYYY-MM-DD"
2. THE System SHALL use yesterday's date as the default folder name
3. IF files are found on FTPS with modification dates, THEN THE System SHALL use the last modified date for the folder name
4. THE System SHALL create the date folder in the configured local storage path
5. THE System SHALL verify the date folder exists before proceeding with file downloads

### Requirement 2: WebScribe FTPS Connection

**User Story:** As a system operator, I want the system to connect to WebScribe FTPS server so that medical documents can be retrieved.

#### Acceptance Criteria

1. THE System SHALL establish a secure FTPS connection to the WebScribe server
2. THE System SHALL use credentials from SOURCE_SFTP_HOST, SOURCE_SFTP_USERNAME, SOURCE_SFTP_PASSWORD environment variables
3. THE System SHALL support FTPS protocol with TLS encryption
4. THE System SHALL implement retry logic with up to 3 connection attempts
5. IF connection fails after all retries, THEN THE System SHALL log the error and send failure notification

### Requirement 3: Type Folder Scanning

**User Story:** As a system operator, I want the system to check all designated type folders so that documents from all sources are processed.

#### Acceptance Criteria

1. THE System SHALL scan the following folders on WebScribe FTPS: type3, type6, type7, type16, type18, type19, type20, type21, type22, type23, type24
2. THE System SHALL list all files directly within each type folder (not subdirectories)
3. THE System SHALL filter for document files with extensions .doc, .docx, .zip
4. THE System SHALL retrieve file metadata including filename, size, and modification time
5. THE System SHALL log the count of files found in each type folder

### Requirement 4: File Download to Date Folder

**User Story:** As a system operator, I want files downloaded to the date-specific folder so that processing is organized by date.

#### Acceptance Criteria

1. THE System SHALL download all discovered files from type folders to the local date folder
2. THE System SHALL preserve the original filename during download
3. THE System SHALL create subdirectories within the date folder for each type folder (e.g., date-folder/type3/, date-folder/type6/)
4. THE System SHALL verify file size matches between source and downloaded file
5. THE System SHALL skip files that already exist in the date folder with matching size
6. IF download fails for a file, THEN THE System SHALL log the error and continue with remaining files

### Requirement 5: AutoJob Processing

**User Story:** As a system operator, I want the AutoJob program to process downloaded files so that medical data is extracted into CSV format.

#### Acceptance Criteria

1. THE System SHALL execute the existing document parsing logic on all files in the date folder
2. THE System SHALL extract 16 medical fields from each document
3. THE System SHALL generate a single CSV file named "YYYYMMDD_output.csv" where YYYYMMDD is the date folder date
4. THE System SHALL include all extracted records in the CSV file
5. THE System SHALL save the CSV file in the date folder
6. IF no valid records are extracted, THEN THE System SHALL create an empty CSV with headers only

### Requirement 6: CSV Upload to WOLF SFTP

**User Story:** As a system operator, I want the CSV file uploaded to WOLF SFTP server so that processed data is available to downstream systems.

#### Acceptance Criteria

1. THE System SHALL connect to WOLF SFTP server at 195.179.229.73
2. THE System SHALL use credentials from DEST_SFTP_USERNAME and DEST_SFTP_PASSWORD environment variables
3. THE System SHALL upload the CSV file to path "/home/test817483/sites/test8.inkliksites.com/destination-folder-2"
4. THE System SHALL verify the uploaded file size matches the local file
5. THE System SHALL implement retry logic with up to 3 upload attempts
6. THE System SHALL execute this action in parallel with log creation and email notification

### Requirement 7: Processing Log Creation

**User Story:** As a system operator, I want a detailed processing log created so that I can audit and troubleshoot the processing cycle.

#### Acceptance Criteria

1. THE System SHALL create a processing log file named "processing_log_YYYYMMDD_HHMMSS.txt"
2. THE System SHALL include the following information in the log:
   - Processing start and end timestamps
   - Date folder name
   - List of type folders scanned
   - Count of files found in each type folder
   - List of downloaded files with sizes
   - Count of documents processed
   - Count of records extracted
   - CSV filename and size
   - Upload status to WOLF SFTP
   - Any errors or warnings encountered
3. THE System SHALL save the log file in the date folder
4. THE System SHALL execute this action in parallel with CSV upload and email notification

### Requirement 8: Email Notification

**User Story:** As a system operator, I want to receive email notifications so that I am informed of processing results.

#### Acceptance Criteria

1. THE System SHALL send an email notification after processing completes
2. THE System SHALL include the following in the email:
   - Processing date
   - Count of type folders scanned
   - Total files downloaded
   - Total documents processed
   - Total records extracted
   - CSV filename
   - Upload status to WOLF SFTP
   - Link or path to processing log
   - Summary of any errors
3. THE System SHALL send the email to addresses configured in ADMIN_EMAIL
4. THE System SHALL use HTML formatting for the email body
5. THE System SHALL execute this action in parallel with CSV upload and log creation
6. IF email sending fails, THEN THE System SHALL log the error but not fail the processing cycle

### Requirement 9: Parallel Action Execution

**User Story:** As a system operator, I want CSV upload, log creation, and email notification to execute in parallel so that processing completes faster.

#### Acceptance Criteria

1. THE System SHALL initiate CSV upload, log creation, and email notification simultaneously
2. THE System SHALL wait for all three actions to complete before finishing the processing cycle
3. THE System SHALL log the completion status of each parallel action
4. IF any parallel action fails, THEN THE System SHALL log the failure but allow other actions to complete
5. THE System SHALL report the overall processing cycle as successful only if all three actions succeed

### Requirement 10: Configuration Management

**User Story:** As a system operator, I want to configure the system through environment variables so that deployment is flexible.

#### Acceptance Criteria

1. THE System SHALL read WebScribe FTPS connection details from SOURCE_SFTP_HOST, SOURCE_SFTP_PORT, SOURCE_SFTP_USERNAME, SOURCE_SFTP_PASSWORD
2. THE System SHALL read WOLF SFTP connection details from DEST_SFTP_HOST (195.179.229.73), DEST_SFTP_PORT, DEST_SFTP_USERNAME, DEST_SFTP_PASSWORD
3. THE System SHALL read destination path from DEST_SFTP_PATH (/home/test817483/sites/test8.inkliksites.com/destination-folder-2)
4. THE System SHALL support configuration of type folders to scan through TYPE_FOLDERS environment variable
5. THE System SHALL validate all required configuration on startup

### Requirement 11: Error Handling and Recovery

**User Story:** As a system operator, I want robust error handling so that transient failures don't stop processing.

#### Acceptance Criteria

1. THE System SHALL implement retry logic for FTPS/SFTP connection failures
2. THE System SHALL continue processing remaining files if individual file download fails
3. THE System SHALL continue processing remaining documents if individual document parsing fails
4. THE System SHALL send failure notification email if critical errors occur
5. THE System SHALL log all errors with full context for troubleshooting

### Requirement 12: Scheduling and Execution

**User Story:** As a system operator, I want the system to run on a schedule so that processing is automated.

#### Acceptance Criteria

1. THE System SHALL support interval-based scheduling (every N seconds)
2. THE System SHALL support cron-based scheduling for specific times
3. THE System SHALL execute one complete processing cycle per scheduled run
4. THE System SHALL prevent overlapping processing cycles
5. THE System SHALL support graceful shutdown without data loss
