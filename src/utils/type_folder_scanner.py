"""Type folder scanner for WebScribe workflow."""

import os
import logging
from typing import List, Dict, Tuple

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class TypeFolderScanner:
    """Scans and processes multiple type folders on FTPS server."""
    
    def __init__(self, type_folders: List[str]):
        """Initialize the type folder scanner.
        
        Args:
            type_folders: List of type folder names to scan (e.g., ['type3', 'type6', ...])
        """
        self.type_folders = type_folders
        logger.info(f"TypeFolderScanner initialized with {len(type_folders)} folders: {', '.join(type_folders)}")
    
    def scan_folders(self, ftps_client, base_path: str = "/") -> Dict[str, List]:
        """Scan all configured type folders and return files found in each.
        
        Args:
            ftps_client: Connected FTPS client (FTP_TLS instance)
            base_path: Base path where type folders are located
            
        Returns:
            Dict[str, List]: Dictionary mapping folder name to list of FileInfo objects
        """
        scan_results = {}
        total_files = 0
        
        logger.info(f"Starting scan of {len(self.type_folders)} type folders in {base_path}")
        
        for type_folder in self.type_folders:
            folder_path = f"{base_path}/{type_folder}".replace('//', '/')
            
            try:
                # Import here to avoid circular dependency
                from ftps.ftps_manager import FTPSManager
                
                # Create a temporary FTPSManager instance to use its list method
                ftps_manager = FTPSManager()
                files = ftps_manager.list_files_in_folder(ftps_client, folder_path)
                
                scan_results[type_folder] = files
                total_files += len(files)
                
                logger.info(f"✓ Scanned {type_folder}: found {len(files)} files")
                
            except Exception as e:
                logger.warning(f"✗ Failed to scan {type_folder}: {e}")
                scan_results[type_folder] = []
                
                handle_error(
                    error=e,
                    category=ErrorCategory.SFTP_FILE_OPERATION,
                    severity=ErrorSeverity.MEDIUM,
                    component="TypeFolderScanner",
                    operation="scan_folder",
                    additional_data={
                        "type_folder": type_folder,
                        "folder_path": folder_path,
                        "base_path": base_path
                    }
                )
        
        logger.info(f"Scan complete: {len(self.type_folders)} folders scanned, {total_files} total files found")
        return scan_results
    
    def get_all_files(self, scan_results: Dict[str, List]) -> List[Tuple[str, any]]:
        """Flatten scan results into a single list with type folder information.
        
        Args:
            scan_results: Dictionary from scan_folders() mapping folder name to file list
            
        Returns:
            List[Tuple[str, FileInfo]]: List of tuples (type_folder_name, file_info)
        """
        all_files = []
        
        for type_folder, files in scan_results.items():
            for file_info in files:
                all_files.append((type_folder, file_info))
        
        logger.debug(f"Flattened {len(all_files)} files from {len(scan_results)} type folders")
        return all_files
    
    def filter_document_files(self, files: List) -> List:
        """Filter for document files (.doc, .docx only).
        
        Args:
            files: List of FileInfo objects
            
        Returns:
            List: Filtered list containing only document files
        """
        document_extensions = {'.doc', '.docx'}
        filtered_files = []
        
        for file_info in files:
            filename = file_info.filename.lower()
            
            # Check if file has a document extension
            if any(filename.endswith(ext) for ext in document_extensions):
                filtered_files.append(file_info)
            else:
                logger.debug(f"Skipping non-document file: {file_info.filename}")
        
        logger.info(f"Filtered {len(filtered_files)} document files from {len(files)} total files")
        return filtered_files
    
    def get_scan_statistics(self, scan_results: Dict[str, List]) -> Dict[str, any]:
        """Generate statistics from scan results.
        
        Args:
            scan_results: Dictionary from scan_folders()
            
        Returns:
            Dict: Statistics including total files, files per folder, etc.
        """
        total_files = sum(len(files) for files in scan_results.values())
        folders_with_files = sum(1 for files in scan_results.values() if len(files) > 0)
        empty_folders = len(scan_results) - folders_with_files
        
        # Calculate total size
        total_size = 0
        for files in scan_results.values():
            for file_info in files:
                if hasattr(file_info, 'size'):
                    total_size += file_info.size
        
        # Find folder with most files
        max_files_folder = None
        max_files_count = 0
        for folder, files in scan_results.items():
            if len(files) > max_files_count:
                max_files_count = len(files)
                max_files_folder = folder
        
        statistics = {
            'total_folders_scanned': len(scan_results),
            'total_files_found': total_files,
            'folders_with_files': folders_with_files,
            'empty_folders': empty_folders,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'folder_with_most_files': max_files_folder,
            'max_files_in_folder': max_files_count,
            'files_per_folder': {folder: len(files) for folder, files in scan_results.items()}
        }
        
        logger.debug(f"Scan statistics: {total_files} files across {len(scan_results)} folders")
        return statistics
    
    def get_files_by_type(self, scan_results: Dict[str, List]) -> Dict[str, List]:
        """Group files by their extension type.
        
        Args:
            scan_results: Dictionary from scan_folders()
            
        Returns:
            Dict[str, List]: Dictionary mapping file extension to list of files
        """
        files_by_type = {}
        
        for type_folder, files in scan_results.items():
            for file_info in files:
                # Get file extension
                filename = file_info.filename.lower()
                ext = None
                
                if filename.endswith('.doc'):
                    ext = '.doc'
                elif filename.endswith('.docx'):
                    ext = '.docx'
                else:
                    ext = 'other'
                
                if ext not in files_by_type:
                    files_by_type[ext] = []
                
                files_by_type[ext].append((type_folder, file_info))
        
        # Log summary
        for ext, file_list in files_by_type.items():
            logger.debug(f"Found {len(file_list)} {ext} files")
        
        return files_by_type
    
    def validate_scan_results(self, scan_results: Dict[str, List]) -> bool:
        """Validate that scan results are complete and valid.
        
        Args:
            scan_results: Dictionary from scan_folders()
            
        Returns:
            bool: True if scan results are valid
        """
        # Check that all configured folders were scanned
        if len(scan_results) != len(self.type_folders):
            logger.warning(f"Scan incomplete: expected {len(self.type_folders)} folders, got {len(scan_results)}")
            return False
        
        # Check that all configured folders are in results
        for folder in self.type_folders:
            if folder not in scan_results:
                logger.warning(f"Missing scan results for folder: {folder}")
                return False
        
        logger.debug("Scan results validation passed")
        return True
