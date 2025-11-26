"""Advanced logging configuration for the medical document processing system."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.models import RetentionConfig


class ContextFilter(logging.Filter):
    """Custom filter to add context information to log records."""
    
    def __init__(self, component: str = ""):
        super().__init__()
        self.component = component
    
    def filter(self, record):
        """Add context information to the log record."""
        if not hasattr(record, 'component'):
            record.component = self.component
        
        # Add process ID and thread ID for debugging
        record.process_id = os.getpid()
        record.thread_id = getattr(record, 'thread', 'main')
        
        return True


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        """Format the log record with colors."""
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        
        return super().format(record)


class LoggingManager:
    """Advanced logging manager with comprehensive configuration."""
    
    def __init__(self, log_dir: str, app_name: str = "medical_processor", retention_config: Optional[RetentionConfig] = None):
        """Initialize the logging manager.
        
        Args:
            log_dir: Directory to store log files
            app_name: Application name for log files
            retention_config: Configuration for log file retention
        """
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.retention_config = retention_config or RetentionConfig()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.main_log_file = self.log_dir / f"{app_name}.log"
        self.error_log_file = self.log_dir / f"{app_name}_errors.log"
        self.debug_log_file = self.log_dir / f"{app_name}_debug.log"
        self.performance_log_file = self.log_dir / f"{app_name}_performance.log"
        
        # Performance logger for timing and metrics
        self.performance_logger = None
        
    def setup_logging(self, 
                     console_level: str = "INFO",
                     file_level: str = "DEBUG",
                     enable_colors: bool = True,
                     max_file_size: int = 10 * 1024 * 1024,  # 10MB
                     backup_count: int = 5) -> None:
        """Set up comprehensive logging configuration.
        
        Args:
            console_level: Logging level for console output
            file_level: Logging level for file output
            enable_colors: Whether to enable colored console output
            max_file_size: Maximum size of log files before rotation
            backup_count: Number of backup files to keep
        """
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level to DEBUG to capture everything
        root_logger.setLevel(logging.DEBUG)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] '
            '[PID:%(process_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        performance_formatter = logging.Formatter(
            '[%(asctime)s] [PERF] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level.upper()))
        
        if enable_colors and sys.stdout.isatty():
            console_formatter = ColoredFormatter(
                '[%(asctime)s] [%(levelname)-8s] - %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            console_formatter = simple_formatter
        
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(ContextFilter())
        root_logger.addHandler(console_handler)
        
        # Main application log file (rotating by time)
        try:
            main_file_handler = logging.handlers.TimedRotatingFileHandler(
                self.main_log_file,
                when='midnight',
                interval=1,
                backupCount=30,  # Keep 30 days
                encoding='utf-8'
            )
            main_file_handler.setLevel(getattr(logging, file_level.upper()))
            main_file_handler.setFormatter(detailed_formatter)
            main_file_handler.addFilter(ContextFilter())
            root_logger.addHandler(main_file_handler)
        except Exception as e:
            print(f"Warning: Could not set up main log file: {e}")
        
        # Error-only log file (rotating by size)
        try:
            error_file_handler = logging.handlers.RotatingFileHandler(
                self.error_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_file_handler.setLevel(logging.ERROR)
            error_file_handler.setFormatter(detailed_formatter)
            error_file_handler.addFilter(ContextFilter())
            root_logger.addHandler(error_file_handler)
        except Exception as e:
            print(f"Warning: Could not set up error log file: {e}")
        
        # Debug log file (rotating by size, larger files)
        try:
            debug_file_handler = logging.handlers.RotatingFileHandler(
                self.debug_log_file,
                maxBytes=max_file_size * 2,  # 20MB for debug logs
                backupCount=3,  # Keep fewer debug files
                encoding='utf-8'
            )
            debug_file_handler.setLevel(logging.DEBUG)
            debug_file_handler.setFormatter(detailed_formatter)
            debug_file_handler.addFilter(ContextFilter())
            root_logger.addHandler(debug_file_handler)
        except Exception as e:
            print(f"Warning: Could not set up debug log file: {e}")
        
        # Performance log file
        try:
            performance_file_handler = logging.handlers.RotatingFileHandler(
                self.performance_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            performance_file_handler.setLevel(logging.INFO)
            performance_file_handler.setFormatter(performance_formatter)
            
            # Create dedicated performance logger
            self.performance_logger = logging.getLogger('performance')
            self.performance_logger.setLevel(logging.INFO)
            self.performance_logger.addHandler(performance_file_handler)
            self.performance_logger.propagate = False  # Don't propagate to root logger
            
        except Exception as e:
            print(f"Warning: Could not set up performance log file: {e}")
        
        # Reduce noise from third-party libraries
        self._configure_third_party_loggers()
        
        # Log the logging setup completion
        logger = logging.getLogger(__name__)
        logger.info(f"Logging system initialized - Console: {console_level}, File: {file_level}")
        logger.info(f"Log directory: {self.log_dir}")
        
    def _configure_third_party_loggers(self):
        """Configure third-party library loggers to reduce noise."""
        third_party_configs = {
            'paramiko': logging.WARNING,
            'paramiko.transport': logging.ERROR,
            'paramiko.sftp': logging.WARNING,
            'schedule': logging.INFO,
            'urllib3': logging.WARNING,
            'urllib3.connectionpool': logging.WARNING,
            'requests': logging.WARNING,
            'smtplib': logging.INFO,
        }
        
        for logger_name, level in third_party_configs.items():
            logging.getLogger(logger_name).setLevel(level)
    
    def get_performance_logger(self) -> Optional[logging.Logger]:
        """Get the performance logger for timing and metrics.
        
        Returns:
            Performance logger instance or None if not available
        """
        return self.performance_logger
    
    def log_performance(self, operation: str, duration: float, 
                       additional_data: Optional[dict] = None):
        """Log performance metrics.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            additional_data: Additional performance data
        """
        if self.performance_logger:
            data_str = ""
            if additional_data:
                data_parts = [f"{k}={v}" for k, v in additional_data.items()]
                data_str = f" | {', '.join(data_parts)}"
            
            self.performance_logger.info(
                f"{operation}: {duration:.3f}s{data_str}"
            )
    
    def cleanup_old_logs(self, days_to_keep: Optional[int] = None):
        """Clean up old log files.
        
        Args:
            days_to_keep: Number of days of logs to retain (uses config default if None)
        """
        try:
            # Use provided days_to_keep or fall back to config
            retention_days = days_to_keep if days_to_keep is not None else self.retention_config.log_retention_days
            
            # If retention is disabled (0 days), skip cleanup
            if retention_days <= 0:
                logging.getLogger(__name__).info("Log file retention is disabled - skipping cleanup")
                return
                
            cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 3600)
            
            for log_file in self.log_dir.glob("*.log*"):
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        logging.getLogger(__name__).debug(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to clean up {log_file}: {e}")
                    
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error during log cleanup: {e}")


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def get_logging_manager(log_dir: Optional[str] = None, 
                       retention_config: Optional[RetentionConfig] = None,
                       app_name: str = "medical_processor") -> LoggingManager:
    """Get the global logging manager instance.
    
    Args:
        log_dir: Directory to store log files (only used on first call)
        retention_config: Configuration for log file retention
        app_name: Application name for log files
        
    Returns:
        Global LoggingManager instance
    """
    global _logging_manager
    
    if _logging_manager is None:
        if log_dir is None:
            log_dir = "logs"
        _logging_manager = LoggingManager(log_dir, app_name, retention_config)
    
    return _logging_manager


def setup_logging(log_dir: str, 
                 console_level: str = "INFO",
                 file_level: str = "DEBUG",
                 enable_colors: bool = True,
                 retention_config: Optional[RetentionConfig] = None) -> LoggingManager:
    """Convenience function to set up logging.
    
    Args:
        log_dir: Directory to store log files
        console_level: Logging level for console output
        file_level: Logging level for file output
        enable_colors: Whether to enable colored console output
        retention_config: Configuration for log file retention
        
    Returns:
        Configured LoggingManager instance
    """
    manager = get_logging_manager(log_dir, retention_config)
    manager.setup_logging(
        console_level=console_level,
        file_level=file_level,
        enable_colors=enable_colors
    )
    return manager