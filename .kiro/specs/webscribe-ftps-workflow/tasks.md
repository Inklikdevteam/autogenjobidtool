# Implementation Plan

## Task List

- [x] 1. Set up project configuration and dependencies



  - Add ftplib support for FTPS connections
  - Update environment variable configuration
  - Add new configuration models for FTPS and type folders
  - _Requirements: 2.1, 2.2, 10.1, 10.2, 10.3_

- [x] 1.1 Update configuration models


  - Create FTPSConfig dataclass in config/models.py
  - Create TypeFolderConfig dataclass
  - Add date folder configuration options
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 1.2 Update ConfigManager


  - Add methods to load FTPS configuration
  - Add method to load type folder configuration
  - Add validation for new configuration fields
  - Update environment variable loading
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_



- [ ] 1.3 Update requirements.txt
  - Verify ftplib is available (standard library)
  - Add any additional dependencies for parallel execution
  - _Requirements: 2.1_

- [x] 2. Implement DateFolderManager component


  - Create src/utils/date_folder_manager.py
  - Implement date folder creation logic
  - Implement date formatting methods
  - Implement yesterday date calculation
  - Implement last modified date extraction
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_



- [ ] 2.1 Create DateFolderManager class
  - Implement create_date_folder() method
  - Implement get_folder_name() method
  - Implement get_yesterday_date() method
  - Implement get_last_modified_date() method
  - Implement organize_by_type() method

  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 2.2 Add date folder validation
  - Verify folder creation success



  - Handle permission errors
  - Log folder creation events
  - _Requirements: 1.5_

- [ ] 3. Implement FTPSManager component
  - Create src/ftps/ftps_manager.py
  - Implement FTPS connection with TLS


  - Implement folder listing
  - Implement file download with verification
  - Implement retry logic
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_


- [ ] 3.1 Create FTPSManager class
  - Implement connect_ftps() method with TLS support
  - Implement _establish_ftps_connection() with retry logic
  - Implement _close_connection() method
  - Add context manager support
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_


- [ ] 3.2 Implement folder operations
  - Implement list_type_folders() method
  - Implement list_files_in_folder() method
  - Implement scan_all_type_folders() method
  - Filter for direct files only (no subdirectories)

  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 3.3 Implement file download
  - Implement download_file() method
  - Add file size verification
  - Add retry logic for failed downloads
  - Handle partial downloads
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 3.4 Add error handling
  - Handle FTPS connection errors
  - Handle authentication errors
  - Handle file not found errors
  - Implement comprehensive logging
  - _Requirements: 2.5, 4.6, 11.1, 11.2_

- [x] 4. Implement TypeFolderScanner component


  - Create src/utils/type_folder_scanner.py
  - Implement type folder scanning logic
  - Implement file filtering
  - Implement result aggregation
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_


- [x] 4.1 Create TypeFolderScanner class

  - Implement __init__() with type folder configuration
  - Implement scan_folders() method
  - Implement get_all_files() method
  - Implement filter_document_files() method
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4.2 Add scanning statistics

  - Track file count per type folder
  - Track total files found
  - Log scanning progress
  - _Requirements: 3.5_

- [x] 5. Implement ProcessingLogCreator component


  - Create src/utils/processing_log_creator.py
  - Implement log file creation
  - Implement log formatting
  - Implement statistics tracking
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 5.1 Create ProcessingLogCreator class


  - Implement create_log() method
  - Implement format_log_entry() method
  - Implement log_scan_results() method
  - Implement log_download_results() method
  - Implement log_processing_results() method
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 5.2 Design log format

  - Create structured log template
  - Include all required information
  - Format timestamps and durations
  - Include error/warning sections
  - _Requirements: 7.2_

- [x] 6. Implement ParallelActionExecutor component



  - Create src/utils/parallel_action_executor.py
  - Implement parallel execution using ThreadPoolExecutor
  - Implement action result tracking
  - Implement error handling for parallel actions
  - _Requirements: 6.6, 7.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 6.1 Create ParallelActionExecutor class


  - Implement execute_parallel() method
  - Implement upload_csv_action() method
  - Implement create_log_action() method
  - Implement send_email_action() method
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 6.2 Add action result tracking

  - Create ActionResult dataclass
  - Track success/failure for each action
  - Track execution duration
  - Collect error messages
  - _Requirements: 9.3, 9.4_

- [x] 6.3 Implement error handling

  - Handle individual action failures
  - Continue execution if one action fails
  - Log all action results
  - Determine overall success criteria
  - _Requirements: 9.4, 9.5_

- [x] 7. Update MainController for new workflow



  - Modify src/controller/main_controller.py
  - Add new workflow method
  - Integrate all new components
  - Implement workflow orchestration
  - _Requirements: All requirements_

- [x] 7.1 Add new components to MainController


  - Initialize DateFolderManager
  - Initialize FTPSManager
  - Initialize TypeFolderScanner
  - Initialize ProcessingLogCreator
  - Initialize ParallelActionExecutor
  - _Requirements: All requirements_

- [x] 7.2 Implement run_webscribe_workflow() method

  - Step 1: Create date folder
  - Step 2: Connect to WebScribe FTPS
  - Step 3: Scan type folders
  - Step 4: Download files to date folder
  - Step 5: Run AutoJob processing
  - Step 6: Execute parallel actions
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1_

- [x] 7.3 Implement helper methods

  - Implement _download_files_to_date_folder()
  - Implement _build_processing_stats()
  - Implement _upload_csv_to_wolf()
  - Implement _create_processing_log()
  - Implement _send_email_notification()
  - _Requirements: 4.1, 5.1, 6.1, 7.1, 8.1_

- [x] 7.4 Add workflow selection logic

  - Add configuration flag for workflow selection
  - Keep old run_processing_cycle() for backward compatibility
  - Route to appropriate workflow based on configuration
  - _Requirements: 10.1_

- [x] 8. Update DocumentParser for date folder processing

  - Modify src/parser/document_parser.py
  - Add method to process entire date folder
  - Handle files from multiple type folders
  - Maintain existing parsing logic
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 8.1 Add process_date_folder() method

  - Scan date folder for all document files
  - Process files from type subdirectories
  - Extract medical records from all documents
  - Return aggregated list of medical records
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 8.2 Handle empty or invalid documents

  - Skip corrupted files
  - Log parsing errors
  - Continue with remaining files
  - _Requirements: 5.6, 11.3_

- [x] 9. Update CSVGenerator for new workflow

  - Modify src/utils/csv_generator.py
  - Update CSV generation to use date folder date
  - Save CSV in date folder
  - Maintain existing CSV format
  - _Requirements: 5.3, 5.4, 5.5_

- [x] 9.1 Update generate_csv() method

  - Accept date folder path parameter
  - Generate filename as YYYYMMDD_output.csv from date folder name
  - Save CSV in date folder root
  - Return CSV path for upload
  - _Requirements: 5.3, 5.4, 5.5_

- [x] 10. Update EmailNotifier for new workflow

  - Modify src/email_notifier/notifier.py
  - Add method for WebScribe workflow notification
  - Include new statistics in email
  - Format email with parallel action results
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 10.1 Create send_webscribe_notification() method

  - Include processing date
  - Include type folder scan results
  - Include download statistics
  - Include processing results
  - Include parallel action status
  - _Requirements: 8.2, 8.3_

- [x] 10.2 Design email template

  - Create HTML template for new workflow
  - Include all required information
  - Format statistics tables
  - Include error/warning sections
  - _Requirements: 8.2, 8.4_

- [x] 11. Add WOLF SFTP upload functionality

  - Use existing SFTPManager for WOLF connection
  - Implement upload to specific path
  - Add verification
  - Add retry logic
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 11.1 Implement upload_to_wolf() method

  - Connect to WOLF SFTP (195.179.229.73)
  - Upload CSV to /home/test817483/sites/test8.inkliksites.com/destination-folder-2
  - Verify upload success
  - Return upload result
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 12. Update environment configuration

  - Update .env.example with new variables
  - Document all new configuration options
  - Add validation for required fields
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 12.1 Add new environment variables

  - Add SOURCE_FTPS_* variables
  - Add DEST_SFTP_* variables for WOLF
  - Add TYPE_FOLDERS variable
  - Add DATE_FOLDER_* variables
  - Add WORKFLOW_MODE variable
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 13. Add comprehensive error handling

  - Implement retry logic for all network operations
  - Add graceful degradation for non-critical failures
  - Implement failure notifications
  - Add detailed error logging
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 13.1 Update error handler

  - Add FTPS_CONNECTION error category
  - Add FTPS_FILE_OPERATION error category
  - Update retry policies
  - Add error context tracking
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 14. Update scheduling system

  - Ensure scheduler works with new workflow
  - Add workflow mode selection
  - Maintain backward compatibility
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 14.1 Update scheduler integration

  - Route to correct workflow based on configuration
  - Handle both workflows in scheduled execution
  - Log workflow mode in use
  - _Requirements: 12.1, 12.2, 12.3_

- [x] 15. Add logging and monitoring


  - Add detailed logging for new workflow
  - Track performance metrics
  - Monitor parallel action execution
  - Add health checks
  - _Requirements: All requirements_

- [x] 15.1 Add workflow-specific logging

  - Log date folder creation
  - Log FTPS connection events
  - Log type folder scan results
  - Log download progress
  - Log parallel action results
  - _Requirements: All requirements_

- [ ] 16. Create migration documentation
  - Document configuration changes
  - Document workflow differences
  - Create migration guide
  - Document rollback procedure
  - _Requirements: 10.1, 10.2, 10.3_

- [ ] 17. Integration testing
  - Test complete workflow end-to-end
  - Test FTPS connection to WebScribe
  - Test SFTP connection to WOLF
  - Test parallel action execution
  - Test error handling and recovery
  - _Requirements: All requirements_

- [ ] 17.1 Create test fixtures
  - Create mock FTPS server
  - Create test files for type folders
  - Create test configuration
  - _Requirements: All requirements_

- [ ] 17.2 Test workflow steps
  - Test date folder creation
  - Test type folder scanning
  - Test file downloads
  - Test document processing
  - Test CSV generation
  - Test parallel actions
  - _Requirements: All requirements_

- [ ] 18. Update documentation
  - Update README.md with new workflow
  - Update CONTEXT_DOCUMENT.md
  - Update PROCESS_DOCUMENTATION.md
  - Update DEPLOYMENT.md
  - Update TROUBLESHOOTING.md
  - _Requirements: All requirements_

- [ ] 18.1 Document new workflow
  - Document date folder structure
  - Document type folder configuration
  - Document FTPS connection setup
  - Document WOLF SFTP configuration
  - Document parallel action execution
  - _Requirements: All requirements_
