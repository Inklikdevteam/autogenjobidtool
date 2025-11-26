"""SFTP Manager for handling remote file operations."""

import os
import time
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

import paramiko
from paramiko import SFTPClient, SSHClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import SFTPConfig
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class SFTPError(Exception):
    """Base exception for SFTP operations."""
    pass


class SFTPConnectionError(SFTPError):
    """Raised when SFTP connection fails."""
    pass


class SFTPFileError(SFTPError):
    """Raised when SFTP file operations fail."""
    pass


@dataclass
class FileInfo:
    """Information about a remote file."""
    filename: str
    full_path: str
    size: int
    mtime: datetime
    is_directory: bool = False


class SFTPManager:
    """Manages SFTP connections and file operations with retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize SFTP manager.
        
        Args:
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._ssh_client = None
        self._sftp_client = None
    
    @contextmanager
    def connect(self, config: SFTPConfig):
        """
        Context manager for SFTP connections with automatic cleanup.
        
        Args:
            config: SFTP configuration
            
        Yields:
            SFTPClient: Connected SFTP client
            
        Raises:
            SFTPConnectionError: If connection fails after all retries
        """
        client = None
        try:
            client = self._establish_connection(config)
            yield client
        finally:
            if client:
                self._close_connection()
    
    def _establish_connection(self, config: SFTPConfig) -> SFTPClient:
        """
        Establish SFTP connection with retry logic.
        
        Args:
            config: SFTP configuration
            
        Returns:
            SFTPClient: Connected SFTP client
            
        Raises:
            SFTPConnectionError: If connection fails after all retries
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting SFTP connection to {config.host}:{config.port} (attempt {attempt + 1}/{self.max_retries})")
                
                # Create SSH client
                self._ssh_client = SSHClient()
                self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect with timeout
                self._ssh_client.connect(
                    hostname=config.host,
                    port=config.port,
                    username=config.username,
                    password=config.password,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=30
                )
                
                # Open SFTP channel
                self._sftp_client = self._ssh_client.open_sftp()
                
                # Test connection by listing the remote path
                try:
                    self._sftp_client.listdir(config.remote_path)
                    logger.debug(f"Verified remote path exists: {config.remote_path}")
                except FileNotFoundError:
                    logger.warning(f"Remote path {config.remote_path} does not exist, will be created if needed")
                
                logger.info(f"Successfully connected to SFTP server {config.host}:{config.port}")
                return self._sftp_client
                
            except Exception as e:
                last_error = e
                
                # Determine error severity based on attempt number and error type
                severity = ErrorSeverity.HIGH if attempt == self.max_retries - 1 else ErrorSeverity.MEDIUM
                
                # Handle the connection error
                handle_error(
                    error=e,
                    category=ErrorCategory.SFTP_CONNECTION,
                    severity=severity,
                    component="SFTPManager",
                    operation="establish_connection",
                    additional_data={
                        "host": config.host,
                        "port": config.port,
                        "username": config.username,
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries
                    },
                    retry_count=attempt,
                    max_retries=self.max_retries - 1
                )
                
                # Clean up failed connection
                self._close_connection()
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to connect to SFTP server {config.host}:{config.port} after {self.max_retries} attempts"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        logger.error(error_msg)
        raise SFTPConnectionError(error_msg)
    
    def _close_connection(self):
        """Close SFTP and SSH connections."""
        if self._sftp_client:
            try:
                self._sftp_client.close()
            except Exception as e:
                logger.warning(f"Error closing SFTP client: {e}")
            finally:
                self._sftp_client = None
        
        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception as e:
                logger.warning(f"Error closing SSH client: {e}")
            finally:
                self._ssh_client = None
    
    def list_zip_files(self, client: SFTPClient, remote_path: str) -> List[FileInfo]:
        """
        List all ZIP files in the remote directory.
        
        Args:
            client: Connected SFTP client
            remote_path: Remote directory path to scan
            
        Returns:
            List of FileInfo objects for ZIP files
            
        Raises:
            SFTPFileError: If listing files fails
        """
        try:
            logger.debug(f"Listing ZIP files in remote path: {remote_path}")
            
            # Ensure remote path exists
            try:
                file_list = client.listdir(remote_path)
                logger.debug(f"Found {len(file_list)} total files in {remote_path}")
            except FileNotFoundError:
                logger.warning(f"Remote path {remote_path} does not exist")
                return []
            
            zip_files = []
            
            # List all files in the directory
            for filename in file_list:
                if filename.lower().endswith('.zip'):
                    full_path = os.path.join(remote_path, filename).replace('\\', '/')
                    
                    try:
                        # Get file attributes
                        attrs = client.stat(full_path)
                        file_info = FileInfo(
                            filename=filename,
                            full_path=full_path,
                            size=attrs.st_size,
                            mtime=datetime.fromtimestamp(attrs.st_mtime),
                            is_directory=False
                        )
                        zip_files.append(file_info)
                        logger.debug(f"Found ZIP file: {filename} ({attrs.st_size} bytes)")
                        
                    except Exception as e:
                        logger.warning(f"Could not get attributes for {filename}: {e}")
                        handle_error(
                            error=e,
                            category=ErrorCategory.SFTP_FILE_OPERATION,
                            severity=ErrorSeverity.LOW,
                            component="SFTPManager",
                            operation="get_file_attributes",
                            additional_data={
                                "filename": filename,
                                "remote_path": remote_path
                            }
                        )
                        continue
            
            logger.info(f"Found {len(zip_files)} ZIP files in {remote_path}")
            return zip_files
            
        except Exception as e:
            error_msg = f"Failed to list ZIP files in {remote_path}: {str(e)}"
            logger.error(error_msg)
            
            handle_error(
                error=e,
                category=ErrorCategory.SFTP_FILE_OPERATION,
                severity=ErrorSeverity.HIGH,
                component="SFTPManager",
                operation="list_zip_files",
                additional_data={"remote_path": remote_path}
            )
            
            raise SFTPFileError(error_msg)
    
    def download_file(self, client: SFTPClient, remote_path: str, local_path: str) -> bool:
        """
        Download a file from the remote server with retry logic.
        
        Args:
            client: Connected SFTP client
            remote_path: Path to remote file
            local_path: Path to save local file
            
        Returns:
            True if download successful, False otherwise
            
        Raises:
            SFTPFileError: If download fails after all retries
        """
        # Ensure local directory exists
        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {remote_path} to {local_path} (attempt {attempt + 1}/{self.max_retries})")
                
                # Get remote file size for progress tracking
                remote_attrs = client.stat(remote_path)
                remote_size = remote_attrs.st_size
                
                # Download the file
                client.get(remote_path, local_path)
                
                # Verify download
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if local_size == remote_size:
                        logger.info(f"Successfully downloaded {remote_path} ({local_size} bytes)")
                        return True
                    else:
                        raise SFTPFileError(f"File size mismatch: remote={remote_size}, local={local_size}")
                else:
                    raise SFTPFileError("Local file was not created")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
                
                # Clean up partial download
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying download in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to download {remote_path} after {self.max_retries} attempts"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        logger.error(error_msg)
        raise SFTPFileError(error_msg)
    
    def upload_file(self, client: SFTPClient, local_path: str, remote_path: str) -> bool:
        """
        Upload a file to the remote server with retry logic.
        
        Args:
            client: Connected SFTP client
            local_path: Path to local file
            remote_path: Path to save remote file
            
        Returns:
            True if upload successful, False otherwise
            
        Raises:
            SFTPFileError: If upload fails after all retries
        """
        if not os.path.exists(local_path):
            raise SFTPFileError(f"Local file does not exist: {local_path}")
        
        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_path).replace('\\', '/')
        if remote_dir and remote_dir != '/':
            self._ensure_remote_directory(client, remote_dir)
        
        local_size = os.path.getsize(local_path)
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Uploading {local_path} to {remote_path} (attempt {attempt + 1}/{self.max_retries})")
                
                # Upload the file
                client.put(local_path, remote_path)
                
                # Verify upload
                try:
                    remote_attrs = client.stat(remote_path)
                    remote_size = remote_attrs.st_size
                    
                    if remote_size == local_size:
                        logger.info(f"Successfully uploaded {local_path} ({local_size} bytes)")
                        return True
                    else:
                        raise SFTPFileError(f"File size mismatch: local={local_size}, remote={remote_size}")
                        
                except FileNotFoundError:
                    raise SFTPFileError("Remote file was not created")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Upload attempt {attempt + 1} failed: {str(e)}")
                
                # Try to clean up failed upload
                try:
                    client.remove(remote_path)
                except Exception:
                    pass
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying upload in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to upload {local_path} after {self.max_retries} attempts"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        logger.error(error_msg)
        raise SFTPFileError(error_msg)
    
    def get_file_mtime(self, client: SFTPClient, remote_path: str) -> Optional[datetime]:
        """
        Get the modification time of a remote file.
        
        Args:
            client: Connected SFTP client
            remote_path: Path to remote file
            
        Returns:
            Modification time as datetime, or None if file doesn't exist
            
        Raises:
            SFTPFileError: If getting file attributes fails
        """
        try:
            attrs = client.stat(remote_path)
            return datetime.fromtimestamp(attrs.st_mtime)
        except FileNotFoundError:
            return None
        except Exception as e:
            error_msg = f"Failed to get modification time for {remote_path}: {str(e)}"
            logger.error(error_msg)
            raise SFTPFileError(error_msg)
    
    def file_exists(self, client: SFTPClient, remote_path: str) -> bool:
        """
        Check if a remote file exists.
        
        Args:
            client: Connected SFTP client
            remote_path: Path to remote file
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            client.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Error checking if file exists {remote_path}: {e}")
            return False
    
    def _ensure_remote_directory(self, client: SFTPClient, remote_dir: str):
        """
        Ensure remote directory exists, creating it if necessary.
        
        Args:
            client: Connected SFTP client
            remote_dir: Remote directory path
        """
        try:
            client.listdir(remote_dir)
        except FileNotFoundError:
            # Directory doesn't exist, try to create it
            try:
                # Create parent directories recursively
                parent_dir = os.path.dirname(remote_dir).replace('\\', '/')
                if parent_dir and parent_dir != '/' and parent_dir != remote_dir:
                    self._ensure_remote_directory(client, parent_dir)
                
                client.mkdir(remote_dir)
                logger.info(f"Created remote directory: {remote_dir}")
            except Exception as e:
                logger.warning(f"Could not create remote directory {remote_dir}: {e}")