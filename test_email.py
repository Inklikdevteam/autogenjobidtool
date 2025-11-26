"""
Test script for AWS SES email configuration.
Run this to verify your email settings before running the main app.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Email configuration from .env
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USERNAME)
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

# Parse recipient emails
recipients = [email.strip() for email in ADMIN_EMAIL.split(',') if email.strip()]

print("=" * 60)
print("AWS SES Email Configuration Test")
print("=" * 60)
print(f"SMTP Host: {SMTP_HOST}")
print(f"SMTP Port: {SMTP_PORT}")
print(f"SMTP Username: {SMTP_USERNAME}")
print(f"SMTP From: {SMTP_FROM}")
print(f"Recipients: {', '.join(recipients)}")
print("=" * 60)

def test_email():
    """Test sending email via AWS SES."""
    
    # Create test message
    subject = "Test Email from WebScribe FTPS Workflow"
    body = """
    <html>
    <body>
        <h2>Email Configuration Test</h2>
        <p>This is a test email to verify your AWS SES configuration.</p>
        <p><strong>Configuration Details:</strong></p>
        <ul>
            <li>SMTP Host: {}</li>
            <li>SMTP Port: {}</li>
            <li>From Address: {}</li>
        </ul>
        <p>If you received this email, your AWS SES configuration is working correctly!</p>
    </body>
    </html>
    """.format(SMTP_HOST, SMTP_PORT, SMTP_FROM)
    
    print("\nAttempting to send test email...")
    print("-" * 60)
    
    for recipient in recipients:
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = SMTP_FROM
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Attach HTML body
            msg.attach(MIMEText(body, 'html'))
            
            print(f"\nSending to: {recipient}")
            print(f"From: {SMTP_FROM}")
            
            # Connect and send
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.set_debuglevel(1)  # Enable debug output
                print("\nConnecting to SMTP server...")
                server.starttls()
                print("Starting TLS...")
                
                print(f"Logging in with username: {SMTP_USERNAME}")
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                print("Login successful!")
                
                print(f"Sending email from {SMTP_FROM} to {recipient}...")
                server.sendmail(SMTP_FROM, [recipient], msg.as_string())
                
            print(f"✓ Email sent successfully to {recipient}")
            print("-" * 60)
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"✗ Authentication Error: {e}")
            print("Check your SMTP_USERNAME and SMTP_PASSWORD")
            return False
            
        except smtplib.SMTPSenderRefused as e:
            print(f"✗ Sender Refused Error: {e}")
            print(f"The FROM address '{SMTP_FROM}' is not verified in AWS SES")
            print("Please verify this email address in AWS SES Console:")
            print("https://console.aws.amazon.com/ses/")
            return False
            
        except smtplib.SMTPRecipientsRefused as e:
            print(f"✗ Recipients Refused Error: {e}")
            print("The recipient email is not verified (if in sandbox mode)")
            return False
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("✓ All test emails sent successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_email()
        if success:
            print("\n✓ Email configuration is working correctly!")
            print("You can now run the main application.")
        else:
            print("\n✗ Email configuration test failed.")
            print("Please fix the issues above before running the main app.")
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
