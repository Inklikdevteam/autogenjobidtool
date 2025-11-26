"""Configuration manager for the medical document processing system."""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

from .models import (
    SFTPConfig, FTPSConfig, TypeFolderConfig,
    EmailConfig, ScheduleConfig, StorageConfig, RetentionConfig
)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigManager:
    """Manages configuration loading and validation for the application."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        load_dotenv()
        self._config = self._load_config()
        self._validate_required_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            # Source FTPS Configuration (WebScribe workflow)
            'SOURCE_FTPS_HOST': os.getenv('SOURCE_FTPS_HOST'),
            'SOURCE_FTPS_PORT': int(os.getenv('SOURCE_FTPS_PORT', '21')),
            'SOURCE_FTPS_USERNAME': os.getenv('SOURCE_FTPS_USERNAME'),
            'SOURCE_FTPS_PASSWORD': os.getenv('SOURCE_FTPS_PASSWORD'),
            'SOURCE_FTPS_PATH': os.getenv('SOURCE_FTPS_PATH', '/'),
            'SOURCE_FTPS_USE_TLS': os.getenv('SOURCE_FTPS_USE_TLS', 'true').lower() == 'true',
            'SOURCE_FTPS_PASSIVE_MODE': os.getenv('SOURCE_FTPS_PASSIVE_MODE', 'true').lower() == 'true',
            
            # Destination SFTP Configuration
            'DEST_SFTP_HOST': os.getenv('DEST_SFTP_HOST'),
            'DEST_SFTP_PORT': int(os.getenv('DEST_SFTP_PORT', '22')),
            'DEST_SFTP_USERNAME': os.getenv('DEST_SFTP_USERNAME'),
            'DEST_SFTP_PASSWORD': os.getenv('DEST_SFTP_PASSWORD'),
            'DEST_SFTP_PATH': os.getenv('DEST_SFTP_PATH', '/'),
            
            # Email Configuration
            'SMTP_HOST': os.getenv('SMTP_HOST'),
            'SMTP_PORT': int(os.getenv('SMTP_PORT', '587')),
            'SMTP_USERNAME': os.getenv('SMTP_USERNAME'),
            'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD'),
            'SMTP_FROM': os.getenv('SMTP_FROM'),
            'ADMIN_EMAIL': os.getenv('ADMIN_EMAIL'),
            
            # Scheduling Configuration
            'POLL_INTERVAL_SECONDS': int(os.getenv('POLL_INTERVAL_SECONDS', '60')),
            'POLL_CRON': os.getenv('POLL_CRON'),
            'TZ': os.getenv('TZ', 'UTC'),
            
            # Storage Configuration
            'LOCAL_STORAGE_PATH': os.getenv('LOCAL_STORAGE_PATH', './data'),
            'TEMP_PATH': os.getenv('TEMP_PATH', './temp'),
            'ZIP_BACKUP_PATH': os.getenv('ZIP_BACKUP_PATH', './data/AutogenJobID/zipfile-backups'),
            
            # Retention Configuration (0 = disabled)
            'CSV_RETENTION_DAYS': int(os.getenv('CSV_RETENTION_DAYS', '0')),
            'LOG_RETENTION_DAYS': int(os.getenv('LOG_RETENTION_DAYS', '0')),
            'ERROR_LOG_RETENTION_DAYS': int(os.getenv('ERROR_LOG_RETENTION_DAYS', '0')),
            'PROCESSING_RECORDS_RETENTION_DAYS': int(os.getenv('PROCESSING_RECORDS_RETENTION_DAYS', '0')),
            'ZIP_BACKUP_RETENTION_DAYS': int(os.getenv('ZIP_BACKUP_RETENTION_DAYS', '0')),
            
            # Type Folders Configuration (WebScribe workflow)
            'TYPE_FOLDERS': os.getenv('TYPE_FOLDERS', 'type3,type6,type7,type16,type18,type19,type20,type21,type22,type23,type24'),
            
            # Date Folder Configuration (WebScribe workflow)
            'USE_YESTERDAY_DATE': os.getenv('USE_YESTERDAY_DATE', 'true').lower() == 'true',
            'DATE_FOLDER_BASE_PATH': os.getenv('DATE_FOLDER_BASE_PATH', './data/processing'),
        }
    
    def _validate_required_config(self) -> None:
        """Validate that all required configuration is present."""
        required_fields = [
            'SOURCE_FTPS_HOST',
            'SOURCE_FTPS_USERNAME',
            'SOURCE_FTPS_PASSWORD',
            'DEST_SFTP_HOST',
            'DEST_SFTP_USERNAME',
            'DEST_SFTP_PASSWORD',
            'SMTP_HOST',
            'SMTP_USERNAME',
            'SMTP_PASSWORD',
            'ADMIN_EMAIL'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not self._config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_fields)}"
            )
        
        # Validate port numbers
        if not (1 <= self._config['SOURCE_FTPS_PORT'] <= 65535):
            raise ConfigurationError("SOURCE_FTPS_PORT must be between 1 and 65535")
        
        if not (1 <= self._config['DEST_SFTP_PORT'] <= 65535):
            raise ConfigurationError("DEST_SFTP_PORT must be between 1 and 65535")
        
        if not (1 <= self._config['SMTP_PORT'] <= 65535):
            raise ConfigurationError("SMTP_PORT must be between 1 and 65535")
        
        # Validate poll interval
        if self._config['POLL_INTERVAL_SECONDS'] < 1:
            raise ConfigurationError("POLL_INTERVAL_SECONDS must be at least 1")
    
    def get_dest_sftp_config(self) -> SFTPConfig:
        """Get destination SFTP server configuration."""
        return SFTPConfig(
            host=self._config['DEST_SFTP_HOST'],
            port=self._config['DEST_SFTP_PORT'],
            username=self._config['DEST_SFTP_USERNAME'],
            password=self._config['DEST_SFTP_PASSWORD'],
            remote_path=self._config['DEST_SFTP_PATH']
        )
    
    def get_email_config(self) -> EmailConfig:
        """Get email notification configuration."""
        # Parse multiple emails from ADMIN_EMAIL if comma-separated
        admin_email = self._config['ADMIN_EMAIL']
        admin_emails = None
        
        if ',' in admin_email:
            # Split by comma and clean up whitespace
            admin_emails = [email.strip() for email in admin_email.split(',') if email.strip()]
            # Use first email as primary admin_email for backward compatibility
            admin_email = admin_emails[0] if admin_emails else admin_email
        
        return EmailConfig(
            smtp_host=self._config['SMTP_HOST'],
            smtp_port=self._config['SMTP_PORT'],
            smtp_username=self._config['SMTP_USERNAME'],
            smtp_password=self._config['SMTP_PASSWORD'],
            admin_email=admin_email,
            admin_emails=admin_emails,
            smtp_from=self._config.get('SMTP_FROM', self._config['SMTP_USERNAME'])
        )
    
    def get_schedule_config(self) -> ScheduleConfig:
        """Get scheduling configuration."""
        return ScheduleConfig(
            poll_interval_seconds=self._config['POLL_INTERVAL_SECONDS'],
            poll_cron=self._config['POLL_CRON'],
            timezone=self._config['TZ']
        )
    
    def get_storage_config(self) -> StorageConfig:
        """Get storage configuration."""
        return StorageConfig(
            local_storage_path=self._config['LOCAL_STORAGE_PATH'],
            temp_path=self._config['TEMP_PATH'],
            zip_backup_path=self._config['ZIP_BACKUP_PATH']
        )
    
    def get_retention_config(self) -> RetentionConfig:
        """Get file retention configuration."""
        return RetentionConfig(
            csv_retention_days=self._config['CSV_RETENTION_DAYS'],
            log_retention_days=self._config['LOG_RETENTION_DAYS'],
            error_log_retention_days=self._config['ERROR_LOG_RETENTION_DAYS'],
            processing_records_retention_days=self._config['PROCESSING_RECORDS_RETENTION_DAYS'],
            zip_backup_retention_days=self._config['ZIP_BACKUP_RETENTION_DAYS']
        )
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        return self._config.get(key, default)
    
    def get_source_ftps_config(self) -> FTPSConfig:
        """Get source FTPS server configuration for WebScribe workflow."""
        return FTPSConfig(
            host=self._config.get('SOURCE_FTPS_HOST', ''),
            port=self._config.get('SOURCE_FTPS_PORT', 21),
            username=self._config.get('SOURCE_FTPS_USERNAME', ''),
            password=self._config.get('SOURCE_FTPS_PASSWORD', ''),
            remote_path=self._config.get('SOURCE_FTPS_PATH', '/'),
            use_tls=self._config.get('SOURCE_FTPS_USE_TLS', True),
            passive_mode=self._config.get('SOURCE_FTPS_PASSIVE_MODE', True)
        )
    
    def get_type_folder_config(self) -> TypeFolderConfig:
        """Get type folder configuration for WebScribe workflow."""
        type_folders_str = self._config.get('TYPE_FOLDERS', '')
        folders = [f.strip() for f in type_folders_str.split(',') if f.strip()]
        
        return TypeFolderConfig(
            folders=folders,
            base_path=self._config.get('SOURCE_FTPS_PATH', '/')
        )
    
    def get_date_folder_config(self) -> Dict[str, Any]:
        """Get date folder configuration for WebScribe workflow."""
        return {
            'use_yesterday_date': self._config.get('USE_YESTERDAY_DATE', True),
            'base_path': self._config.get('DATE_FOLDER_BASE_PATH', './data/processing')
        }