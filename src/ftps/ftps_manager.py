"""FTPS Manager for handling WebScribe FTPS operations with TLS support."""

import os
import time
import logging
from ftplib import FTP_TLS, error_perm, error_temp
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import FTPSConfig
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class FTPSError(Exception):
    """Base exception for FTPS operations."""
    pass


class FTPSConnectionError(FTPSError):
    """Raised when FTPS connection fails."""
    pass


class FTPSFileError(FTPSError):
    """Raised when FTPS file operations fail."""
    pass


@dataclass
class FileInfo:
    """Information about a remote file."""
    filename: str
    full_path: str
    size: int
    mtime: datetime
    is_directory: bool = False


class FTPSManager:
    """Manages FTPS connections and file operations with TLS support and retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize FTPS manager.
        
        Args:
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._ftps_client = None
    
    @contextmanager
    def connect_ftps(self, config: FTPSConfig):
        """Context manager for FTPS connections with automatic cleanup.
        
        Args:
            config: FTPS configuration
            
        Yields:
            FTP_TLS: Connected FTPS client
            
        Raises:
            FTPSConnectionError: If connection fails after all retries
        """
        client = None
        try:
            client = self._establish_ftps_connection(config)
            yield client
        finally:
            if client:
                self._close_connection(client)
    
    def _establish_ftps_connection(self, config: FTPSConfig) -> FTP_TLS:
        """Establish FTPS connection with TLS and retry logic.
        
        Args:
            config: FTPS configuration
            
        Returns:
            FTP_TLS: Connected FTPS client
            
        Raises:
            FTPSConnectionError: If connection fails after all retries
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting FTPS connection to {config.host}:{config.port} (attempt {attempt + 1}/{self.max_retries})")
                
                # Create FTPS client with TLS support
                if config.use_tls:
                    ftps = FTP_TLS()
                    logger.debug("Using FTP_TLS for secure connection")
                else:
                    from ftplib import FTP
                    ftps = FTP()
                    logger.debug("Using plain FTP (TLS disabled)")
                
                # Set timeout
                ftps.timeout = 30
                
                # Connect to server
                ftps.connect(config.host, config.port)
                logger.debug(f"Connected to {config.host}:{config.port}")
                
                # Login
                ftps.login(config.username, config.password)
                logger.debug(f"Logged in as {config.username}")
                
                # Enable TLS for data connection if using TLS
                if config.use_tls:
                    ftps.prot_p()  # Set up secure data connection
                    logger.debug("Enabled TLS for data connection")
                
                # Set passive or active mode
                ftps.set_pasv(config.passive_mode)
                logger.debug(f"Set {'passive' if config.passive_mode else 'active'} mode")
                
                # Change to remote path if specified
                if config.remote_path and config.remote_path != '/':
                    try:
                        ftps.cwd(config.remote_path)
                        logger.debug(f"Changed to directory: {config.remote_path}")
                    except error_perm:
                        logger.warning(f"Remote path {config.remote_path} does not exist or is not accessible")
                
                logger.info(f"Successfully connected to FTPS server {config.host}:{config.port}")
                self._ftps_client = ftps
                return ftps
                
            except Exception as e:
                last_error = e
                
                # Determine error severity based on attempt number
                severity = ErrorSeverity.HIGH if attempt == self.max_retries - 1 else ErrorSeverity.MEDIUM
                
                # Handle the connection error
                handle_error(
                    error=e,
                    category=ErrorCategory.SFTP_CONNECTION,  # Using SFTP category for consistency
                    severity=severity,
                    component="FTPSManager",
                    operation="establish_ftps_connection",
                    additional_data={
                        "host": config.host,
                        "port": config.port,
                        "username": config.username,
                        "use_tls": config.use_tls,
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries
                    },
                    retry_count=attempt,
                    max_retries=self.max_retries - 1
                )
                
                # Clean up failed connection
                if self._ftps_client:
                    try:
                        self._ftps_client.quit()
                    except:
                        pass
                    self._ftps_client = None
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to connect to FTPS server {config.host}:{config.port} after {self.max_retries} attempts"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        logger.error(error_msg)
        raise FTPSConnectionError(error_msg)
    
    def _close_connection(self, client: FTP_TLS):
        """Close FTPS connection.
        
        Args:
            client: FTPS client to close
        """
        if client:
            try:
                client.quit()
                logger.debug("FTPS connection closed")
            except Exception as e:
                logger.warning(f"Error closing FTPS connection: {e}")
                try:
                    client.close()
                except:
                    pass
    
    def list_files_in_folder(self, client: FTP_TLS, folder_path: str) -> List[FileInfo]:
        """List all files directly in a folder (no subdirectories).
        
        Args:
            client: Connected FTPS client
            folder_path: Path to folder to list
            
        Returns:
            List[FileInfo]: List of files in the folder
            
        Raises:
            FTPSFileError: If listing fails
        """
        try:
            logger.debug(f"Listing files in folder: {folder_path}")
            
            # Change to the folder
            original_dir = client.pwd()
            
            try:
                if folder_path and folder_path != '.':
                    client.cwd(folder_path)
            except error_perm as e:
                logger.warning(f"Cannot access folder {folder_path}: {e}")
                return []
            
            files = []
            
            # List files using MLSD (modern listing) if available
            try:
                for name, facts in client.mlsd():
                    if name in ['.', '..']:
                        continue
                    
                    # Only include files, not directories
                    if facts.get('type') == 'file':
                        size = int(facts.get('size', 0))
                        
                        # Parse modification time
                        mtime_str = facts.get('modify')
                        if mtime_str:
                            try:
                                mtime = datetime.strptime(mtime_str, '%Y%m%d%H%M%S')
                            except:
                                mtime = datetime.now()
                        else:
                            mtime = datetime.now()
                        
                        full_path = f"{folder_path}/{name}".replace('//', '/')
                        
                        file_info = FileInfo(
                            filename=name,
                            full_path=full_path,
                            size=size,
                            mtime=mtime,
                            is_directory=False
                        )
                        files.append(file_info)
                        logger.debug(f"Found file: {name} ({size} bytes)")
                
            except Exception as mlsd_error:
                # Fallback to NLST if MLSD not supported
                logger.debug(f"MLSD not supported, falling back to NLST: {mlsd_error}")
                
                try:
                    file_list = client.nlst()
                    
                    for name in file_list:
                        if name in ['.', '..']:
                            continue
                        
                        try:
                            # Try to get file size
                            size = client.size(name)
                            if size is None:
                                # Might be a directory
                                continue
                            
                            full_path = f"{folder_path}/{name}".replace('//', '/')
                            
                            file_info = FileInfo(
                                filename=name,
                                full_path=full_path,
                                size=size,
                                mtime=datetime.now(),  # Can't get mtime with NLST
                                is_directory=False
                            )
                            files.append(file_info)
                            logger.debug(f"Found file: {name} ({size} bytes)")
                            
                        except:
                            # Skip if we can't get size (probably a directory)
                            continue
                    
                except Exception as nlst_error:
                    logger.error(f"Failed to list files with NLST: {nlst_error}")
                    raise
            
            # Return to original directory
            try:
                client.cwd(original_dir)
            except:
                pass
            
            logger.info(f"Found {len(files)} files in {folder_path}")
            return files
            
        except Exception as e:
            error_msg = f"Failed to list files in {folder_path}: {str(e)}"
            logger.error(error_msg)
            
            handle_error(
                error=e,
                category=ErrorCategory.SFTP_FILE_OPERATION,
                severity=ErrorSeverity.HIGH,
                component="FTPSManager",
                operation="list_files_in_folder",
                additional_data={"folder_path": folder_path}
            )
            
            raise FTPSFileError(error_msg)
    
    def download_file(self, client: FTP_TLS, remote_path: str, local_path: str) -> bool:
        """Download a file from FTPS server with retry logic.
        
        Args:
            client: Connected FTPS client
            remote_path: Path to remote file
            local_path: Path to save local file
            
        Returns:
            bool: True if download successful
            
        Raises:
            FTPSFileError: If download fails after all retries
        """
        # Ensure local directory exists
        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {remote_path} to {local_path} (attempt {attempt + 1}/{self.max_retries})")
                
                # Get remote file size
                try:
                    remote_size = client.size(remote_path)
                except:
                    remote_size = None
                
                # Download the file
                with open(local_path, 'wb') as local_file:
                    client.retrbinary(f'RETR {remote_path}', local_file.write)
                
                # Verify download
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    
                    if remote_size is not None and local_size != remote_size:
                        raise FTPSFileError(f"File size mismatch: remote={remote_size}, local={local_size}")
                    
                    logger.info(f"Successfully downloaded {remote_path} ({local_size} bytes)")
                    return True
                else:
                    raise FTPSFileError("Local file was not created")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
                
                # Clean up partial download
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except:
                        pass
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying download in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to download {remote_path} after {self.max_retries} attempts"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        logger.error(error_msg)
        raise FTPSFileError(error_msg)
    
    def scan_all_type_folders(self, client: FTP_TLS, type_folders: List[str], base_path: str = "/") -> dict:
        """Scan all type folders and return files found in each.
        
        Args:
            client: Connected FTPS client
            type_folders: List of type folder names to scan
            base_path: Base path where type folders are located
            
        Returns:
            dict: Dictionary mapping folder name to list of FileInfo objects
        """
        scan_results = {}
        
        for type_folder in type_folders:
            folder_path = f"{base_path}/{type_folder}".replace('//', '/')
            
            try:
                files = self.list_files_in_folder(client, folder_path)
                scan_results[type_folder] = files
                logger.info(f"Scanned {type_folder}: found {len(files)} files")
                
            except Exception as e:
                logger.warning(f"Failed to scan {type_folder}: {e}")
                scan_results[type_folder] = []
                
                handle_error(
                    error=e,
                    category=ErrorCategory.SFTP_FILE_OPERATION,
                    severity=ErrorSeverity.MEDIUM,
                    component="FTPSManager",
                    operation="scan_type_folder",
                    additional_data={
                        "type_folder": type_folder,
                        "folder_path": folder_path
                    }
                )
        
        total_files = sum(len(files) for files in scan_results.values())
        logger.info(f"Scanned {len(type_folders)} type folders, found {total_files} total files")
        
        return scan_results
