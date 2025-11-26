# Requirements Document

## Introduction

The Medical Document Processing System is an automated Python application that monitors SFTP servers for ZIP files containing medical documents (.doc/.docx), extracts and parses medical data fields, generates CSV reports, and distributes them via SFTP with comprehensive email notifications and error handling.

## Glossary

- **Source_SFTP**: The SFTP server where ZIP files containing medical documents are uploaded
- **Destination_SFTP**: The SFTP server where processed CSV files are uploaded
- **Medical_Document**: A .doc or .docx file containing medical report data with specific fields to extract
- **ZIP_File**: A compressed archive containing one or more medical documents
- **CSV_Report**: A comma-separated values file with extracted medical data, one row per document
- **Processing_System**: The main Python application that orchestrates the entire workflow
- **Schedule_Manager**: The component that handles both interval and cron-based scheduling
- **Document_Parser**: The component that extracts text and medical fields from documents
- **Email_Notifier**: The component that sends success summaries and failure alerts
- **File_Tracker**: The component that tracks processed files and modification times

## Requirements

### Requirement 1

**User Story:** As a medical data administrator, I want the system to automatically detect and process new or modified ZIP files on the source SFTP server, so that medical documents are processed without manual intervention.

#### Acceptance Criteria

1. WHEN the Processing_System connects to Source_SFTP, THE Processing_System SHALL authenticate using credentials from environment variables
2. THE Processing_System SHALL identify ZIP files that are new or have modified timestamps since last processing
3. WHEN a ZIP_File is detected as new or modified, THE Processing_System SHALL download the ZIP_File to local temporary storage
4. THE Processing_System SHALL maintain a record of processed files with their last modification timestamps
5. THE Processing_System SHALL reprocess ZIP files when their modification time changes

### Requirement 2

**User Story:** As a system administrator, I want flexible scheduling options for the processing system, so that I can configure it to run at optimal times for our workflow.

#### Acceptance Criteria

1. WHERE POLL_CRON environment variable is set, THE Schedule_Manager SHALL use cron-based scheduling
2. WHERE POLL_CRON environment variable is not set, THE Schedule_Manager SHALL use interval-based scheduling with POLL_INTERVAL_SECONDS
3. THE Schedule_Manager SHALL default to 60 seconds for interval mode when POLL_INTERVAL_SECONDS is not specified
4. WHERE TZ environment variable is set, THE Schedule_Manager SHALL use the specified timezone for cron scheduling
5. THE Schedule_Manager SHALL use system timezone when TZ environment variable is not specified

### Requirement 3

**User Story:** As a medical data processor, I want the system to extract specific medical fields from documents and generate standardized CSV reports, so that data can be easily imported into other systems.

#### Acceptance Criteria

1. THE Document_Parser SHALL extract .doc and .docx files from downloaded ZIP archives
2. THE Document_Parser SHALL parse medical text to extract: first_name, last_name, date_of_birth, record_number, case_number, accident_date, provider_first, provider_last, exam_date, exam_place, transcriptionist, dd_date, transcription_date, job_number, case_code
3. THE Processing_System SHALL create one CSV_Report per ZIP_File with extracted data
4. THE CSV_Report SHALL contain columns in exact order: source_file, first_name, last_name, date_of_birth, record_number, case_number, accident_date, provider_first, provider_last, exam_date, exam_place, transcriptionist, dd_date, transcription_date, job_number, case_code
5. THE Document_Parser SHALL normalize all dates to MM/DD/YYYY format and use empty strings for missing data

### Requirement 4

**User Story:** As a data recipient, I want processed CSV files automatically uploaded to the destination SFTP server, so that I can access the processed medical data without manual file transfers.

#### Acceptance Criteria

1. WHEN CSV_Report generation is complete, THE Processing_System SHALL upload the CSV_Report to Destination_SFTP
2. THE Processing_System SHALL authenticate to Destination_SFTP using credentials from environment variables
3. THE Processing_System SHALL retain processed CSV files locally for 60 days
4. THE Processing_System SHALL clean temporary files after successful processing
5. THE Processing_System SHALL maintain organized storage of retained CSV files with timestamps

### Requirement 5

**User Story:** As a system administrator, I want comprehensive error handling and email notifications, so that I can monitor system health and respond quickly to processing failures.

#### Acceptance Criteria

1. WHEN any document extraction fails, THE Email_Notifier SHALL immediately send a failure email to administrators
2. THE Processing_System SHALL continue processing remaining documents after individual failures
3. WHEN processing completes successfully, THE Email_Notifier SHALL send a summary email with processing statistics
4. THE Processing_System SHALL log all operations with detailed status messages and timestamps
5. THE Processing_System SHALL handle SFTP connection failures, file I/O errors, and document parsing errors gracefully

### Requirement 6

**User Story:** As a system administrator, I want all sensitive configuration managed through environment variables, so that credentials and settings can be securely managed without code changes.

#### Acceptance Criteria

1. THE Processing_System SHALL load all SFTP credentials from .env file or environment variables
2. THE Processing_System SHALL load email configuration from environment variables
3. THE Processing_System SHALL load scheduling configuration from environment variables
4. THE Processing_System SHALL validate required environment variables at startup
5. THE Processing_System SHALL provide clear error messages for missing or invalid configuration