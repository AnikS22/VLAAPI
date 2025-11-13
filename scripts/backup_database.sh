#!/bin/bash
# Database backup script for VLA API
# Run this daily via cron: 0 2 * * * /path/to/backup_database.sh

set -e  # Exit on error

# Configuration
BACKUP_DIR="/var/backups/vlaapi"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# S3 Configuration (optional - set these to enable S3 backups)
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
S3_PREFIX="${S3_BACKUP_PREFIX:-backups/database}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
log_info "Starting database backup..."

# Backup PostgreSQL
if docker-compose ps postgres | grep -q "Up"; then
    log_info "Backing up PostgreSQL database..."
    
    POSTGRES_BACKUP="$BACKUP_DIR/vlaapi_postgres_$TIMESTAMP.sql"
    
    docker-compose exec -T postgres pg_dump -U vlaapi vlaapi > "$POSTGRES_BACKUP"
    
    if [ $? -eq 0 ]; then
        # Compress backup
        gzip "$POSTGRES_BACKUP"
        POSTGRES_BACKUP="${POSTGRES_BACKUP}.gz"
        
        SIZE=$(du -h "$POSTGRES_BACKUP" | cut -f1)
        log_info "PostgreSQL backup completed: $POSTGRES_BACKUP ($SIZE)"
    else
        log_error "PostgreSQL backup failed!"
        exit 1
    fi
else
    log_warning "PostgreSQL container is not running, skipping..."
fi

# Backup Redis (if you store important data there)
if docker-compose ps redis | grep -q "Up"; then
    log_info "Backing up Redis data..."
    
    REDIS_BACKUP="$BACKUP_DIR/vlaapi_redis_$TIMESTAMP.rdb"
    
    # Trigger Redis save
    docker-compose exec -T redis redis-cli SAVE > /dev/null
    
    # Copy RDB file
    docker cp $(docker-compose ps -q redis):/data/dump.rdb "$REDIS_BACKUP"
    
    if [ $? -eq 0 ]; then
        gzip "$REDIS_BACKUP"
        REDIS_BACKUP="${REDIS_BACKUP}.gz"
        
        SIZE=$(du -h "$REDIS_BACKUP" | cut -f1)
        log_info "Redis backup completed: $REDIS_BACKUP ($SIZE)"
    else
        log_warning "Redis backup failed (may be empty)"
    fi
fi

# Backup environment file
if [ -f ".env" ]; then
    log_info "Backing up .env file..."
    
    ENV_BACKUP="$BACKUP_DIR/vlaapi_env_$TIMESTAMP.txt"
    cp .env "$ENV_BACKUP"
    gzip "$ENV_BACKUP"
    
    log_info "Environment file backed up: ${ENV_BACKUP}.gz"
fi

# Upload to S3 (if configured)
if [ -n "$S3_BUCKET" ]; then
    log_info "Uploading backups to S3..."
    
    if command -v aws &> /dev/null; then
        for backup_file in "$BACKUP_DIR"/*_$TIMESTAMP.*.gz; do
            if [ -f "$backup_file" ]; then
                filename=$(basename "$backup_file")
                aws s3 cp "$backup_file" "s3://$S3_BUCKET/$S3_PREFIX/$filename"
                
                if [ $? -eq 0 ]; then
                    log_info "Uploaded $filename to S3"
                else
                    log_error "Failed to upload $filename to S3"
                fi
            fi
        done
    else
        log_warning "AWS CLI not installed, skipping S3 upload"
    fi
fi

# Clean up old backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."

find "$BACKUP_DIR" -name "vlaapi_*.gz" -mtime +$RETENTION_DAYS -delete

OLD_COUNT=$(find "$BACKUP_DIR" -name "vlaapi_*.gz" | wc -l)
log_info "Kept $OLD_COUNT backup(s)"

# Summary
log_info "Backup completed successfully!"
log_info "Backup location: $BACKUP_DIR"

# Check disk space
DISK_USAGE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $5}')
log_info "Backup disk usage: $DISK_USAGE"

if [ "${DISK_USAGE%\%}" -gt 80 ]; then
    log_warning "Backup disk is ${DISK_USAGE} full!"
fi






