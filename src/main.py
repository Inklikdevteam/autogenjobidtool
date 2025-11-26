"""Main entry point for the WebScribe FTPS workflow system."""

import sys
import signal
import logging
import os
from pathlib import Path
from config.settings import ConfigManager, ConfigurationError
from controller.main_controller import MainController, ProcessingError
from scheduler.job_scheduler import Scheduler
from utils.error_handler import get_error_handler, ErrorCategory, ErrorSeverity, handle_error
from utils.logging_config import setup_logging as setup_advanced_logging


# Global variables for graceful shutdown
scheduler = None
main_controller = None
logger = None


def setup_logging(config_manager: ConfigManager):
    """Set up comprehensive logging configuration with advanced features."""
    # Create logs directory if it doesn't exist
    storage_config = config_manager.get_storage_config()
    retention_config = config_manager.get_retention_config()
    log_dir = Path(storage_config.local_storage_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the advanced logging system with retention config
    logging_manager = setup_advanced_logging(
        log_dir=str(log_dir),
        console_level="INFO",
        file_level="DEBUG",
        enable_colors=True,
        retention_config=retention_config
    )
    
    # Initialize error handler with storage path and retention config
    error_storage_path = log_dir / "error_context"
    get_error_handler(str(error_storage_path), retention_config)
    
    # Log system information
    logger = logging.getLogger(__name__)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Log directory: {log_dir}")
    
    return logging_manager


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global scheduler, logger
    
    if logger:
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    
    # Stop scheduler first
    if scheduler and scheduler.is_running():
        if logger:
            logger.info("Stopping scheduler...")
        scheduler.stop()
    
    if logger:
        logger.info("Graceful shutdown complete")
    
    sys.exit(0)


def validate_environment():
    """Validate the runtime environment and create necessary directories."""
    # Check Python version
    if sys.version_info < (3, 7):
        raise RuntimeError("Python 3.7 or higher is required")
    
    # Check for required packages with correct import names
    required_imports = [
        ('paramiko', 'paramiko'),
        ('python-docx', 'docx'),
        ('python-dotenv', 'dotenv'), 
        ('schedule', 'schedule'),
        ('croniter', 'croniter'),
        ('pytz', 'pytz')
    ]
    
    missing_packages = []
    for package_name, import_name in required_imports:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        raise RuntimeError(
            f"Missing required packages: {', '.join(missing_packages)}. "
            f"Please install with: pip install {' '.join(missing_packages)}"
        )


def create_directories(config_manager: ConfigManager):
    """Create necessary directories for the application."""
    storage_config = config_manager.get_storage_config()
    
    # Create storage directories
    directories = [
        storage_config.local_storage_path,
        storage_config.temp_path,
        os.path.join(storage_config.local_storage_path, "logs"),
        os.path.join(storage_config.local_storage_path, "csv_files")
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def run_scheduled_processing():
    """Function to be called by the scheduler."""
    global main_controller, logger
    
    try:
        if main_controller:
            logger.info("Starting scheduled processing cycle")
            results = main_controller.run_processing_cycle()
            if results:
                logger.info(f"Scheduled processing completed successfully. Processed {len(results)} ZIP files")
                # Log summary statistics
                total_docs = sum(r.total_documents for r in results)
                successful_docs = sum(r.successful_extractions for r in results)
                logger.info(f"Processing summary: {successful_docs}/{total_docs} documents processed successfully")
            else:
                logger.debug("Scheduled processing completed. No files to process")
        else:
            error_msg = "Main controller not initialized for scheduled processing"
            logger.error(error_msg)
            handle_error(
                error=RuntimeError(error_msg),
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                component="main",
                operation="scheduled_processing"
            )
    except Exception as e:
        logger.error(f"Error in scheduled processing: {e}", exc_info=True)
        handle_error(
            error=e,
            category=ErrorCategory.SYSTEM_RESOURCE,
            severity=ErrorSeverity.HIGH,
            component="main",
            operation="scheduled_processing"
        )


def main():
    """Main application entry point."""
    global scheduler, main_controller, logger
    
    try:
        # Validate environment first
        logger = logging.getLogger(__name__)  # Initialize basic logger first
        logger.info("Starting system validation...")
        validate_environment()
        
        # Initialize configuration
        print("Initializing WebScribe FTPS workflow system...")
        config_manager = ConfigManager()
        
        # Set up comprehensive logging
        logging_manager = setup_logging(config_manager)
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("WebScribe FTPS Workflow System starting up")
        logger.info("=" * 60)
        logger.info("Configuration loaded and validated successfully")
        
        # Create necessary directories
        create_directories(config_manager)
        logger.info("Directory structure validated")
        
        # Initialize main controller
        main_controller = MainController(config_manager)
        logger.info("Main controller initialized successfully")
        
        # Get schedule configuration
        schedule_config = config_manager.get_schedule_config()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize and start scheduler
        scheduler = Scheduler(schedule_config, run_scheduled_processing)
        logger.info("Scheduler initialized successfully")
        
        # Start the scheduler
        scheduler.start()
        
        # Log startup completion with detailed configuration
        logger.info("System startup completed successfully")
        if schedule_config.poll_cron:
            logger.info(f"Scheduling mode: CRON ({schedule_config.poll_cron})")
            if hasattr(schedule_config, 'timezone') and schedule_config.timezone:
                logger.info(f"Timezone: {schedule_config.timezone}")
            next_run = scheduler.get_next_run_time()
            if next_run:
                logger.info(f"Next scheduled run: {next_run}")
        else:
            logger.info(f"Scheduling mode: INTERVAL ({schedule_config.poll_interval_seconds} seconds)")
        
        # Log system configuration summary
        storage_config = config_manager.get_storage_config()
        logger.info(f"Storage path: {storage_config.local_storage_path}")
        logger.info(f"Temporary path: {storage_config.temp_path}")
        
        # Run an initial processing cycle
        logger.info("Running initial processing cycle...")
        try:
            results = main_controller.run_processing_cycle()
            if results:
                total_docs = sum(r.total_documents for r in results)
                successful_docs = sum(r.successful_extractions for r in results)
                logger.info(f"Initial processing completed: {len(results)} ZIP files, {successful_docs}/{total_docs} documents")
            else:
                logger.info("Initial processing completed. No files to process")
        except Exception as e:
            logger.warning(f"Initial processing cycle failed: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.MEDIUM,
                component="main",
                operation="initial_processing"
            )
        
        # Keep the main thread alive
        logger.info("System is running and monitoring for files. Press Ctrl+C to stop.")
        logger.info("=" * 60)
        
        try:
            while scheduler.is_running():
                signal.pause()  # Wait for signals
        except AttributeError:
            # signal.pause() is not available on Windows
            import time
            while scheduler.is_running():
                time.sleep(1)
        
    except ConfigurationError as e:
        error_msg = f"Configuration error: {e}"
        if logger:
            logger.critical(error_msg)
            handle_error(
                error=e,
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.CRITICAL,
                component="main",
                operation="startup"
            )
        else:
            print(error_msg)
        sys.exit(1)
    except ProcessingError as e:
        error_msg = f"Processing error: {e}"
        if logger:
            logger.error(error_msg)
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.HIGH,
                component="main",
                operation="startup"
            )
        else:
            print(error_msg)
        sys.exit(1)
    except KeyboardInterrupt:
        if logger:
            logger.info("Received keyboard interrupt, initiating graceful shutdown...")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        error_msg = f"Unexpected error during execution: {e}"
        if logger:
            logger.critical(error_msg, exc_info=True)
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                component="main",
                operation="execution",
                additional_data={"traceback": str(e)}
            )
        else:
            print(error_msg)
        sys.exit(1)
    finally:
        # Ensure cleanup and generate final error report
        try:
            if scheduler and scheduler.is_running():
                scheduler.stop()
            
            if logger:
                logger.info("System shutdown complete")
                
                # Generate and log error report
                error_handler = get_error_handler()
                error_report = error_handler.generate_error_report(hours=24)
                if "Total Errors: 0" not in error_report:
                    logger.info("Error Summary for Last 24 Hours:")
                    for line in error_report.strip().split('\n'):
                        if line.strip():
                            logger.info(line)
                
                # Cleanup old error logs and log files (using configured retention times)
                error_handler.cleanup_old_error_logs()
                if 'logging_manager' in locals():
                    logging_manager.cleanup_old_logs()
                
                # Cleanup old ZIP backups, CSV files, and summary files
                if 'main_controller' in locals() and main_controller:
                    main_controller.csv_generator.cleanup_expired_files()
                    main_controller.csv_generator.cleanup_expired_zip_backups()
                    main_controller.summary_logger.cleanup_old_summaries()
                
        except Exception as cleanup_error:
            if logger:
                logger.warning(f"Error during cleanup: {cleanup_error}")
            else:
                print(f"Error during cleanup: {cleanup_error}")


if __name__ == "__main__":
    main()