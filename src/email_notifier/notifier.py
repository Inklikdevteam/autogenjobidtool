"""Email notification system for the medical document processing system."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.models import EmailConfig, ProcessingResult
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity


class EmailNotificationError(Exception):
    """Raised when email notification fails."""
    pass


class EmailNotifier:
    """Handles email notifications for processing results and failures."""
    
    def __init__(self, config: EmailConfig):
        """Initialize the email notifier with configuration.
        
        Args:
            config: Email configuration containing SMTP settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_success_summary(self, results: List[ProcessingResult]) -> bool:
        """Send a success summary email with processing statistics.
        
        Args:
            results: List of processing results to summarize
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not results:
            self.logger.warning("No processing results to send in summary email")
            return False
        
        try:
            subject = f"Medical Document Processing Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            body = self._generate_success_summary_body(results)
            
            # Send to multiple emails if configured, otherwise use single admin email
            recipients = self.config.admin_emails if self.config.admin_emails else [self.config.admin_email]
            
            return self._send_email_to_multiple(
                to_emails=recipients,
                subject=subject,
                body=body,
                is_html=True
            )
        except Exception as e:
            self.logger.error(f"Failed to send success summary email: {e}")
            return False
    
    def send_failure_notification(self, zip_filename: str, error_message: str, 
                                document_name: Optional[str] = None) -> bool:
        """Send immediate failure notification email.
        
        Args:
            zip_filename: Name of the ZIP file being processed
            error_message: Description of the error that occurred
            document_name: Optional name of specific document that failed
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            subject = f"URGENT: Medical Document Processing Failure - {zip_filename}"
            body = self._generate_failure_notification_body(
                zip_filename, error_message, document_name
            )
            
            # Send to multiple emails if configured, otherwise use single admin email
            recipients = self.config.admin_emails if self.config.admin_emails else [self.config.admin_email]
            
            return self._send_email_to_multiple(
                to_emails=recipients,
                subject=subject,
                body=body,
                is_html=True
            )
        except Exception as e:
            self.logger.error(f"Failed to send failure notification email: {e}")
            return False
    
    def _generate_success_summary_body(self, results: List[ProcessingResult]) -> str:
        """Generate HTML body for success summary email.
        
        Args:
            results: List of processing results to summarize
            
        Returns:
            str: HTML formatted email body
        """
        total_files = len(results)
        total_documents = sum(r.total_documents for r in results)
        total_successful = sum(r.successful_extractions for r in results)
        total_failed = sum(r.failed_extractions for r in results)
        total_time = sum(r.processing_time for r in results)
        
        html_body = f"""
        <html>
        <head></head>
        <body>
            <h2>Medical Document Processing Summary</h2>
            <p><strong>Processing completed at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>Overall Statistics</h3>
            <ul>
                <li><strong>ZIP files processed:</strong> {total_files}</li>
                <li><strong>Total documents:</strong> {total_documents}</li>
                <li><strong>Successful extractions:</strong> {total_successful}</li>
                <li><strong>Failed extractions:</strong> {total_failed}</li>
                <li><strong>Success rate:</strong> {(total_successful / total_documents * 100):.1f}% ({total_successful}/{total_documents})</li>
                <li><strong>Total processing time:</strong> {total_time:.2f} seconds</li>
            </ul>
            
            <h3>File Details</h3>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <tr style="background-color: #f0f0f0;">
                    <th>ZIP File</th>
                    <th>Documents</th>
                    <th>Successful</th>
                    <th>Failed</th>
                    <th>CSV Output</th>
                    <th>Processing Time</th>
                </tr>
        """
        
        for result in results:
            success_rate = (result.successful_extractions / result.total_documents * 100) if result.total_documents > 0 else 0
            row_color = "#ffeeee" if result.failed_extractions > 0 else "#eeffee"
            
            html_body += f"""
                <tr style="background-color: {row_color};">
                    <td>{result.zip_filename}</td>
                    <td>{result.total_documents}</td>
                    <td>{result.successful_extractions}</td>
                    <td>{result.failed_extractions}</td>
                    <td>{result.csv_filename}</td>
                    <td>{result.processing_time:.2f}s</td>
                </tr>
            """
        
        html_body += """
            </table>
        """
        
        # Add error details if any
        errors_found = [r for r in results if r.errors]
        if errors_found:
            html_body += """
            <h3>Error Details</h3>
            """
            for result in errors_found:
                if result.errors:
                    html_body += f"""
                    <h4>{result.zip_filename}</h4>
                    <ul>
                    """
                    for error in result.errors:
                        html_body += f"<li>{error}</li>"
                    html_body += "</ul>"
        
        html_body += """
        </body>
        </html>
        """
        
        return html_body
    
    def _generate_failure_notification_body(self, zip_filename: str, 
                                          error_message: str, 
                                          document_name: Optional[str] = None) -> str:
        """Generate HTML body for failure notification email.
        
        Args:
            zip_filename: Name of the ZIP file being processed
            error_message: Description of the error that occurred
            document_name: Optional name of specific document that failed
            
        Returns:
            str: HTML formatted email body
        """
        html_body = f"""
        <html>
        <head></head>
        <body>
            <h2 style="color: red;">URGENT: Medical Document Processing Failure</h2>
            <p><strong>Failure occurred at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>Failure Details</h3>
            <ul>
                <li><strong>ZIP File:</strong> {zip_filename}</li>
        """
        
        if document_name:
            html_body += f"<li><strong>Document:</strong> {document_name}</li>"
        
        html_body += f"""
                <li><strong>Error:</strong> {error_message}</li>
            </ul>
            
            <h3>Recommended Actions</h3>
            <ul>
                <li>Check the source ZIP file for corruption or invalid format</li>
                <li>Verify document contents and structure</li>
                <li>Review system logs for additional error details</li>
                <li>Ensure SFTP connections are stable</li>
            </ul>
            
            <p><em>This is an automated notification from the Medical Document Processing System.</em></p>
        </body>
        </html>
        """
        
        return html_body
    
    def _send_email(self, to_email: str, subject: str, body: str, 
                   is_html: bool = False, max_retries: int = 3) -> bool:
        """Send an email with retry logic.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            is_html: Whether the body is HTML formatted
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Create message
                msg = MIMEMultipart('alternative')
                msg['From'] = self.config.smtp_from if self.config.smtp_from else self.config.smtp_username
                msg['To'] = to_email
                msg['Subject'] = subject
                
                # Add body
                if is_html:
                    msg.attach(MIMEText(body, 'html'))
                else:
                    msg.attach(MIMEText(body, 'plain'))
                
                # Connect to SMTP server and send
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.starttls()  # Enable TLS encryption
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    # Use sendmail with explicit from address for AWS SES compatibility
                    from_addr = self.config.smtp_from if self.config.smtp_from else self.config.smtp_username
                    self.logger.debug(f"Sending email from: {from_addr} to: {to_email}")
                    server.sendmail(from_addr, [to_email], msg.as_string())
                
                self.logger.info(f"Email sent successfully to {to_email} (attempt {attempt + 1})")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                self.logger.error(f"SMTP authentication failed: {e}")
                handle_error(
                    error=e,
                    category=ErrorCategory.EMAIL_NOTIFICATION,
                    severity=ErrorSeverity.HIGH,
                    component="EmailNotifier",
                    operation="send_email",
                    additional_data={
                        "smtp_host": self.config.smtp_host,
                        "smtp_username": self.config.smtp_username,
                        "to_email": to_email,
                        "subject": subject
                    }
                )
                # Don't retry authentication errors
                break
                
            except smtplib.SMTPRecipientsRefused as e:
                self.logger.error(f"SMTP recipients refused: {e}")
                handle_error(
                    error=e,
                    category=ErrorCategory.EMAIL_NOTIFICATION,
                    severity=ErrorSeverity.HIGH,
                    component="EmailNotifier",
                    operation="send_email",
                    additional_data={
                        "to_email": to_email,
                        "subject": subject
                    }
                )
                # Don't retry recipient errors
                break
                
            except (smtplib.SMTPException, ConnectionError, OSError) as e:
                severity = ErrorSeverity.HIGH if attempt == max_retries - 1 else ErrorSeverity.MEDIUM
                
                handle_error(
                    error=e,
                    category=ErrorCategory.EMAIL_NOTIFICATION,
                    severity=severity,
                    component="EmailNotifier",
                    operation="send_email",
                    additional_data={
                        "smtp_host": self.config.smtp_host,
                        "to_email": to_email,
                        "subject": subject,
                        "attempt": attempt + 1,
                        "max_retries": max_retries
                    },
                    retry_count=attempt,
                    max_retries=max_retries - 1
                )
                
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** attempt
                    self.logger.info(f"Retrying email send in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to send email after {max_retries} attempts")
            
            except Exception as e:
                self.logger.error(f"Unexpected error sending email: {e}")
                handle_error(
                    error=e,
                    category=ErrorCategory.EMAIL_NOTIFICATION,
                    severity=ErrorSeverity.HIGH,
                    component="EmailNotifier",
                    operation="send_email",
                    additional_data={
                        "to_email": to_email,
                        "subject": subject,
                        "attempt": attempt + 1
                    }
                )
                break
        
        return False
    
    def _send_email_to_multiple(self, to_emails: List[str], subject: str, body: str, 
                               is_html: bool = False, max_retries: int = 3) -> bool:
        """Send an email to multiple recipients with retry logic.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            is_html: Whether the body is HTML formatted
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if email was sent successfully to all recipients, False otherwise
        """
        if not to_emails:
            self.logger.warning("No email recipients provided")
            return False
        
        success_count = 0
        total_recipients = len(to_emails)
        
        for email in to_emails:
            try:
                if self._send_email(email, subject, body, is_html, max_retries):
                    success_count += 1
                    self.logger.info(f"Email sent successfully to {email}")
                else:
                    self.logger.error(f"Failed to send email to {email}")
            except Exception as e:
                self.logger.error(f"Error sending email to {email}: {e}")
        
        # Consider successful if at least one email was sent
        if success_count > 0:
            self.logger.info(f"Email sent to {success_count}/{total_recipients} recipients")
            return True
        else:
            self.logger.error(f"Failed to send email to all {total_recipients} recipients")
            return False
    
    def test_connection(self) -> bool:
        """Test SMTP connection and authentication.
        
        Returns:
            bool: True if connection test successful, False otherwise
        """
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            # Log configured email recipients
            recipients = self.config.admin_emails if self.config.admin_emails else [self.config.admin_email]
            self.logger.info(f"SMTP connection test successful. Configured recipients: {recipients}")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def send_webscribe_notification(self, stats) -> bool:
        """Send email notification for WebScribe workflow processing.
        
        Args:
            stats: ProcessingStats object with processing statistics
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            subject = f"WebScribe Processing Complete - {stats.date_folder}"
            
            # Build HTML email body
            html_body = self._build_webscribe_html_body(stats)
            
            # Send to multiple emails if configured, otherwise use single admin email
            recipients = self.config.admin_emails if self.config.admin_emails else [self.config.admin_email]
            
            # Send email
            return self._send_email_to_multiple(
                to_emails=recipients,
                subject=subject,
                body=html_body,
                is_html=True
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send WebScribe notification: {e}")
            handle_error(
                error=e,
                category=ErrorCategory.EMAIL_NOTIFICATION,
                severity=ErrorSeverity.MEDIUM,
                component="EmailNotifier",
                operation="send_webscribe_notification"
            )
            return False
    
    def _build_webscribe_html_body(self, stats) -> str:
        """Build HTML email body for WebScribe workflow.
        
        Args:
            stats: ProcessingStats object
            
        Returns:
            str: HTML formatted email body
        """
        # Calculate duration
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(stats.start_time)
            end_dt = datetime.fromisoformat(stats.end_time)
            duration = (end_dt - start_dt).total_seconds()
            duration_str = f"{duration:.2f} seconds ({duration/60:.2f} minutes)"
        except:
            duration_str = "N/A"
        
        # Calculate success rate
        successful_downloads = sum(1 for d in stats.files_downloaded if d.success)
        total_downloads = len(stats.files_downloaded)
        download_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
        
        # Build HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #4CAF50; }}
                .section-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #2c3e50; }}
                .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }}
                .stat-item {{ padding: 10px; background-color: white; border-radius: 3px; }}
                .stat-label {{ font-weight: bold; color: #555; }}
                .stat-value {{ color: #2c3e50; font-size: 16px; }}
                .table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .table th {{ background-color: #2c3e50; color: white; padding: 10px; text-align: left; }}
                .table td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .success {{ color: #4CAF50; font-weight: bold; }}
                .failed {{ color: #f44336; font-weight: bold; }}
                .warning {{ color: #ff9800; }}
                .footer {{ margin-top: 30px; padding: 15px; background-color: #f0f0f0; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>WebScribe Processing Complete</h1>
                    <p>Date Folder: {stats.date_folder}</p>
                </div>
                
                <div class="section">
                    <div class="section-title">📊 Processing Summary</div>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Start Time:</div>
                            <div class="stat-value">{stats.start_time}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">End Time:</div>
                            <div class="stat-value">{stats.end_time}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Duration:</div>
                            <div class="stat-value">{duration_str}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">CSV Generated:</div>
                            <div class="stat-value">{stats.csv_filename}</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">📁 Type Folder Scan Results</div>
                    <table class="table">
                        <tr>
                            <th>Type Folder</th>
                            <th>Files Found</th>
                        </tr>
        """
        
        # Add type folder rows
        for folder, count in sorted(stats.type_folders_scanned.items()):
            status_class = "success" if count > 0 else "warning"
            html += f"""
                        <tr>
                            <td>{folder}</td>
                            <td class="{status_class}">{count}</td>
                        </tr>
            """
        
        total_scanned = sum(stats.type_folders_scanned.values())
        html += f"""
                        <tr style="font-weight: bold; background-color: #f0f0f0;">
                            <td>Total</td>
                            <td>{total_scanned}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="section">
                    <div class="section-title">⬇️ Download Results</div>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Total Downloads:</div>
                            <div class="stat-value">{total_downloads}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Successful:</div>
                            <div class="stat-value success">{successful_downloads}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Failed:</div>
                            <div class="stat-value failed">{total_downloads - successful_downloads}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Success Rate:</div>
                            <div class="stat-value">{download_rate:.1f}%</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">📄 Document Processing</div>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Documents Processed:</div>
                            <div class="stat-value">{stats.documents_processed}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Records Extracted:</div>
                            <div class="stat-value success">{stats.records_extracted}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">CSV Size:</div>
                            <div class="stat-value">{stats.csv_size / 1024:.2f} KB</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Upload Status:</div>
                            <div class="stat-value {'success' if 'SUCCESS' in stats.upload_status else 'failed'}">{stats.upload_status}</div>
                        </div>
                    </div>
                </div>
        """
        
        # Add errors section if there are errors
        if stats.errors:
            html += f"""
                <div class="section">
                    <div class="section-title">⚠️ Errors and Warnings</div>
                    <ul>
            """
            for error in stats.errors[:10]:  # Limit to first 10 errors
                html += f"<li>{error}</li>"
            
            if len(stats.errors) > 10:
                html += f"<li><em>... and {len(stats.errors) - 10} more errors</em></li>"
            
            html += """
                    </ul>
                </div>
            """
        
        html += f"""
                <div class="footer">
                    <p>This is an automated notification from the Medical Document Processing System</p>
                    <p>Processing Log: {stats.log_filename if stats.log_filename else 'Not available'}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
