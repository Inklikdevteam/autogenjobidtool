"""Job scheduler for the medical document processing system."""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional
import schedule
from croniter import croniter
import pytz

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import ScheduleConfig


logger = logging.getLogger(__name__)


class Scheduler:
    """
    Scheduler class supporting both interval and cron-based scheduling modes.
    
    Supports:
    - Interval-based scheduling with configurable seconds
    - Cron expression scheduling with timezone support
    - Graceful startup and shutdown
    """
    
    def __init__(self, config: ScheduleConfig, job_function: Callable[[], None]):
        """
        Initialize the scheduler.
        
        Args:
            config: Schedule configuration containing interval/cron settings
            job_function: The function to execute on schedule
        """
        self.config = config
        self.job_function = job_function
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Validate configuration
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the schedule configuration."""
        if self.config.poll_cron:
            # Validate cron expression
            try:
                # Test if cron expression is valid
                cron = croniter(self.config.poll_cron)
                # Test getting next execution time
                cron.get_next(datetime)
                logger.info(f"Validated cron expression: {self.config.poll_cron}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid cron expression '{self.config.poll_cron}': {e}")
                
            # Validate timezone
            try:
                pytz.timezone(self.config.timezone)
                logger.info(f"Validated timezone: {self.config.timezone}")
            except pytz.exceptions.UnknownTimeZoneError as e:
                raise ValueError(f"Invalid timezone '{self.config.timezone}': {e}")
        else:
            # Validate interval
            if self.config.poll_interval_seconds <= 0:
                raise ValueError(f"Poll interval must be positive, got: {self.config.poll_interval_seconds}")
            logger.info(f"Validated interval: {self.config.poll_interval_seconds} seconds")
    
    def _setup_interval_schedule(self) -> None:
        """Set up interval-based scheduling."""
        logger.info(f"Setting up interval scheduling: every {self.config.poll_interval_seconds} seconds")
        schedule.every(self.config.poll_interval_seconds).seconds.do(self._safe_job_execution)
        
    def _setup_cron_schedule(self) -> None:
        """Set up cron-based scheduling."""
        logger.info(f"Setting up cron scheduling: {self.config.poll_cron} (timezone: {self.config.timezone})")
        # For cron scheduling, we'll use a different approach since the schedule library
        # doesn't directly support cron expressions. We'll use croniter to calculate
        # next execution times and schedule accordingly.
        self._schedule_next_cron_job()
        
    def _schedule_next_cron_job(self) -> None:
        """Schedule the next cron job execution."""
        if not self._running:
            return
            
        try:
            # Get timezone object
            tz = pytz.timezone(self.config.timezone)
            
            # Get current time in the specified timezone
            now = datetime.now(tz)
            
            # Calculate next execution time
            cron = croniter(self.config.poll_cron, now)
            next_run = cron.get_next(datetime)
            
            # Calculate seconds until next run
            seconds_until_next = (next_run - now).total_seconds()
            
            logger.info(f"Next cron execution scheduled for: {next_run} ({seconds_until_next:.1f} seconds)")
            
            # Schedule the job
            schedule.every(int(seconds_until_next)).seconds.do(self._cron_job_wrapper).tag('cron_job')
            
        except Exception as e:
            logger.error(f"Error scheduling next cron job: {e}")
            # Fallback to interval scheduling
            self._setup_interval_schedule()
    
    def _cron_job_wrapper(self) -> None:
        """Wrapper for cron job execution that reschedules the next run."""
        try:
            # Execute the job
            self._safe_job_execution()
            
            # Clear the current cron job
            schedule.clear('cron_job')
            
            # Schedule the next cron job
            self._schedule_next_cron_job()
            
        except Exception as e:
            logger.error(f"Error in cron job wrapper: {e}")
    
    def _safe_job_execution(self) -> None:
        """Safely execute the job function with error handling."""
        try:
            logger.info("Executing scheduled job")
            start_time = time.time()
            
            self.job_function()
            
            execution_time = time.time() - start_time
            logger.info(f"Job completed successfully in {execution_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error executing scheduled job: {e}", exc_info=True)
    
    def _run_scheduler(self) -> None:
        """Main scheduler loop running in a separate thread."""
        logger.info("Scheduler thread started")
        
        try:
            # Set up the appropriate scheduling mode
            if self.config.poll_cron:
                self._setup_cron_schedule()
            else:
                self._setup_interval_schedule()
            
            # Main scheduling loop
            while self._running and not self._stop_event.is_set():
                try:
                    schedule.run_pending()
                    # Check every second for pending jobs
                    self._stop_event.wait(1.0)
                    
                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                    # Continue running even if there's an error
                    time.sleep(1.0)
                    
        except Exception as e:
            logger.error(f"Fatal error in scheduler thread: {e}", exc_info=True)
        finally:
            logger.info("Scheduler thread stopped")
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
            
        logger.info("Starting scheduler")
        self._running = True
        self._stop_event.clear()
        
        # Start the scheduler thread
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        
        # Log the scheduling mode
        if self.config.poll_cron:
            logger.info(f"Scheduler started in cron mode: {self.config.poll_cron} (timezone: {self.config.timezone})")
        else:
            logger.info(f"Scheduler started in interval mode: every {self.config.poll_interval_seconds} seconds")
    
    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            logger.warning("Scheduler is not running")
            return
            
        logger.info("Stopping scheduler")
        self._running = False
        self._stop_event.set()
        
        # Clear all scheduled jobs
        schedule.clear()
        
        # Wait for the thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("Scheduler thread did not stop within timeout")
            else:
                logger.info("Scheduler stopped successfully")
        
        self._thread = None
    
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._running and self._thread is not None and self._thread.is_alive()
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        try:
            if self.config.poll_cron:
                # For cron scheduling, calculate next run time
                tz = pytz.timezone(self.config.timezone)
                now = datetime.now(tz)
                cron = croniter(self.config.poll_cron, now)
                return cron.get_next(datetime)
            else:
                # For interval scheduling, we can't easily predict the exact next run
                # since it depends on when the last job finished
                return None
                
        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            return None