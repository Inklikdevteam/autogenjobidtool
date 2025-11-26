"""File tracking and processing history management using SQLite database."""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import ProcessingRecord, RetentionConfig

logger = logging.getLogger(__name__)


class FileTracker:
    """Manages file processing history and tracks processed files using SQLite database."""
    
    def __init__(self, db_path: str = "processing_history.db", retention_config: Optional[RetentionConfig] = None):
        """Initialize FileTracker with database path.
        
        Args:
            db_path: Path to SQLite database file
            retention_config: Configuration for processing record retention
        """
        self.db_path = db_path
        self.retention_config = retention_config or RetentionConfig()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the SQLite database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create processing_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processing_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        modification_time TEXT NOT NULL,
                        processed_time TEXT NOT NULL,
                        status TEXT NOT NULL,
                        csv_filename TEXT,
                        error_message TEXT,
                        UNIQUE(filename, modification_time)
                    )
                """)
                
                # Create index for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_filename_mtime 
                    ON processing_history(filename, modification_time)
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def is_file_processed(self, filename: str, mtime: datetime) -> bool:
        """Check if a file has been processed with the given modification time.
        
        Args:
            filename: Name of the file to check
            mtime: Modification time of the file
            
        Returns:
            True if file has been processed with this modification time, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM processing_history 
                    WHERE filename = ? AND modification_time = ? AND status = 'success'
                """, (filename, mtime.isoformat()))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except sqlite3.Error as e:
            logger.error(f"Failed to check if file is processed: {e}")
            return False
    
    def mark_file_processed(self, filename: str, mtime: datetime, status: str = 'success', 
                          csv_filename: Optional[str] = None, error_message: Optional[str] = None) -> None:
        """Mark a file as processed with the given status.
        
        Args:
            filename: Name of the processed file
            mtime: Modification time of the file
            status: Processing status ('success', 'failed', 'partial')
            csv_filename: Name of generated CSV file (if successful)
            error_message: Error message (if failed)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                processed_time = datetime.now()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO processing_history 
                    (filename, modification_time, processed_time, status, csv_filename, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (filename, mtime.isoformat(), processed_time.isoformat(), 
                     status, csv_filename, error_message))
                
                conn.commit()
                logger.info(f"Marked file {filename} as {status}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to mark file as processed: {e}")
            raise
    
    def get_processing_history(self, limit: Optional[int] = None) -> List[ProcessingRecord]:
        """Get processing history records, ordered by processed time (most recent first).
        
        Args:
            limit: Maximum number of records to return (None for all)
            
        Returns:
            List of ProcessingRecord objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT filename, modification_time, processed_time, status, csv_filename, error_message
                    FROM processing_history 
                    ORDER BY processed_time DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    records.append(ProcessingRecord(
                        filename=row[0],
                        modification_time=row[1],  # Keep as ISO string
                        processed_time=row[2],     # Keep as ISO string
                        status=row[3],
                        csv_filename=row[4],
                        error_message=row[5]
                    ))
                
                return records
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get processing history: {e}")
            return []
    
    def get_file_last_processed(self, filename: str) -> Optional[Tuple[datetime, str]]:
        """Get the last processing time and status for a specific file.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            Tuple of (processed_time, status) or None if file was never processed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT processed_time, status FROM processing_history 
                    WHERE filename = ? 
                    ORDER BY processed_time DESC 
                    LIMIT 1
                """, (filename,))
                
                row = cursor.fetchone()
                if row:
                    return (datetime.fromisoformat(row[0]), row[1])
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get last processed time for file: {e}")
            return None
    
    def cleanup_old_records(self, days_to_keep: Optional[int] = None) -> int:
        """Remove processing records older than specified number of days.
        
        Args:
            days_to_keep: Number of days to keep records (uses config default if None)
            
        Returns:
            Number of records deleted
        """
        try:
            # Use provided days_to_keep or fall back to config
            retention_days = days_to_keep if days_to_keep is not None else self.retention_config.processing_records_retention_days
            
            # If retention is disabled (0 days), skip cleanup
            if retention_days <= 0:
                logger.info("Processing records retention is disabled - skipping cleanup")
                return 0
                
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM processing_history 
                    WHERE processed_time < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old processing records")
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0
    
    def get_processing_stats(self, days: int = 30) -> dict:
        """Get processing statistics for the last N days.
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get overall stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_files,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'partial' THEN 1 ELSE 0 END) as partial
                    FROM processing_history 
                    WHERE processed_time >= ?
                """, (cutoff_date.isoformat(),))
                
                row = cursor.fetchone()
                
                return {
                    'total_files': row[0] or 0,
                    'successful': row[1] or 0,
                    'failed': row[2] or 0,
                    'partial': row[3] or 0,
                    'success_rate': (row[1] or 0) / max(row[0] or 1, 1) * 100
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {
                'total_files': 0,
                'successful': 0,
                'failed': 0,
                'partial': 0,
                'success_rate': 0.0
            }
    
    def close(self) -> None:
        """Close database connections and cleanup resources."""
        # SQLite connections are automatically closed when using context managers
        # This method is provided for interface consistency
        logger.info("FileTracker closed")