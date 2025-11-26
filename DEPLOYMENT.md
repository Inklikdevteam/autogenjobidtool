# WebScribe FTPS Workflow - Deployment Guide

## Overview

This guide provides detailed instructions for deploying the WebScribe FTPS Workflow System in various environments, from development to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Development Deployment](#development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security Considerations](#security-considerations)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 1 core, 2.0 GHz
- RAM: 512 MB available
- Storage: 1 GB free space
- Network: Stable internet connection

**Recommended Requirements:**
- CPU: 2 cores, 2.4 GHz or higher
- RAM: 2 GB available
- Storage: 10 GB free space
- Network: High-speed internet connection

### Software Requirements

- **Python**: 3.7 or higher (3.9+ recommended)
- **Operating System**: Linux (Ubuntu 18.04+), macOS (10.14+), or Windows (10+)
- **Network Access**: SFTP and SMTP connectivity
- **Permissions**: Ability to create directories and files

## Environment Setup

### 1. System Dependencies

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y build-essential libssl-dev libffi-dev
sudo apt install -y curl wget git

# Install system monitoring tools (optional)
sudo apt install -y htop iotop nethogs
```

#### CentOS/RHEL/Amazon Linux
```bash
# Update system
sudo yum update -y

# Install Python and development tools
sudo yum install -y python3 python3-pip python3-devel
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel libffi-devel

# For Amazon Linux 2
sudo amazon-linux-extras install python3.8
```

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.9

# Install development tools
xcode-select --install
```

#### Windows
1. Download Python 3.9+ from [python.org](https://python.org)
2. Install Microsoft Visual C++ Build Tools
3. Install Git for Windows
4. Use PowerShell or Command Prompt for commands

### 2. User and Directory Setup

#### Linux/macOS Production Setup
```bash
# Create application user
sudo useradd -r -m -s /bin/bash medproc
sudo usermod -aG sudo medproc  # Optional: for maintenance access

# Create application directory
sudo mkdir -p /opt/webscribe-ftps-workflow
sudo chown medproc:medproc /opt/webscribe-ftps-workflow

# Switch to application user
sudo su - medproc
cd /opt/webscribe-ftps-workflow
```

#### Windows Production Setup
```powershell
# Create application directory
New-Item -ItemType Directory -Path "C:\webscribe-ftps-workflow" -Force

# Set permissions (run as Administrator)
icacls "C:\webscribe-ftps-workflow" /grant "Users:(OI)(CI)F"
```

## Development Deployment

### Quick Start for Development

```bash
# Clone repository
git clone <repository-url>
cd webscribe-ftps-workflow

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp .env.example .env
# Edit .env with development settings

# Create data directories
mkdir -p data/logs data/csv_files temp

# Run application
python src/main.py
```

### Development Configuration

Create a development-specific `.env` file:

```bash
# Development SFTP (use test servers)
SOURCE_SFTP_HOST=dev-source.example.com
SOURCE_SFTP_PORT=22
SOURCE_SFTP_USERNAME=dev_user
SOURCE_SFTP_PASSWORD=dev_password
SOURCE_SFTP_PATH=/dev/incoming

DEST_SFTP_HOST=dev-dest.example.com
DEST_SFTP_PORT=22
DEST_SFTP_USERNAME=dev_user
DEST_SFTP_PASSWORD=dev_password
DEST_SFTP_PATH=/dev/processed

# Development email (use test SMTP)
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=587
SMTP_USERNAME=your_mailtrap_user
SMTP_PASSWORD=your_mailtrap_password
ADMIN_EMAIL=dev@example.com

# Fast polling for development
POLL_INTERVAL_SECONDS=30

# Local storage
LOCAL_STORAGE_PATH=./data
TEMP_PATH=./temp

# Development timezone
TZ=America/New_York
```

## Staging Deployment

### Staging Environment Setup

```bash
# Create staging directory
sudo mkdir -p /opt/webscribe-ftps-workflow-staging
sudo chown medproc:medproc /opt/webscribe-ftps-workflow-staging

# Deploy application
cd /opt/webscribe-ftps-workflow-staging
# Copy application files here

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup staging configuration
cp .env.example .env.staging
# Edit .env.staging with staging settings

# Create systemd service for staging
sudo cp deployment/staging.service /etc/systemd/system/webscribe-workflow-staging.service
sudo systemctl daemon-reload
sudo systemctl enable webscribe-workflow-staging
```

### Staging Configuration

```bash
# Staging SFTP servers
SOURCE_SFTP_HOST=staging-source.example.com
DEST_SFTP_HOST=staging-dest.example.com

# Staging email
SMTP_HOST=smtp-staging.example.com
ADMIN_EMAIL=staging-admin@example.com

# Production-like polling
POLL_INTERVAL_SECONDS=300  # 5 minutes

# Staging storage paths
LOCAL_STORAGE_PATH=/opt/webscribe-ftps-workflow-staging/data
TEMP_PATH=/opt/webscribe-ftps-workflow-staging/temp
```

## Production Deployment

### 1. Server Preparation

#### Security Hardening
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow out 22    # SFTP
sudo ufw allow out 587   # SMTP
sudo ufw allow out 443   # HTTPS

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Install fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

#### System Optimization
```bash
# Increase file descriptor limits
echo "medproc soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "medproc hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Configure log rotation
sudo tee /etc/logrotate.d/webscribe-workflow << EOF
/opt/webscribe-ftps-workflow/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 medproc medproc
}
EOF
```

### 2. Application Deployment

```bash
# Create production directory
sudo mkdir -p /opt/webscribe-ftps-workflow
sudo chown medproc:medproc /opt/webscribe-ftps-workflow

# Deploy application (as medproc user)
sudo su - medproc
cd /opt/webscribe-ftps-workflow

# Copy application files
# (Use your preferred deployment method: git, rsync, etc.)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup production configuration
cp .env.example .env
# Edit .env with production settings

# Create data directories with proper permissions
mkdir -p data/logs data/csv_files temp
chmod 755 data data/logs data/csv_files temp
```

### 3. Production Configuration

```bash
# Production SFTP servers
SOURCE_SFTP_HOST=prod-source.company.com
SOURCE_SFTP_PORT=22
SOURCE_SFTP_USERNAME=prod_sftp_user
SOURCE_SFTP_PASSWORD=secure_password_here
SOURCE_SFTP_PATH=/production/incoming

DEST_SFTP_HOST=prod-dest.company.com
DEST_SFTP_PORT=22
DEST_SFTP_USERNAME=prod_sftp_user
DEST_SFTP_PASSWORD=secure_password_here
DEST_SFTP_PATH=/production/processed

# Production email
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=notifications@company.com
SMTP_PASSWORD=secure_smtp_password
ADMIN_EMAIL=admin@company.com

# Production scheduling
POLL_CRON="0 */2 * * *"  # Every 2 hours
TZ=America/New_York

# Production storage
LOCAL_STORAGE_PATH=/opt/webscribe-ftps-workflow/data
TEMP_PATH=/opt/webscribe-ftps-workflow/temp
```

### 4. Service Configuration

Create systemd service file:

```bash
sudo tee /etc/systemd/system/webscribe-ftps-workflow.service << EOF
[Unit]
Description=WebScribe FTPS Workflow System
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=medproc
Group=medproc
WorkingDirectory=/opt/webscribe-ftps-workflow
Environment=PATH=/opt/webscribe-ftps-workflow/venv/bin
ExecStart=/opt/webscribe-ftps-workflow/venv/bin/python src/main.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=webscribe-workflow

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/webscribe-ftps-workflow/data /opt/webscribe-ftps-workflow/temp

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable webscribe-ftps-workflow
sudo systemctl start webscribe-ftps-workflow

# Check status
sudo systemctl status webscribe-ftps-workflow
```

### 5. Monitoring Setup

#### Log Monitoring with journalctl
```bash
# View real-time logs
sudo journalctl -u webscribe-ftps-workflow -f

# View logs from last hour
sudo journalctl -u webscribe-ftps-workflow --since "1 hour ago"

# View logs with specific priority
sudo journalctl -u webscribe-ftps-workflow -p err
```

#### Health Check Script
```bash
sudo tee /opt/webscribe-ftps-workflow/health_check.sh << 'EOF'
#!/bin/bash

HEALTH_CHECK_LOG="/opt/webscribe-ftps-workflow/data/logs/health_check.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting health check" >> $HEALTH_CHECK_LOG

# Check if service is running
if systemctl is-active --quiet webscribe-ftps-workflow; then
    echo "[$DATE] ✓ Service is running" >> $HEALTH_CHECK_LOG
else
    echo "[$DATE] ✗ Service is not running" >> $HEALTH_CHECK_LOG
    exit 1
fi

# Check disk space
DISK_USAGE=$(df /opt/webscribe-ftps-workflow | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 90 ]; then
    echo "[$DATE] ✓ Disk usage: ${DISK_USAGE}%" >> $HEALTH_CHECK_LOG
else
    echo "[$DATE] ✗ Disk usage critical: ${DISK_USAGE}%" >> $HEALTH_CHECK_LOG
    exit 1
fi

# Check recent log activity
if find /opt/webscribe-ftps-workflow/data/logs -name "*.log" -mmin -30 | grep -q .; then
    echo "[$DATE] ✓ Recent log activity detected" >> $HEALTH_CHECK_LOG
else
    echo "[$DATE] ⚠ No recent log activity" >> $HEALTH_CHECK_LOG
fi

echo "[$DATE] Health check completed successfully" >> $HEALTH_CHECK_LOG
EOF

chmod +x /opt/webscribe-ftps-workflow/health_check.sh

# Add to crontab for regular health checks
(crontab -l 2>/dev/null; echo "*/15 * * * * /opt/webscribe-ftps-workflow/health_check.sh") | crontab -
```

## Docker Deployment

### 1. Dockerfile

```dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY src/ ./src/
COPY .env.example .env

# Create non-root user
RUN useradd -r -u 1001 medproc && \
    mkdir -p data/logs data/csv_files temp && \
    chown -R medproc:medproc /app

USER medproc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

CMD ["python", "src/main.py"]
```

### 2. Docker Compose

```yaml
version: '3.8'

services:
  webscribe-workflow:
    build: .
    container_name: webscribe-ftps-workflow
    restart: unless-stopped
    environment:
      - SOURCE_SFTP_HOST=${SOURCE_SFTP_HOST}
      - SOURCE_SFTP_USERNAME=${SOURCE_SFTP_USERNAME}
      - SOURCE_SFTP_PASSWORD=${SOURCE_SFTP_PASSWORD}
      - DEST_SFTP_HOST=${DEST_SFTP_HOST}
      - DEST_SFTP_USERNAME=${DEST_SFTP_USERNAME}
      - DEST_SFTP_PASSWORD=${DEST_SFTP_PASSWORD}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - ADMIN_EMAIL=${ADMIN_EMAIL}
      - POLL_INTERVAL_SECONDS=${POLL_INTERVAL_SECONDS:-60}
      - TZ=${TZ:-UTC}
    volumes:
      - ./data:/app/data
      - ./temp:/app/temp
    networks:
      - medical-processor-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  medical-processor-network:
    driver: bridge
```

### 3. Docker Deployment Commands

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f webscribe-workflow

# Stop and remove
docker-compose down

# Update and restart
docker-compose pull
docker-compose up -d --force-recreate
```

## Cloud Deployment

### AWS EC2 Deployment

#### 1. EC2 Instance Setup

```bash
# Launch EC2 instance (t3.small or larger recommended)
# Use Amazon Linux 2 or Ubuntu 20.04 LTS

# Connect to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Update system
sudo yum update -y  # Amazon Linux
# sudo apt update && sudo apt upgrade -y  # Ubuntu

# Install Docker (optional)
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

#### 2. Security Group Configuration

Allow the following outbound traffic:
- Port 22 (SFTP)
- Port 587 (SMTP)
- Port 443 (HTTPS)
- Port 80 (HTTP) - if needed

#### 3. IAM Role (Optional)

Create IAM role with permissions for:
- CloudWatch Logs (for centralized logging)
- S3 (for backup storage)
- SES (for email notifications)

### Azure VM Deployment

```bash
# Create resource group
az group create --name webscribe-workflow-rg --location eastus

# Create VM
az vm create \
  --resource-group webscribe-workflow-rg \
  --name webscribe-workflow-vm \
  --image UbuntuLTS \
  --admin-username medproc \
  --generate-ssh-keys \
  --size Standard_B2s

# Open ports
az vm open-port --port 22 --resource-group webscribe-workflow-rg --name webscribe-workflow-vm
```

### Google Cloud Platform Deployment

```bash
# Create VM instance
gcloud compute instances create webscribe-workflow \
  --zone=us-central1-a \
  --machine-type=e2-small \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB

# SSH to instance
gcloud compute ssh webscribe-workflow --zone=us-central1-a
```

## Security Considerations

### 1. Credential Management

#### Environment Variables
```bash
# Use strong passwords
SOURCE_SFTP_PASSWORD=$(openssl rand -base64 32)
DEST_SFTP_PASSWORD=$(openssl rand -base64 32)
SMTP_PASSWORD=$(openssl rand -base64 32)

# Restrict .env file permissions
chmod 600 .env
chown medproc:medproc .env
```

#### AWS Secrets Manager Integration
```python
# Example integration with AWS Secrets Manager
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Use in configuration
secrets = get_secret('webscribe-workflow/prod')
SOURCE_SFTP_PASSWORD = secrets['source_sftp_password']
```

### 2. Network Security

#### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow out 22    # SFTP
sudo ufw allow out 587   # SMTP

# iptables (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=587/tcp
sudo firewall-cmd --reload
```

#### VPN Configuration (if required)
```bash
# Install OpenVPN client
sudo apt install openvpn

# Configure VPN connection
sudo openvpn --config /path/to/client.ovpn --daemon

# Auto-start VPN
sudo systemctl enable openvpn@client
```

### 3. File System Security

```bash
# Set secure permissions
chmod 700 /opt/webscribe-ftps-workflow
chmod 600 /opt/webscribe-ftps-workflow/.env
chmod 755 /opt/webscribe-ftps-workflow/data
chmod 700 /opt/webscribe-ftps-workflow/temp

# Enable SELinux (if available)
sudo setsebool -P httpd_can_network_connect 1
```

## Monitoring and Maintenance

### 1. Log Management

#### Centralized Logging with rsyslog
```bash
# Configure rsyslog for centralized logging
sudo tee -a /etc/rsyslog.conf << EOF
# Medical Document Processor logs
local0.*    /var/log/webscribe-workflow.log
EOF

sudo systemctl restart rsyslog
```

#### Log Rotation
```bash
# Configure logrotate
sudo tee /etc/logrotate.d/webscribe-workflow << EOF
/opt/webscribe-ftps-workflow/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 medproc medproc
    postrotate
        systemctl reload webscribe-ftps-workflow
    endscript
}
EOF
```

### 2. Backup Strategy

#### Data Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/webscribe-workflow"
DATE=$(date +%Y%m%d_%H%M%S)
SOURCE_DIR="/opt/webscribe-ftps-workflow"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration and data
tar -czf $BACKUP_DIR/webscribe-workflow-$DATE.tar.gz \
    $SOURCE_DIR/.env \
    $SOURCE_DIR/data/csv_files \
    $SOURCE_DIR/data/logs

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: webscribe-workflow-$DATE.tar.gz"
```

#### Automated Backup with Cron
```bash
# Add to crontab
0 2 * * * /opt/webscribe-ftps-workflow/backup.sh >> /var/log/backup.log 2>&1
```

### 3. Performance Monitoring

#### System Monitoring Script
```bash
#!/bin/bash
# monitor.sh

LOG_FILE="/opt/webscribe-ftps-workflow/data/logs/system_monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# CPU Usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)

# Memory Usage
MEM_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')

# Disk Usage
DISK_USAGE=$(df /opt/webscribe-ftps-workflow | tail -1 | awk '{print $5}' | sed 's/%//')

# Network Connections
SFTP_CONNECTIONS=$(netstat -an | grep :22 | grep ESTABLISHED | wc -l)

echo "[$DATE] CPU: ${CPU_USAGE}%, Memory: ${MEM_USAGE}%, Disk: ${DISK_USAGE}%, SFTP Connections: $SFTP_CONNECTIONS" >> $LOG_FILE
```

### 4. Update and Maintenance Procedures

#### Application Updates
```bash
#!/bin/bash
# update.sh

# Stop service
sudo systemctl stop webscribe-ftps-workflow

# Backup current version
cp -r /opt/webscribe-ftps-workflow /opt/webscribe-ftps-workflow.backup.$(date +%Y%m%d)

# Update application code
cd /opt/webscribe-ftps-workflow
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run tests (if available)
python -m pytest tests/ || exit 1

# Start service
sudo systemctl start webscribe-ftps-workflow

# Verify service is running
sleep 10
sudo systemctl status webscribe-ftps-workflow

echo "Update completed successfully"
```

#### System Maintenance
```bash
#!/bin/bash
# maintenance.sh

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean up old logs
find /opt/webscribe-ftps-workflow/data/logs -name "*.log.*" -mtime +30 -delete

# Clean up old CSV files (older than 60 days)
find /opt/webscribe-ftps-workflow/data/csv_files -name "*.csv" -mtime +60 -delete

# Clean up temporary files
rm -rf /opt/webscribe-ftps-workflow/temp/*

# Restart service to refresh connections
sudo systemctl restart webscribe-ftps-workflow

echo "Maintenance completed"
```

## Troubleshooting Deployment Issues

### Common Deployment Problems

#### 1. Permission Issues
```bash
# Fix ownership
sudo chown -R medproc:medproc /opt/webscribe-ftps-workflow

# Fix permissions
chmod 755 /opt/webscribe-ftps-workflow
chmod 600 /opt/webscribe-ftps-workflow/.env
chmod -R 755 /opt/webscribe-ftps-workflow/data
```

#### 2. Service Won't Start
```bash
# Check service status
sudo systemctl status webscribe-ftps-workflow

# Check logs
sudo journalctl -u webscribe-ftps-workflow -n 50

# Test configuration
sudo -u medproc /opt/webscribe-ftps-workflow/venv/bin/python /opt/webscribe-ftps-workflow/src/main.py --test-config
```

#### 3. Network Connectivity Issues
```bash
# Test SFTP connectivity
telnet your-sftp-host 22

# Test SMTP connectivity
telnet your-smtp-host 587

# Check firewall rules
sudo ufw status
sudo iptables -L
```

#### 4. Resource Issues
```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check file descriptors
lsof | wc -l
ulimit -n
```

This deployment guide provides comprehensive instructions for deploying the Medical Document Processing System in various environments with proper security, monitoring, and maintenance procedures.
