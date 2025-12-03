# WebScribe FTPS Workflow

An automated Python application that connects to WebScribe FTPS server, processes files from multiple type folders, and uploads results to WOLF SFTP server with comprehensive email notifications and error handling..

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Deployment Guide](#deployment-guide)
- [Troubleshooting](#troubleshooting)
- [Monitoring and Logs](#monitoring-and-logs)
- [Contributing](#contributing)

## Features

- **WebScribe FTPS Integration**: Connects to WebScribe FTPS server and scans multiple type folders
- **Date-Based Organization**: Creates date folders for organized file processing
- **Parallel Action Execution**: Processes files with configurable parallel actions
- **WOLF SFTP Upload**: Uploads processed files to WOLF SFTP server
- **Flexible Scheduling**: Supports both interval-based and cron-based scheduling
- **Email Notifications**: Sends detailed processing summaries with statistics
- **Error Handling**: Comprehensive error handling with detailed logging
- **Type Folder Configuration**: Configurable type folders to scan (type3, type6, type7, etc.)
- **Configurable Retention**: Flexible file retention policies for all file types
- **Secure Configuration**: All sensitive data managed through environment variables

## System Requirements

### Minimum Requirements

- **Python**: 3.7 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 512 MB RAM minimum, 1 GB recommended
- **Disk Space**: 1 GB free space for logs and temporary files
- **Network**: Stable internet connection for SFTP and email operations

### Python Dependencies

The application requires the following Python packages (automatically installed via requirements.txt):

- `paramiko==3.4.0` - SFTP client functionality
- `python-docx==1.1.0` - Microsoft Word document processing
- `python-dotenv==1.0.0` - Environment variable management
- `schedule==1.2.0` - Interval-based scheduling
- `croniter==2.0.1` - Cron expression parsing
- `docx2txt==0.9` - Additional .doc file support
- `pytz==2023.3` - Timezone handling

## Installation

### 1. Clone or Download the Project

```bash
git clone <repository-url>
cd webscribe-ftps-workflow
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example configuration file
cp .env.example .env

# Edit .env with your actual configuration values
# Use your preferred text editor
nano .env  # or vim .env, code .env, etc.
```

### 5. Verify Installation

```bash
# Test the installation
python src/main.py --help
```

## Configuration

All configuration is managed through environment variables. The application will look for a `.env` file in the project root or use system environment variables.

### Required Environment Variables

#### Source SFTP Server Configuration
```bash
SOURCE_SFTP_HOST=source.example.com          # SFTP server hostname/IP
SOURCE_SFTP_USERNAME=source_user             # SFTP username
SOURCE_SFTP_PASSWORD=source_password         # SFTP password
```

#### Destination SFTP Server Configuration
```bash
DEST_SFTP_HOST=dest.example.com              # Destination SFTP hostname/IP
DEST_SFTP_USERNAME=dest_user                 # Destination SFTP username
DEST_SFTP_PASSWORD=dest_password             # Destination SFTP password
```

#### Email Configuration
```bash
SMTP_HOST=smtp.example.com                   # SMTP server hostname
SMTP_USERNAME=notify@example.com             # SMTP username/email
SMTP_PASSWORD=smtp_password                  # SMTP password
ADMIN_EMAIL=admin@example.com                # Email address for notifications
```

### Optional Environment Variables

#### SFTP Configuration
```bash
SOURCE_SFTP_PORT=22                          # Source SFTP port (default: 22)
SOURCE_SFTP_PATH=/incoming                   # Source SFTP directory path (default: /)
DEST_SFTP_PORT=22                            # Destination SFTP port (default: 22)
DEST_SFTP_PATH=/processed                    # Destination SFTP directory path (default: /)
```

#### Email Configuration
```bash
SMTP_PORT=587                                # SMTP port (default: 587)
```

#### Scheduling Configuration
```bash
POLL_INTERVAL_SECONDS=60                     # Polling interval in seconds (default: 60)
POLL_CRON=0 2 * * *                         # Cron expression (overrides interval if set)
TZ=America/New_York                          # Timezone for cron scheduling (default: UTC)
```

#### Storage Configuration
```bash
LOCAL_STORAGE_PATH=/app/data                 # Local storage directory (default: ./data)
TEMP_PATH=/app/temp                          # Temporary files directory (default: ./temp)
ZIP_BACKUP_PATH=/app/data/AutogenJobID/zipfile-backups  # ZIP backup directory
```

### Configuration Priority

1. System environment variables (highest priority)
2. `.env` file in project root
3. Default values (lowest priority)

## Usage

### Starting the Application

```bash
# Start with default configuration
python src/main.py

# Start with custom environment file
ENV_FILE=/path/to/custom.env python src/main.py
```

### Scheduling Modes

#### Interval-Based Scheduling (Default)
The application will check for new files every `POLL_INTERVAL_SECONDS` seconds.

```bash
# Check every 60 seconds (default)
POLL_INTERVAL_SECONDS=60

# Check every 5 minutes
POLL_INTERVAL_SECONDS=300
```

#### Cron-Based Scheduling
Use cron expressions for more precise scheduling. When `POLL_CRON` is set, it overrides interval-based scheduling.

```bash
# Run every day at 2:00 AM
POLL_CRON="0 2 * * *"

# Run every hour at minute 0
POLL_CRON="0 * * * *"

# Run every 30 minutes
POLL_CRON="*/30 * * * *"
```

### Stopping the Application

- **Graceful shutdown**: Press `Ctrl+C` or send `SIGTERM` signal
- **Force stop**: Press `Ctrl+C` twice or send `SIGKILL` signal

## Project Structure

```
webscribe-ftps-workflow/
├── src/                                     # Source code
│   ├── main.py                             # Application entry point
│   ├── config/                             # Configuration management
│   │   ├── __init__.py
│   │   ├── models.py                       # Configuration data models
│   │   └── settings.py                     # Configuration manager
│   ├── controller/                         # Main processing controller
│   │   ├── __init__.py
│   │   └── main_controller.py
│   ├── sftp/                              # SFTP operations
│   │   ├── __init__.py
│   │   └── manager.py
│   ├── parser/                            # Document parsing
│   │   ├── __init__.py
│   │   └── document_parser.py
│   ├── scheduler/                         # Job scheduling
│   │   ├── __init__.py
│   │   └── job_scheduler.py
│   ├── email_notifier/                    # Email notifications
│   │   ├── __init__.py
│   │   └── notifier.py
│   └── utils/                             # Utility modules
│       ├── __init__.py
│       ├── csv_generator.py
│       ├── error_handler.py
│       ├── file_tracker.py
│       └── logging_config.py
├── tests/                                  # Test files
│   ├── __init__.py
│   ├── test_csv_generator.py
│   ├── test_document_parser.py
│   ├── test_email_notifier.py
│   ├── test_file_tracker.py
│   ├── test_integration.py
│   ├── test_integration_simple.py
│   ├── test_scheduler.py
│   └── test_sftp_manager.py
├── data/                                   # Runtime data (created automatically)
│   ├── logs/                              # Application logs
│   └── csv_files/                         # Processed CSV files
├── requirements.txt                        # Python dependencies
├── .env.example                           # Example environment configuration
├── .env                                   # Your environment configuration (create this)
└── README.md                              # This file
```

## Deployment Guide

### Production Deployment

#### 1. Server Setup

**Minimum Server Specifications:**
- CPU: 1 core (2 cores recommended)
- RAM: 1 GB (2 GB recommended)
- Storage: 10 GB free space
- Network: Stable internet connection

**Supported Operating Systems:**
- Ubuntu 18.04+ / Debian 9+
- CentOS 7+ / RHEL 7+
- Amazon Linux 2
- Windows Server 2016+

#### 2. System Dependencies

**Linux (Ubuntu/Debian):**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.7+
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies
sudo apt install build-essential libssl-dev libffi-dev -y
```

**Linux (CentOS/RHEL):**
```bash
# Update system packages
sudo yum update -y

# Install Python 3.7+
sudo yum install python3 python3-pip -y

# Install development tools
sudo yum groupinstall "Development Tools" -y
sudo yum install openssl-devel libffi-devel -y
```

**Windows:**
- Install Python 3.7+ from python.org
- Install Microsoft Visual C++ Build Tools

#### 3. Application Deployment

```bash
# Create application directory
sudo mkdir -p /opt/webscribe-ftps-workflow
cd /opt/webscribe-ftps-workflow

# Copy application files
# (Upload your project files here)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.example .env
# Edit .env with production values

# Create data directories
mkdir -p data/logs data/csv_files temp

# Set permissions
sudo chown -R $(whoami):$(whoami) /opt/webscribe-ftps-workflow
chmod +x src/main.py
```

#### 4. Service Configuration (Linux)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/webscribe-ftps-workflow.service
```

Service file content:
```ini
[Unit]
Description=Medical Document Processing System
After=network.target

[Service]
Type=simple
User=medproc
Group=medproc
WorkingDirectory=/opt/webscribe-ftps-workflow
Environment=PATH=/opt/webscribe-ftps-workflow/venv/bin
ExecStart=/opt/webscribe-ftps-workflow/venv/bin/python src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
# Create service user
sudo useradd -r -s /bin/false medproc
sudo chown -R medproc:medproc /opt/webscribe-ftps-workflow

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable webscribe-ftps-workflow
sudo systemctl start webscribe-ftps-workflow

# Check status
sudo systemctl status webscribe-ftps-workflow
```

#### 5. Docker Deployment (Optional)

Create a Dockerfile:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .env.example .env

# Create data directories
RUN mkdir -p data/logs data/csv_files temp

# Run as non-root user
RUN useradd -r -u 1001 medproc && chown -R medproc:medproc /app
USER medproc

EXPOSE 8080
CMD ["python", "src/main.py"]
```

Build and run:
```bash
# Build image
docker build -t webscribe-ftps-workflow .

# Run container
docker run -d \
  --name webscribe-workflow \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  webscribe-ftps-workflow
```

### Environment-Specific Configurations

#### Development Environment
```bash
# Use shorter polling intervals for testing
POLL_INTERVAL_SECONDS=30

# Use local storage paths
LOCAL_STORAGE_PATH=./data
TEMP_PATH=./temp

# Enable debug logging
LOG_LEVEL=DEBUG
```

#### Staging Environment
```bash
# Use production-like intervals
POLL_INTERVAL_SECONDS=300

# Use staging SFTP servers
SOURCE_SFTP_HOST=staging-source.example.com
DEST_SFTP_HOST=staging-dest.example.com

# Send notifications to staging email
ADMIN_EMAIL=staging-admin@example.com
```

#### Production Environment
```bash
# Use production intervals
POLL_INTERVAL_SECONDS=60
# Or use cron for specific times
POLL_CRON="0 */2 * * *"  # Every 2 hours

# Use production SFTP servers
SOURCE_SFTP_HOST=prod-source.example.com
DEST_SFTP_HOST=prod-dest.example.com

# Production email settings
ADMIN_EMAIL=admin@example.com
SMTP_HOST=smtp.company.com
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Application Won't Start

**Error: "Configuration error: Missing required environment variable"**

*Solution:*
```bash
# Check if .env file exists
ls -la .env

# Verify all required variables are set
cat .env | grep -E "(SFTP_HOST|SFTP_USERNAME|SFTP_PASSWORD|SMTP_HOST|ADMIN_EMAIL)"

# Copy from example if missing
cp .env.example .env
```

**Error: "Python 3.7 or higher is required"**

*Solution:*
```bash
# Check Python version
python --version
python3 --version

# Install Python 3.7+ if needed
# Ubuntu/Debian:
sudo apt install python3.8 python3.8-pip
# Use python3.8 instead of python3
```

**Error: "Missing required packages"**

*Solution:*
```bash
# Reinstall dependencies
pip install -r requirements.txt

# If using virtual environment, activate it first
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. SFTP Connection Issues

**Error: "Authentication failed" or "Connection refused"**

*Solution:*
```bash
# Test SFTP connection manually
sftp username@hostname

# Check firewall settings
telnet hostname 22

# Verify credentials in .env file
grep SFTP .env
```

**Error: "No route to host" or "Connection timeout"**

*Solution:*
```bash
# Test network connectivity
ping hostname

# Check if SFTP port is accessible
nc -zv hostname 22

# Verify VPN connection if required
```

#### 3. Email Notification Issues

**Error: "SMTP authentication failed"**

*Solution:*
```bash
# Test SMTP connection
telnet smtp.example.com 587

# Check email credentials
grep SMTP .env

# For Gmail, enable "App Passwords"
# For Office 365, check authentication method
```

**Error: "Email sending failed"**

*Solution:*
```bash
# Check SMTP port and security settings
# Port 587: STARTTLS
# Port 465: SSL/TLS
# Port 25: Unencrypted (not recommended)

# Update SMTP_PORT in .env if needed
```

#### 4. Document Processing Issues

**Error: "Failed to extract text from document"**

*Solution:*
```bash
# Check if document is corrupted
file /path/to/document.docx

# Verify document format
# Supported: .doc, .docx
# Not supported: .pdf, .txt, .rtf

# Check file permissions
ls -la /path/to/document.docx
```

**Error: "No medical fields found in document"**

*Solution:*
- Verify document contains expected medical data fields
- Check if document format matches expected structure
- Review parsing patterns in `src/parser/document_parser.py`

#### 5. Storage and Permission Issues

**Error: "Permission denied" when creating directories**

*Solution:*
```bash
# Check current user permissions
whoami
ls -la

# Create directories with proper permissions
mkdir -p data/logs data/csv_files temp
chmod 755 data data/logs data/csv_files temp

# For production, ensure service user has permissions
sudo chown -R medproc:medproc /opt/webscribe-ftps-workflow
```

**Error: "Disk space full"**

*Solution:*
```bash
# Check disk usage
df -h

# Clean up old log files
find data/logs -name "*.log" -mtime +30 -delete

# Clean up old CSV files (older than 60 days)
find data/csv_files -name "*.csv" -mtime +60 -delete
```

#### 6. Scheduling Issues

**Error: "Invalid cron expression"**

*Solution:*
```bash
# Validate cron expression format
# Format: "minute hour day month weekday"
# Example: "0 2 * * *" (daily at 2 AM)

# Test cron expression online: crontab.guru
# Update POLL_CRON in .env file
```

**Error: "Timezone issues with cron scheduling"**

*Solution:*
```bash
# Set timezone in .env
TZ=America/New_York

# Check available timezones
python -c "import pytz; print(pytz.all_timezones)"

# Use UTC for consistency across environments
TZ=UTC
```

### Debugging Steps

#### 1. Enable Debug Logging

Add to your `.env` file:
```bash
LOG_LEVEL=DEBUG
```

#### 2. Check Log Files

```bash
# View recent logs
tail -f data/logs/webscribe_processor.log

# Search for errors
grep -i error data/logs/webscribe_processor.log

# View specific component logs
grep "SFTPManager" data/logs/webscribe_processor.log
```

#### 3. Test Individual Components

```bash
# Test SFTP connection
python -c "
from src.sftp.manager import SFTPManager
from src.config.settings import ConfigManager
config = ConfigManager()
sftp_config = config.get_source_sftp_config()
manager = SFTPManager()
client = manager.connect(sftp_config)
print('SFTP connection successful')
"

# Test email configuration
python -c "
from src.email_notifier.notifier import EmailNotifier
from src.config.settings import ConfigManager
config = ConfigManager()
notifier = EmailNotifier(config)
notifier.send_test_email()
print('Email test successful')
"
```

#### 4. Monitor System Resources

```bash
# Check memory usage
free -h

# Check CPU usage
top -p $(pgrep -f "python.*main.py")

# Check disk I/O
iostat -x 1

# Check network connections
netstat -an | grep :22  # SFTP connections
netstat -an | grep :587 # SMTP connections
```

### Getting Help

#### Log Analysis

When reporting issues, include:

1. **Error messages** from logs
2. **Configuration** (sanitized, no passwords)
3. **System information** (OS, Python version)
4. **Steps to reproduce** the issue

#### Useful Commands for Support

```bash
# Generate system information
echo "=== System Information ===" > debug_info.txt
uname -a >> debug_info.txt
python --version >> debug_info.txt
pip list >> debug_info.txt

echo "=== Configuration ===" >> debug_info.txt
env | grep -E "(SFTP|SMTP)" | sed 's/PASSWORD=.*/PASSWORD=***/' >> debug_info.txt

echo "=== Recent Logs ===" >> debug_info.txt
tail -100 data/logs/webscribe_processor.log >> debug_info.txt

echo "=== Disk Usage ===" >> debug_info.txt
df -h >> debug_info.txt
```

## Monitoring and Logs

### Log Files

The application creates several log files in the `data/logs/` directory:

- `webscribe_processor.log` - Main application log
- `error_context/` - Detailed error context files
- `sftp_operations.log` - SFTP-specific operations
- `email_notifications.log` - Email notification history

### Log Rotation

Logs are automatically rotated to prevent disk space issues:
- Daily rotation for main logs
- 30-day retention for log files
- Automatic cleanup of old error context files

### Monitoring Metrics

Key metrics to monitor:

- **Processing Success Rate**: Percentage of successfully processed documents
- **SFTP Connection Health**: Connection success/failure rates
- **Email Delivery**: Notification delivery success rates
- **Processing Time**: Average time per document/batch
- **Error Frequency**: Number of errors per hour/day

### Health Checks

Create monitoring scripts to check system health:

```bash
#!/bin/bash
# health_check.sh

# Check if process is running
if pgrep -f "python.*main.py" > /dev/null; then
    echo "✓ Application is running"
else
    echo "✗ Application is not running"
    exit 1
fi

# Check recent log activity
if find data/logs -name "*.log" -mmin -10 | grep -q .; then
    echo "✓ Recent log activity detected"
else
    echo "⚠ No recent log activity"
fi

# Check disk space
DISK_USAGE=$(df data | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 90 ]; then
    echo "✓ Disk usage: ${DISK_USAGE}%"
else
    echo "✗ Disk usage critical: ${DISK_USAGE}%"
    exit 1
fi

echo "Health check completed successfully"
```

## Contributing

### Development Setup

1. Fork the repository
2. Create a virtual environment
3. Install development dependencies
4. Run tests before making changes

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Run tests
python -m pytest tests/

# Run code formatting
black src/ tests/

# Run linting
flake8 src/ tests/
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings for all public functions
- Write unit tests for new functionality

### Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_document_parser.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

For additional support or questions, please check the troubleshooting section above or contact the development team.
