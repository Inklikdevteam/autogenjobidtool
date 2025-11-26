"""Parallel action executor for WebScribe workflow."""

import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Dict, Any
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import ActionResult
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class ParallelActionExecutor:
    """Executes multiple actions in parallel using thread pool."""
    
    def __init__(self, max_workers: int = 3):
        """Initialize the parallel action executor.
        
        Args:
            max_workers: Maximum number of parallel workers (default: 3 for CSV upload, log, email)
        """
        self.max_workers = max_workers
        logger.info(f"ParallelActionExecutor initialized with {max_workers} workers")
    
    def execute_parallel(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """Execute multiple actions in parallel.
        
        Args:
            actions: List of action dictionaries with 'name' and 'function' keys
                    Example: [{'name': 'upload_csv', 'function': lambda: upload_csv()}]
            
        Returns:
            List[ActionResult]: Results for each action
        """
        if not actions:
            logger.warning("No actions to execute")
            return []
        
        logger.info(f"Starting parallel execution of {len(actions)} actions")
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all actions
            future_to_action = {}
            for action in actions:
                action_name = action.get('name', 'unknown')
                action_func = action.get('function')
                
                if not action_func:
                    logger.error(f"Action {action_name} has no function")
                    results.append(ActionResult(
                        action_name=action_name,
                        success=False,
                        duration=0.0,
                        error_message="No function provided"
                    ))
                    continue
                
                future = executor.submit(self._execute_action, action_name, action_func)
                future_to_action[future] = action_name
            
            # Collect results as they complete
            for future in as_completed(future_to_action):
                action_name = future_to_action[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "✓" if result.success else "✗"
                    logger.info(f"{status} {action_name} completed in {result.duration:.2f}s")
                    
                except Exception as e:
                    logger.error(f"✗ {action_name} raised exception: {e}")
                    results.append(ActionResult(
                        action_name=action_name,
                        success=False,
                        duration=0.0,
                        error_message=str(e)
                    ))
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_duration = sum(r.duration for r in results)
        
        logger.info(f"Parallel execution complete: {successful} successful, {failed} failed, {total_duration:.2f}s total")
        
        return results
    
    def _execute_action(self, action_name: str, action_func: Callable) -> ActionResult:
        """Execute a single action and return result.
        
        Args:
            action_name: Name of the action
            action_func: Function to execute
            
        Returns:
            ActionResult: Result of the action execution
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Executing action: {action_name}")
            
            # Execute the action
            action_func()
            
            duration = time.time() - start_time
            
            return ActionResult(
                action_name=action_name,
                success=True,
                duration=duration,
                error_message=None
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Action {action_name} failed: {error_msg}")
            
            # Handle the error
            handle_error(
                error=e,
                category=ErrorCategory.SYSTEM_RESOURCE,
                severity=ErrorSeverity.MEDIUM,
                component="ParallelActionExecutor",
                operation=f"execute_{action_name}",
                additional_data={
                    "action_name": action_name,
                    "duration": duration
                }
            )
            
            return ActionResult(
                action_name=action_name,
                success=False,
                duration=duration,
                error_message=error_msg
            )
    
    def upload_csv_action(self, csv_path: str, sftp_manager, sftp_config) -> None:
        """Action to upload CSV file to WOLF SFTP.
        
        Args:
            csv_path: Path to CSV file
            sftp_manager: SFTP manager instance
            sftp_config: SFTP configuration
            
        Raises:
            Exception: If upload fails
        """
        logger.info(f"Starting CSV upload action: {csv_path}")
        
        try:
            import os
            csv_filename = os.path.basename(csv_path)
            remote_path = f"{sftp_config.remote_path}/{csv_filename}".replace('//', '/')
            
            # Connect and upload
            with sftp_manager.connect(sftp_config) as sftp_client:
                sftp_manager.upload_file(sftp_client, csv_path, remote_path)
            
            logger.info(f"CSV upload successful: {csv_filename} -> {remote_path}")
            
        except Exception as e:
            logger.error(f"CSV upload failed: {e}")
            raise
    
    def create_log_action(self, date_folder, stats, log_creator) -> None:
        """Action to create processing log.
        
        Args:
            date_folder: Path to date folder
            stats: Processing statistics
            log_creator: ProcessingLogCreator instance
            
        Raises:
            Exception: If log creation fails
        """
        logger.info("Starting log creation action")
        
        try:
            log_path = log_creator.create_log(date_folder, stats)
            logger.info(f"Log creation successful: {log_path}")
            
        except Exception as e:
            logger.error(f"Log creation failed: {e}")
            raise
    
    def send_email_action(self, stats, email_notifier) -> None:
        """Action to send email notification.
        
        Args:
            stats: Processing statistics
            email_notifier: EmailNotifier instance
            
        Raises:
            Exception: If email sending fails
        """
        logger.info("Starting email notification action")
        
        try:
            # Send email with processing stats
            email_notifier.send_webscribe_notification(stats)
            logger.info("Email notification sent successfully")
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            raise
    
    def get_execution_summary(self, results: List[ActionResult]) -> Dict[str, Any]:
        """Generate summary of parallel execution results.
        
        Args:
            results: List of action results
            
        Returns:
            Dict: Summary statistics
        """
        if not results:
            return {
                'total_actions': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'total_duration': 0.0,
                'average_duration': 0.0
            }
        
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_duration = sum(r.duration for r in results)
        average_duration = total_duration / len(results) if results else 0.0
        success_rate = (successful / len(results)) * 100 if results else 0.0
        
        summary = {
            'total_actions': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate,
            'total_duration': total_duration,
            'average_duration': average_duration,
            'actions': {r.action_name: r.success for r in results}
        }
        
        return summary
    
    def all_actions_successful(self, results: List[ActionResult]) -> bool:
        """Check if all actions were successful.
        
        Args:
            results: List of action results
            
        Returns:
            bool: True if all actions succeeded
        """
        return all(r.success for r in results)
    
    def get_failed_actions(self, results: List[ActionResult]) -> List[ActionResult]:
        """Get list of failed actions.
        
        Args:
            results: List of action results
            
        Returns:
            List[ActionResult]: List of failed actions
        """
        return [r for r in results if not r.success]
    
    def get_successful_actions(self, results: List[ActionResult]) -> List[ActionResult]:
        """Get list of successful actions.
        
        Args:
            results: List of action results
            
        Returns:
            List[ActionResult]: List of successful actions
        """
        return [r for r in results if r.success]
