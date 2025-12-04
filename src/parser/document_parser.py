"""Document parsing and text extraction for medical documents."""

import os
import re
import zipfile
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

import docx2txt
from docx import Document

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import MedicalRecord
from utils.date_utils import normalize_date
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class DocumentParser:
    """Parser for extracting medical data from .doc and .docx files."""
    
    def __init__(self):
        """Initialize the document parser with field extraction patterns."""
        self.field_patterns = self._initialize_field_patterns()
    
    def _is_valid_document_file(self, file_path: str) -> bool:
        """
        Check if the file is a valid document file that can be processed.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file appears to be a valid document, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.warning(f"File is empty: {file_path}")
                return False
            
            # Check for minimum reasonable file size (1KB)
            if file_size < 1024:
                logger.warning(f"File is very small ({file_size} bytes), might be corrupted: {file_path}")
                return False
            
            # Check file extension
            file_extension = Path(file_path).suffix.lower()
            if file_extension not in ['.doc', '.docx']:
                logger.warning(f"Unsupported file extension: {file_extension}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking file validity for {file_path}: {e}")
            return False
    
    def _initialize_field_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for extracting medical fields based on map.csv mapping."""
        return {
            'first_name': [
                r'FIRST\s+NAME:\s*([A-Z][A-Z\s-]+?)(?:\n|$)',
                r'FIRST\s+NAME\s*:\s*([A-Z][A-Z\s-]+?)(?:\n|$)',
                r'first\s+name[:\s]+([^\n\r,]+)'
            ],
            'last_name': [
                r'LAST\s+NAME:\s*([A-Z][A-Z\s-]+?)(?:\n|$)',
                r'LAST\s+NAME\s*:\s*([A-Z][A-Z\s-]+?)(?:\n|$)',
                r'last\s+name[:\s]+([^\n\r,]+)'
            ],
            'date_of_birth': [
                r'Date\s+of\s+Birth:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DATE\s+OF\s+BIRTH:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s+of\s+Birth\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DOB:\s*(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'record_number': [
                r'Record\s+Number:\s*(\d+\.\d+\.\d+)',
                r'RECORD\s+NUMBER:\s*(\d+\.\d+\.\d+)',
                r'Record\s+Number\s*:\s*(\d+\.\d+\.\d+)',
                r'RecordNumber:\s*(\d+\.\d+\.\d+)',
                r'MRN:\s*(\d+\.\d+\.\d+)',
                # Also look for record numbers in filename patterns
                r'~(\d+\.\d+\.\d+)~'
            ],
            'case_number': [
                r'Case\s+Number:\s*(\d+)',
                r'CASE\s+NUMBER:\s*(\d+)',
                r'Case\s+Number\s*:\s*(\d+)',
                r'case\s+number[:\s]+(\d+)'
            ],
            'accident_date': [
                # D/Accident patterns
                r'D/Accident:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'D/Accident\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s+of\s+Accident:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Accident\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
                # D/Injury patterns (same as accident date)
                r'D/Injury:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'D/Injury\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s+of\s+Injury:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Injury\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'provider_first': [
                # Match PROVIDER FIRST/FRIST with periods and spaces in names (e.g., "MARK A.")
                r'PROVIDER\s+FIRST:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',
                r'PROVIDER\s+FRIST:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',  # Note: "FRIST" as per mapping
                r'PROVIDER\s+FIRST\s*:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',
                r'PROVIDER\s+FRIST\s*:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',
                # Case insensitive patterns
                r'Provider\s+First:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',
                r'Provider\s+Frist:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)'
            ],
            'provider_last': [
                r'PROVIDER\s+LAST:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',
                r'PROVIDER\s+LAST\s*:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)',
                r'Provider\s+Last:\s*([A-Z][A-Z\s.\-]+?)(?:\n|$)'
            ],
            'exam_date': [
                r'Date\s+of\s+Exam:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DATE\s+OF\s+EXAM:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Date\s+of\s+Exam\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Exam\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'exam_place': [
                # Only match when there's actual content on the same line as the label
                r'Place\s+of\s+Exam:\s*([A-Z][A-Za-z\s.\'-]+?)(?:\s*$)',
                r'PLACE\s+OF\s+EXAM:\s*([A-Z][A-Za-z\s.\'-]+?)(?:\s*$)',
                r'Place\s+of\s+Exam\s*:\s*([A-Z][A-Za-z\s.\'-]+?)(?:\s*$)',
                r'Exam\s+Place:\s*([A-Z][A-Za-z\s.\'-]+?)(?:\s*$)'
            ],
            'transcriptionist': [
                r'Transcriptionist:\s*([a-z]{2}/[a-z]{2})',
                r'TRANSCRIPTIONIST:\s*([a-z]{2}/[a-z]{2})',
                r'Transcriptionist\s*:\s*([a-z]{2}/[a-z]{2})',
                # Extract from DD/Transcription pattern
                r'([a-z]{2}/[a-z]{2})\s+DD:'
            ],
            'dd_date': [
                r'DD:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DD\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DD\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Dictation\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'transcription_date': [
                r'Transcription\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'TRANSCRIPTION\s+DATE:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Transcription\s+Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'transcribed\s+date[:\s]+(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'job_number': [
                # Extract from document content - most flexible patterns first
                r'Job\s*:\s*(\d{4}-\d{2,3})',
                r'JOB\s*:\s*(\d{4}-\d{2,3})',
                r'job\s*:\s*(\d{4}-\d{2,3})',
                # Without colon
                r'Job\s+(\d{4}-\d{2,3})',
                r'JOB\s+(\d{4}-\d{2,3})',
                # Extract from filename pattern like "U 1029-252"
                r'[A-Z]\s+(\d{4}-\d{2,3})\s+\d',
                # With optional letter prefix in content
                r'Job\s*:\s*[A-Z]\s*(\d{4}-\d{2,3})',
                r'JOB\s*:\s*[A-Z]\s*(\d{4}-\d{2,3})'
            ],
            'case_code': [
                # Extract case codes based on "Case" label - handles spaces between letters and numbers
                # Matches patterns like "AA061625", "AWC090924", "aa102425", "AA 061625" (with space)
                r'Case:\s*([A-Za-z]{2,3}\s*\d+)(?=\s|$)',
                r'CASE:\s*([A-Za-z]{2,3}\s*\d+)(?=\s|$)',
                r'case:\s*([A-Za-z]{2,3}\s*\d+)(?=\s|$)',
                r'Case\s*:\s*([A-Za-z]{2,3}\s*\d+)(?=\s|$)',
            ]
        }
    
    def extract_documents_from_zip(self, zip_path: str, extract_to: str) -> List[str]:
        """
        Extract .doc and .docx files from a ZIP archive.
        
        Args:
            zip_path: Path to the ZIP file
            extract_to: Directory to extract files to
            
        Returns:
            List of paths to extracted document files
            
        Raises:
            Exception: If ZIP file cannot be opened or extracted
        """
        extracted_files = []
        
        try:
            logger.debug(f"Opening ZIP file: {zip_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_contents = zip_ref.infolist()
                logger.debug(f"ZIP contains {len(zip_contents)} files")
                
                for file_info in zip_contents:
                    # Check if file is a document and not in a subdirectory we want to skip
                    if (file_info.filename.lower().endswith(('.doc', '.docx')) and 
                        not file_info.filename.startswith('__MACOSX/') and
                        not file_info.is_dir()):
                        
                        try:
                            # Extract the file
                            extracted_path = zip_ref.extract(file_info, extract_to)
                            extracted_files.append(extracted_path)
                            logger.debug(f"Extracted document: {file_info.filename} ({file_info.file_size} bytes)")
                        except Exception as extract_error:
                            logger.warning(f"Failed to extract {file_info.filename}: {extract_error}")
                            handle_error(
                                error=extract_error,
                                category=ErrorCategory.FILE_PROCESSING,
                                severity=ErrorSeverity.MEDIUM,
                                component="DocumentParser",
                                operation="extract_single_document",
                                additional_data={
                                    "zip_path": zip_path,
                                    "document_name": file_info.filename,
                                    "document_size": file_info.file_size
                                }
                            )
                            continue
                        
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file {zip_path}: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.HIGH,
                component="DocumentParser",
                operation="extract_documents_from_zip",
                additional_data={"zip_path": zip_path}
            )
            raise Exception(f"Invalid ZIP file: {e}")
        except Exception as e:
            logger.error(f"Error extracting ZIP file {zip_path}: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.HIGH,
                component="DocumentParser",
                operation="extract_documents_from_zip",
                additional_data={"zip_path": zip_path}
            )
            raise Exception(f"Error extracting ZIP file: {e}")
        
        logger.info(f"Successfully extracted {len(extracted_files)} documents from {zip_path}")
        return extracted_files
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from a .docx file.
        
        Args:
            file_path: Path to the .docx file
            
        Returns:
            Extracted text content
            
        Raises:
            Exception: If file cannot be read or processed
        """
        try:
            # Try using python-docx first for better formatting
            doc = Document(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            text = '\n'.join(text_parts)
            
            # If no text found with python-docx, try docx2txt as fallback
            if not text.strip():
                text = docx2txt.process(file_path)
            
            logger.debug(f"Extracted {len(text)} characters from {file_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            # Try docx2txt as fallback
            try:
                text = docx2txt.process(file_path)
                logger.info(f"Fallback extraction successful for {file_path}")
                return text
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed for {file_path}: {fallback_error}")
                raise Exception(f"Could not extract text from {file_path}: {e}")
    
    def extract_text_from_doc(self, file_path: str) -> str:
        """
        Extract text from a .doc file using docx2txt.
        
        Args:
            file_path: Path to the .doc file
            
        Returns:
            Extracted text content
            
        Raises:
            Exception: If file cannot be read or processed
        """
        try:
            text = docx2txt.process(file_path)
            logger.debug(f"Extracted {len(text)} characters from {file_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise Exception(f"Could not extract text from {file_path}: {e}")
    
    def _extract_with_docx2txt_universal(self, file_path: str) -> str:
        """
        Universal text extraction using docx2txt (works for both .doc and .docx).
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        try:
            text = docx2txt.process(file_path)
            logger.debug(f"Universal extraction: {len(text)} characters from {file_path}")
            return text if text else ""
        except Exception as e:
            logger.warning(f"Universal extraction failed for {file_path}: {e}")
            return ""
    
    def _extract_with_alternative_methods(self, file_path: str) -> str:
        """
        Try alternative extraction methods for problematic .doc files.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        # Method 1: Try to detect if it's actually HTML with .doc extension
        try:
            with open(file_path, 'rb') as f:
                first_1kb = f.read(1024)
            
            # Check if it's HTML content
            if b'<html' in first_1kb.lower() or b'<!doctype' in first_1kb.lower():
                logger.info(f"Detected HTML content in {file_path}, attempting HTML extraction")
                return self._extract_from_html_doc(file_path)
            
            # Check if it's RTF content
            if b'{\\rtf' in first_1kb:
                logger.info(f"Detected RTF content in {file_path}, attempting RTF extraction")
                return self._extract_from_rtf_doc(file_path)
                
        except Exception as e:
            logger.warning(f"Alternative format detection failed for {file_path}: {e}")
        
        # Method 2: Try reading as plain text with different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'utf-16']:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                
                # Look for readable text content
                if len(content) > 100 and any(c.isalpha() for c in content):
                    logger.info(f"Extracted text using {encoding} encoding from {file_path}")
                    return content
                    
            except Exception as e:
                continue
        
        logger.warning(f"All alternative extraction methods failed for {file_path}")
        return ""
    
    def _extract_from_html_doc(self, file_path: str) -> str:
        """Extract text from HTML content saved as .doc file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Simple HTML tag removal (basic approach)
            import re
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            # Decode HTML entities
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"HTML extraction failed for {file_path}: {e}")
            return ""
    
    def _extract_from_rtf_doc(self, file_path: str) -> str:
        """Extract text from RTF content saved as .doc file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
            
            # Simple RTF text extraction (basic approach)
            import re
            # Remove RTF control words
            text = re.sub(r'\\[a-z]+\d*\s?', ' ', rtf_content)
            # Remove braces
            text = re.sub(r'[{}]', ' ', text)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"RTF extraction failed for {file_path}: {e}")
            return ""
    
    def _extract_with_antiword(self, file_path: str) -> str:
        """
        Extract text using antiword library (specifically for old .doc files).
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        try:
            import subprocess
            import tempfile
            
            # Use antiword command line tool if available
            result = subprocess.run(['antiword', file_path], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30)
            
            if result.returncode == 0 and result.stdout:
                text = result.stdout.strip()
                logger.info(f"Antiword extracted {len(text)} characters from {file_path}")
                return text
            else:
                logger.warning(f"Antiword failed for {file_path}: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Antiword timeout for {file_path}")
            return ""
        except FileNotFoundError:
            logger.warning("Antiword command not found, trying Python antiword library")
            
            # Try Python antiword library as fallback
            try:
                import antiword
                text = antiword.extract(file_path)
                if text:
                    logger.info(f"Python antiword extracted {len(text)} characters from {file_path}")
                    return text
                else:
                    return ""
            except Exception as e:
                logger.warning(f"Python antiword failed for {file_path}: {e}")
                return ""
        except Exception as e:
            logger.warning(f"Antiword extraction failed for {file_path}: {e}")
            return ""
    
    def extract_text_from_document(self, file_path: str) -> str:
        """
        Extract text from a document file (.doc or .docx).
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
            
        Raises:
            Exception: If file cannot be read or processed
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension not in ['.doc', '.docx']:
            raise Exception(f"Unsupported file format: {file_extension}")
        
        # Use a multi-approach strategy to handle various document formats
        # This addresses the specific issue where .doc files are being processed incorrectly
        
        extraction_methods = []
        
        # For .doc files, try multiple approaches
        if file_extension == '.doc':
            extraction_methods = [
                ('docx2txt', self.extract_text_from_doc),
                ('antiword', self._extract_with_antiword),
                ('docx2txt_universal', self._extract_with_docx2txt_universal),
                ('alternative_methods', self._extract_with_alternative_methods)
            ]
        # For .docx files, try python-docx first, then docx2txt
        elif file_extension == '.docx':
            extraction_methods = [
                ('python-docx', self.extract_text_from_docx),
                ('docx2txt_fallback', self._extract_with_docx2txt_universal),
                ('alternative_methods', self._extract_with_alternative_methods)
            ]
        
        # Try each extraction method
        for method_name, method_func in extraction_methods:
            try:
                logger.debug(f"Trying {method_name} for {file_path}")
                text = method_func(file_path)
                if text and text.strip():
                    logger.info(f"Successfully extracted text using {method_name} for {os.path.basename(file_path)}")
                    return text
                else:
                    logger.warning(f"{method_name} returned empty text for {file_path}")
            except Exception as e:
                logger.warning(f"{method_name} failed for {file_path}: {e}")
                continue
        
        # If all methods failed, log and return empty string
        logger.error(f"All extraction methods failed for {file_path}")
        return ""
    
    def extract_field_value(self, text: str, field_name: str) -> str:
        """
        Extract a specific field value from text using regex patterns.
        
        Args:
            text: The text to search in
            field_name: The name of the field to extract
            
        Returns:
            Extracted field value or empty string if not found
        """
        if not text or field_name not in self.field_patterns:
            return ""
        
        patterns = self.field_patterns[field_name]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                
                # Clean up the extracted value
                value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                value = value.strip('.,;:')  # Remove trailing punctuation
                
                # Validate name fields to ensure they contain actual names
                if field_name in ['first_name', 'last_name', 'provider_first', 'provider_last']:
                    # Skip values that look like dates, codes, or other non-name data
                    if self._is_invalid_name(value):
                        continue
                
                # Special filtering for exam_place to exclude unwanted text
                if field_name == 'exam_place':
                    # Filter out common non-location text and document headers
                    unwanted_phrases = [
                        'INTERNAL USE ONLY',
                        'INTERNAL',
                        'USE ONLY',
                        'RADIOLOGY REPORT',
                        'DICTATED BUT NOT READ',
                        'SIGNED REPORT',
                        'PATIENT',
                        'CHIROPRACTIC MEDICAL EXAM',
                        'MEDICAL EXAM',
                        'PHYSICAL EXAM',
                        'EXAMINATION',
                        'REPORT',
                        'EVALUATION'
                    ]
                    
                    # Check if the extracted value is one of the unwanted phrases
                    if any(unwanted.lower() in value.lower() for unwanted in unwanted_phrases):
                        continue  # Skip this match and try next pattern
                    
                    # If the value is too short or empty, skip it
                    if len(value.strip()) < 3:
                        continue
                
                # For case_code field, remove spaces, convert to uppercase, and validate
                if field_name == 'case_code':
                    # Remove all spaces from case code (e.g., "AA 061625" becomes "AA061625")
                    value = value.replace(' ', '')
                    # Convert to uppercase (e.g., "aa102425" becomes "AA102425")
                    value = value.upper()
                    # Check if value contains only ASCII letters and digits (2-3 letters followed by digits)
                    if not value.isascii() or not re.match(r'^[A-Z]{2,3}\d+$', value):
                        continue  # Skip invalid case codes
                
                # For date fields, normalize the date format
                if field_name in ['date_of_birth', 'accident_date', 'exam_date', 'dd_date', 'transcription_date']:
                    normalized_date = normalize_date(value)
                    if normalized_date:
                        return normalized_date
                    # If date normalization fails, continue to next pattern
                    continue
                
                if value:
                    logger.debug(f"Extracted {field_name}: {value}")
                    return value
        
        return ""
    
    def _is_invalid_name(self, value: str) -> bool:
        """
        Check if a value is not a valid name (contains dates, codes, or other non-name data).
        
        Args:
            value: The extracted value to validate
            
        Returns:
            True if the value is not a valid name, False otherwise
        """
        if not value or len(value.strip()) < 2:
            return True
        
        # Check for date patterns (MM/DD/YYYY, DD/MM/YYYY, etc.)
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}-\d{1,2}-\d{4}',  # MM-DD-YYYY or DD-MM-YYYY
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        
        # Check for common non-name patterns
        invalid_patterns = [
            r'D/Accident',  # Specific pattern from the issue
            r'Date\s*of\s*',  # Date of something
            r'Record\s*Number',  # Record number
            r'Case\s*Number',  # Case number
            r'^\d+$',  # Only numbers
            r'[A-Z]{2}\d{6}',  # Case codes like WC032525
            r'\d{4}-\d{3}',  # Job numbers like 1028-032
            r'1\.\d+\.\d+',  # Record numbers like 1.221743.0
            r'^[a-z]{2}/[a-z]{2}$',  # Transcriptionist codes like ad/ag
            r'00/00/0000',  # Invalid dates
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        # Check if value contains mostly non-alphabetic characters
        alpha_chars = sum(1 for c in value if c.isalpha())
        total_chars = len(value.replace(' ', ''))  # Exclude spaces
        
        if total_chars > 0 and alpha_chars / total_chars < 0.5:
            return True
        
        return False
    
    def _extract_from_filename(self, filename: str) -> dict:
        """
        Extract data from the filename pattern based on map.csv requirements.
        
        Args:
            filename: The source filename
            
        Returns:
            Dictionary with extracted fields from filename
        """
        filename_data = {}
        
        # Extract job number from filename pattern like "N 1028-032 8167..."
        # Extract only the numeric part (1028-032), not the letter prefix
        job_match = re.search(r'[A-Z]\s+(\d{4}-\d{3})', filename)
        if job_match:
            # Extract only the numeric part without the letter prefix
            job_number = job_match.group(1)  # This captures just "1028-032"
            filename_data['job_number'] = job_number
        
        # Extract record number from filename pattern like "~1.221743.0~"
        record_match = re.search(r'~(1\.\d+\.\d+)~', filename)
        if record_match:
            filename_data['record_number'] = record_match.group(1)
        
        # Extract case code from filename (various patterns)
        # Look for patterns like WC032525, AA081925, etc.
        case_code_match = re.search(r'([A-Z]{2}\d{6})', filename)
        if case_code_match:
            filename_data['case_code'] = case_code_match.group(1)
        
        return filename_data
    

    def parse_medical_fields(self, text: str, source_file: str) -> MedicalRecord:
        """
        Parse medical fields from extracted text and filename.
        
        Args:
            text: The extracted text from the document
            source_file: The source filename for reference
            
        Returns:
            MedicalRecord object with extracted fields
        """
        if not text:
            logger.warning(f"No text provided for parsing from {source_file}")
            return MedicalRecord(source_file=source_file)

        # Check if filename contains "MERGED" - these files have paragraph format
        # and should only show source_file in CSV with all other fields blank
        if 'MERGED' in source_file.upper():
            logger.info(f"Detected MERGED document (paragraph format): {source_file}")
            return MedicalRecord(source_file=source_file)


        
        # Check if document is essentially blank or has "No dictation"
        # Remove whitespace and check content length
        text_stripped = text.strip()
        text_lower = text_stripped.lower()
        
        # Patterns that indicate a blank/empty document or addendum/reference document
        blank_indicators = [
            'no dictation',
            'no dictation.',
            'nodictation',
            'there is no dictation',
            'blank file',
            'blank',
            'this is a blank file',
            'note: this is a blank file',
            'dictation cancelled',
            'dictation cancelled.',
            'this is an addendum to file',
            'addendum to file',
            'addendum added to file',
            're-dictated in file',
            'redictated in file',
        ]
        # Check if document contains blank indicators
        is_blank_document = any(indicator in text_lower for indicator in blank_indicators)
        
        # Also check if document has very minimal content (less than 50 characters after stripping)
        # This catches documents that only have headers/logos but no actual medical content
        if len(text_stripped) < 50:
            is_blank_document = True
        
        # Log if document is blank or addendum (but still process it to include in CSV)
        if is_blank_document:
           logger.info(f"Detected blank/cancelled/addendum document (will still include in CSV): {source_file}")
        # Extract fields from text
        record = MedicalRecord(
            source_file=source_file,
            first_name=self.extract_field_value(text, 'first_name'),
            last_name=self.extract_field_value(text, 'last_name'),
            date_of_birth=self.extract_field_value(text, 'date_of_birth'),
            record_number=self.extract_field_value(text, 'record_number'),
            case_number=self.extract_field_value(text, 'case_number'),
            accident_date=self.extract_field_value(text, 'accident_date'),
            provider_first=self.extract_field_value(text, 'provider_first'),
            provider_last=self.extract_field_value(text, 'provider_last'),
            exam_date=self.extract_field_value(text, 'exam_date'),
            exam_place=self.extract_field_value(text, 'exam_place'),
            transcriptionist=self.extract_field_value(text, 'transcriptionist'),
            dd_date=self.extract_field_value(text, 'dd_date'),
            transcription_date=self.extract_field_value(text, 'transcription_date'),
            job_number=self.extract_field_value(text, 'job_number'),
            case_code=self.extract_field_value(text, 'case_code')
        )
        
        # Extract job_number from filename if not found in document content
        if not record.job_number:
            # Try to extract job number from filename pattern like "U 1029-343 9054..."
            import re
            job_match = re.search(r'[A-Z]\s+(\d{4}-\d{2,3})\s+\d', source_file)
            if job_match:
                record.job_number = job_match.group(1)
                logger.debug(f"Extracted job_number from filename: {record.job_number}")
        
        # Log extraction summary
        extracted_fields = [field for field, value in record.__dict__.items() 
                          if field != 'source_file' and value]
        logger.info(f"Extracted {len(extracted_fields)} fields from {source_file}: {extracted_fields}")
        
        return record
    
    def process_document(self, file_path: str) -> MedicalRecord:
        """
        Process a single document file and extract medical fields.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            MedicalRecord object with extracted data
            
        Raises:
            Exception: If document cannot be processed
        """
        source_filename = os.path.basename(file_path)
        
        try:
            logger.debug(f"Processing document: {source_filename}")
            
            # Extract text from the document
            text = self.extract_text_from_document(file_path)
            logger.debug(f"Extracted {len(text)} characters from {source_filename}")
            
            # Parse medical fields from the text
            record = self.parse_medical_fields(text, source_filename)
            
            # Count extracted fields for logging
            extracted_fields = [field for field, value in record.__dict__.items() 
                              if field != 'source_file' and value]
            
            logger.info(f"Successfully processed document: {source_filename} "
                       f"({len(extracted_fields)} fields extracted)")
            return record
            
        except Exception as e:
            logger.error(f"Failed to process document {file_path}: {e}")
            
            handle_error(
                error=e,
                category=ErrorCategory.DOCUMENT_PARSING,
                severity=ErrorSeverity.MEDIUM,
                component="DocumentParser",
                operation="process_document",
                additional_data={
                    "file_path": file_path,
                    "source_filename": source_filename,
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
            )
            
            raise Exception(f"Failed to process {source_filename}: {e}")
    
    def process_zip_file(self, zip_path: str, temp_dir: str) -> List[MedicalRecord]:
        """
        Process all documents in a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            temp_dir: Temporary directory for extraction
            
        Returns:
            List of MedicalRecord objects
            
        Raises:
            Exception: If ZIP file cannot be processed
        """
        records = []
        extracted_files = []
        
        try:
            # Extract documents from ZIP
            extracted_files = self.extract_documents_from_zip(zip_path, temp_dir)
            
            if not extracted_files:
                logger.warning(f"No .doc or .docx files found in {zip_path}")
                return records
            
            # Process each extracted document
            for file_path in extracted_files:
                try:
                    record = self.process_document(file_path)
                    records.append(record)
                except Exception as e:
                    logger.error(f"Failed to process document {file_path}: {e}")
                    # Continue processing other documents
                    continue
            
            logger.info(f"Processed {len(records)} documents from {zip_path}")
            return records
            
        except Exception as e:
            logger.error(f"Failed to process ZIP file {zip_path}: {e}")
            raise
        finally:
            # Clean up extracted files
            for file_path in extracted_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"Cleaned up temporary file: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up {file_path}: {cleanup_error}")