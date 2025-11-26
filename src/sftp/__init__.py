"""SFTP module for remote file operations."""

from .manager import SFTPManager, SFTPError, SFTPConnectionError, SFTPFileError, FileInfo

__all__ = ['SFTPManager', 'SFTPError', 'SFTPConnectionError', 'SFTPFileError', 'FileInfo']