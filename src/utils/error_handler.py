"""Comprehensive error handling and logging system for the medical document processing system."""

import logging
import traceback
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import RetentionConfig


class ErrorCategory(Enum):
    """Categories of errors that can occur in the system."""
    CONFIGURATION = "configuration"
    SFTP_CONNECTION = "sftp_connection"
    SFTP_FILE_OPERATION = "sftp_file_operation"
    FILE_PROCESSING = "file_processing"
    DOCUMENT_PARSING = "document_parsing"
    EMAIL_NOTIFICATION = "email_notification"
    DATABASE_OPERATION = "database_operation"
    SYSTEM_RESOURCE = "system_resource"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    CRITICAL = "critical"  # System cannot continue
    HIGH = "high"         # Major functionality affected
    MEDIUM = "medium"     # Some functionality affected
    LOW = "low"          # Minor issues, system continues normally


@dataclass
class ErrorContext:
    """Context information for an error occurrence."""
    timestamp: datetime = field(default_factory=datetime.now)
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    component: str = ""
    operation: str = ""
    error_message: str = ""
    exception_type: str = ""
    stack_trace: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 0
    is_recoverable: bool = True


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True


class ErrorHandler:
    """Comprehensive error handler with categorized error handling, retry logic, and context tracking."""
    
    def __init__(self, storage_path: Optional[str] = None, retention_config: Optional[RetentionConfig] = None):
        """Initialize the error handler.
        
        Args:
            storage_path: Path to store error logs and context data
            retention_config: Configuration for error log retention
        """
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(storage_path) if storage_path else Path("data/errors")
        self.retention_config = retention_config or RetentionConfig()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Error tracking
        self.error_history: List[ErrorContext] = []
        self.error_counts: Dict[str, int] = {}
        self.last_error_times: Dict[str, datetime] = {}
        
        # Retry configurations for different error categories
        self.retry_configs = {
            ErrorCategory.SFTP_CONNECTION: RetryConfig(max_attempts=5, base_delay=2.0),
            ErrorCategory.SFTP_FILE_OPERATION: RetryConfig(max_attempts=3, base_delay=1.0),
            ErrorCategory.EMAIL_NOTIFICATION: RetryConfig(max_attempts=3, base_delay=2.0),
            ErrorCategory.DATABASE_OPERATION: RetryConfig(max_attempts=3, base_delay=0.5),
            ErrorCategory.FILE_PROCESSING: RetryConfig(max_attempts=2, base_delay=1.0),
            ErrorCategory.DOCUMENT_PARSING: RetryConfig(max_attempts=1, base_delay=0.0),  # No retry for parsing
            ErrorCategory.CONFIGURATION: RetryConfig(max_attempts=1, base_delay=0.0),     # No retry for config
            ErrorCategory.VALIDATION: RetryConfig(max_attempts=1, base_delay=0.0),        # No retry for validation
        }
        
        # Initialize error log file
        self.error_log_file = self.storage_path / "error_context.jsonl"
        
        self.logger.info("ErrorHandler initialized successfully")
    
    def handle_error(self, 
                    error: Exception, 
                    category: ErrorCategory,
                    severity: ErrorSeverity,
                    component: str,
                    operation: str,
                    additional_data: Optional[Dict[str, Any]] = None,
                    retry_count: int = 0,
                    max_retries: int = 0) -> ErrorContext:
        """Handle an error with comprehensive logging and context tracking.
        
        Args:
            error: The exception that occurred
            category: Category of the error
            severity: Severity level of the error
            component: Component where the error occurred
            operation: Operation being performed when error occurred
            additional_data: Additional context data
            retry_count: Current retry attempt number
            max_retries: Maximum number of retries configured
            
        Returns:
            ErrorContext object with error details
        """
        # Create error context
        context = ErrorContext(
            category=category,
            severity=severity,
            component=component,
            operation=operation,
            error_message=str(error),
            exception_type=type(error).__name__,
            stack_trace=traceback.format_exc(),
            additional_data=additional_data or {},
            retry_count=retry_count,
            max_retries=max_retries,
            is_recoverable=self._is_recoverable_error(error, category)
        )
        
        # Log the error with appropriate level
        self._log_error(context)
        
        # Track error statistics
        self._track_error_statistics(context)
        
        # Store error context
        self._store_error_context(context)
        
        # Add to error history (keep last 1000 errors)
        self.error_history.append(context)
        if len(self.error_history) > 1000:
            self.error_history.pop(0)
        
        return context
    
    def execute_with_retry(self,
                          operation: Callable,
                          category: ErrorCategory,
                          component: str,
                          operation_name: str,
                          additional_data: Optional[Dict[str, Any]] = None) -> Any:
        """Execute an operation with automatic retry logic.
        
        Args:
            operation: Function to execute
            category: Error category for retry configuration
            component: Component performing the operation
            operation_name: Name of the operation for logging
            additional_data: Additional context data
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If operation fails after all retries
        """
        retry_config = self.retry_configs.get(category, RetryConfig())
        last_error = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                if attempt > 0:
                    delay = self._calculate_retry_delay(attempt, retry_config)
                    self.logger.info(f"Retrying {operation_name} in {delay:.2f} seconds (attempt {attempt + 1}/{retry_config.max_attempts})")
                    time.sleep(delay)
                
                result = operation()
                
                if attempt > 0:
                    self.logger.info(f"Operation {operation_name} succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Determine severity based on attempt number
                if attempt == retry_config.max_attempts - 1:
                    severity = self._determine_error_severity(e, category)
                else:
                    severity = ErrorSeverity.LOW  # Lower severity for retryable attempts
                
                # Handle the error
                context = self.handle_error(
                    error=e,
                    category=category,
                    severity=severity,
                    component=component,
                    operation=operation_name,
                    additional_data=additional_data,
                    retry_count=attempt,
                    max_retries=retry_config.max_attempts - 1
                )
                
                # Check if error is recoverable
                if not context.is_recoverable:
                    self.logger.error(f"Non-recoverable error in {operation_name}, stopping retries")
                    break
        
        # All retries exhausted
        if last_error:
            self.logger.error(f"Operation {operation_name} failed after {retry_config.max_attempts} attempts")
            raise last_error
    
    def _log_error(self, context: ErrorContext):
        """Log error with appropriate level and formatting."""
        log_message = (f"[{context.category.value.upper()}] {context.component}.{context.operation}: "
                      f"{context.error_message}")
        
        if context.retry_count > 0:
            log_message += f" (retry {context.retry_count}/{context.max_retries})"
        
        if context.additional_data:
            log_message += f" | Context: {context.additional_data}"
        
        # Log based on severity
        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=True)
        elif context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Always log stack trace for debugging at debug level
        if context.stack_trace:
            self.logger.debug(f"Stack trace for {context.component}.{context.operation}:\n{context.stack_trace}")
    
    def _track_error_statistics(self, context: ErrorContext):
        """Track error statistics for monitoring and reporting."""
        error_key = f"{context.category.value}:{context.component}:{context.operation}"
        
        # Update error counts
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_times[error_key] = context.timestamp
        
        # Log statistics periodically
        if self.error_counts[error_key] % 10 == 0:
            self.logger.warning(f"Error {error_key} has occurred {self.error_counts[error_key]} times")
    
    def _store_error_context(self, context: ErrorContext):
        """Store error context to persistent storage for analysis."""
        try:
            error_data = {
                "timestamp": context.timestamp.isoformat(),
                "category": context.category.value,
                "severity": context.severity.value,
                "component": context.component,
                "operation": context.operation,
                "error_message": context.error_message,
                "exception_type": context.exception_type,
                "retry_count": context.retry_count,
                "max_retries": context.max_retries,
                "is_recoverable": context.is_recoverable,
                "additional_data": context.additional_data
            }
            
            # Append to JSONL file
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_data) + '\n')
                
        except Exception as e:
            self.logger.warning(f"Failed to store error context: {e}")
    
    def _is_recoverable_error(self, error: Exception, category: ErrorCategory) -> bool:
        """Determine if an error is recoverable and should be retried."""
        # Configuration and validation errors are not recoverable
        if category in [ErrorCategory.CONFIGURATION, ErrorCategory.VALIDATION]:
            return False
        
        # Check specific exception types
        error_type = type(error).__name__
        
        # Non-recoverable error types
        non_recoverable_types = [
            'FileNotFoundError',
            'PermissionError',
            'AuthenticationError',
            'SMTPAuthenticationError',
            'SMTPRecipientsRefused',
            'ValueError',
            'TypeError',
            'AttributeError'
        ]
        
        if error_type in non_recoverable_types:
            return False
        
        # Check error message for non-recoverable patterns
        error_message = str(error).lower()
        non_recoverable_patterns = [
            'authentication failed',
            'invalid credentials',
            'permission denied',
            'file not found',
            'invalid format',
            'malformed',
            'corrupt'
        ]
        
        for pattern in non_recoverable_patterns:
            if pattern in error_message:
                return False
        
        return True
    
    def _determine_error_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine the severity of an error based on its type and category."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Critical errors that stop the system
        if category == ErrorCategory.CONFIGURATION:
            return ErrorSeverity.CRITICAL
        
        if error_type in ['SystemExit', 'KeyboardInterrupt', 'MemoryError']:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.SFTP_CONNECTION, ErrorCategory.DATABASE_OPERATION]:
            return ErrorSeverity.HIGH
        
        if 'authentication' in error_message or 'permission' in error_message:
            return ErrorSeverity.HIGH
        
        # Medium severity errors (default)
        if category in [ErrorCategory.FILE_PROCESSING, ErrorCategory.EMAIL_NOTIFICATION]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        if category in [ErrorCategory.DOCUMENT_PARSING, ErrorCategory.VALIDATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _calculate_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay before retry attempt."""
        if config.exponential_backoff:
            delay = min(config.base_delay * (2 ** attempt), config.max_delay)
        else:
            delay = config.base_delay
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary containing error statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter recent errors
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        # Calculate statistics
        stats = {
            "total_errors": len(recent_errors),
            "time_period_hours": hours,
            "errors_by_category": {},
            "errors_by_severity": {},
            "errors_by_component": {},
            "most_frequent_errors": {},
            "recent_critical_errors": []
        }
        
        for error in recent_errors:
            # By category
            category = error.category.value
            stats["errors_by_category"][category] = stats["errors_by_category"].get(category, 0) + 1
            
            # By severity
            severity = error.severity.value
            stats["errors_by_severity"][severity] = stats["errors_by_severity"].get(severity, 0) + 1
            
            # By component
            component = error.component
            stats["errors_by_component"][component] = stats["errors_by_component"].get(component, 0) + 1
            
            # Track critical errors
            if error.severity == ErrorSeverity.CRITICAL:
                stats["recent_critical_errors"].append({
                    "timestamp": error.timestamp.isoformat(),
                    "component": error.component,
                    "operation": error.operation,
                    "message": error.error_message
                })
        
        # Most frequent error types
        error_type_counts = {}
        for error in recent_errors:
            error_key = f"{error.category.value}:{error.exception_type}"
            error_type_counts[error_key] = error_type_counts.get(error_key, 0) + 1
        
        # Sort by frequency
        stats["most_frequent_errors"] = dict(sorted(error_type_counts.items(), 
                                                   key=lambda x: x[1], 
                                                   reverse=True)[:10])
        
        return stats
    
    def cleanup_old_error_logs(self, days_to_keep: Optional[int] = None):
        """Clean up old error log entries.
        
        Args:
            days_to_keep: Number of days of error logs to retain (uses config default if None)
        """
        try:
            # Use provided days_to_keep or fall back to config
            retention_days = days_to_keep if days_to_keep is not None else self.retention_config.error_log_retention_days
            
            # If retention is disabled (0 days), skip cleanup
            if retention_days <= 0:
                self.logger.info("Error log retention is disabled - skipping cleanup")
                return
                
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            # Clean up in-memory error history
            self.error_history = [e for e in self.error_history if e.timestamp >= cutoff_time]
            
            # Clean up persistent error log file
            if self.error_log_file.exists():
                temp_file = self.error_log_file.with_suffix('.tmp')
                
                with open(self.error_log_file, 'r', encoding='utf-8') as infile, \
                     open(temp_file, 'w', encoding='utf-8') as outfile:
                    
                    for line in infile:
                        try:
                            error_data = json.loads(line.strip())
                            error_time = datetime.fromisoformat(error_data['timestamp'])
                            
                            if error_time >= cutoff_time:
                                outfile.write(line)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            # Skip malformed lines
                            continue
                
                # Replace original file with cleaned version
                temp_file.replace(self.error_log_file)
                
                self.logger.info(f"Cleaned up error logs older than {days_to_keep} days")
                
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old error logs: {e}")
    
    def generate_error_report(self, hours: int = 24) -> str:
        """Generate a human-readable error report.
        
        Args:
            hours: Number of hours to include in the report
            
        Returns:
            Formatted error report string
        """
        stats = self.get_error_statistics(hours)
        
        report = f"""
ERROR REPORT - Last {hours} Hours
{'=' * 50}

SUMMARY:
- Total Errors: {stats['total_errors']}
- Time Period: {hours} hours

ERRORS BY SEVERITY:
"""
        
        for severity, count in stats['errors_by_severity'].items():
            report += f"- {severity.upper()}: {count}\n"
        
        report += "\nERRORS BY CATEGORY:\n"
        for category, count in stats['errors_by_category'].items():
            report += f"- {category.upper()}: {count}\n"
        
        report += "\nERRORS BY COMPONENT:\n"
        for component, count in stats['errors_by_component'].items():
            report += f"- {component}: {count}\n"
        
        if stats['most_frequent_errors']:
            report += "\nMOST FREQUENT ERROR TYPES:\n"
            for error_type, count in list(stats['most_frequent_errors'].items())[:5]:
                report += f"- {error_type}: {count}\n"
        
        if stats['recent_critical_errors']:
            report += "\nRECENT CRITICAL ERRORS:\n"
            for error in stats['recent_critical_errors'][-5:]:  # Last 5 critical errors
                report += f"- {error['timestamp']}: {error['component']}.{error['operation']} - {error['message']}\n"
        
        return report


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler(storage_path: Optional[str] = None, retention_config: Optional[RetentionConfig] = None) -> ErrorHandler:
    """Get the global error handler instance.
    
    Args:
        storage_path: Path to store error logs (only used on first call)
        retention_config: Configuration for error log retention
        
    Returns:
        Global ErrorHandler instance
    """
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(storage_path, retention_config)
    
    return _global_error_handler


def handle_error(error: Exception,
                category: ErrorCategory,
                severity: ErrorSeverity,
                component: str,
                operation: str,
                additional_data: Optional[Dict[str, Any]] = None,
                retry_count: int = 0,
                max_retries: int = 0) -> ErrorContext:
    """Convenience function to handle errors using the global error handler.
    
    Args:
        error: The exception that occurred
        category: Category of the error
        severity: Severity level of the error
        component: Component where the error occurred
        operation: Operation being performed when error occurred
        additional_data: Additional context data
        retry_count: Current retry attempt number
        max_retries: Maximum number of retries configured
        
    Returns:
        ErrorContext object with error details
    """
    return get_error_handler().handle_error(
        error=error,
        category=category,
        severity=severity,
        component=component,
        operation=operation,
        additional_data=additional_data,
        retry_count=retry_count,
        max_retries=max_retries
    )


def execute_with_retry(operation: Callable,
                      category: ErrorCategory,
                      component: str,
                      operation_name: str,
                      additional_data: Optional[Dict[str, Any]] = None) -> Any:
    """Convenience function to execute operations with retry using the global error handler.
    
    Args:
        operation: Function to execute
        category: Error category for retry configuration
        component: Component performing the operation
        operation_name: Name of the operation for logging
        additional_data: Additional context data
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: If operation fails after all retries
    """
    return get_error_handler().execute_with_retry(
        operation=operation,
        category=category,
        component=component,
        operation_name=operation_name,
        additional_data=additional_data
    )