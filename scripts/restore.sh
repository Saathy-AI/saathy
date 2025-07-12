#!/bin/bash

# Saathy Qdrant Restore Script
# Usage: ./scripts/restore.sh [backup-file] [--force]

set -e

# Configuration
BACKUP_DIR="/opt/saathy/backups"
QDRANT_CONTAINER="saathy-qdrant-1"
LOG_FILE="/var/log/saathy/restore.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Parse command line arguments
BACKUP_FILE=""
FORCE_RESTORE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_RESTORE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [backup-file] [--force]"
            echo "  backup-file  Specific backup file to restore (optional)"
            echo "  --force      Skip confirmation prompts"
            echo ""
            echo "If no backup file is specified, the latest backup will be used."
            exit 0
            ;;
        -*)
            error_exit "Unknown option: $1"
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                error_exit "Multiple backup files specified"
            fi
            shift
            ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed"
    fi

    if ! docker ps | grep -q "$QDRANT_CONTAINER"; then
        error_exit "Qdrant container is not running"
    fi

    if [[ ! -d "$BACKUP_DIR" ]]; then
        error_exit "Backup directory does not exist: $BACKUP_DIR"
    fi

    log "INFO" "Prerequisites check passed"
}

# List available backups
list_backups() {
    log "INFO" "Available backups:"

    local backup_count=0
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local size=$(du -h "$file" | cut -f1)
            local date=$(stat -c %y "$file" | cut -d' ' -f1)
            local filename=$(basename "$file")
            echo "  $filename - ${size} - $date"
            ((backup_count++))
        fi
    done < <(find "$BACKUP_DIR" -name "qdrant-backup-*.tar.gz" -print0 | sort -z)

    if [[ $backup_count -eq 0 ]]; then
        error_exit "No backup files found in $BACKUP_DIR"
    fi

    log "INFO" "Total backups: $backup_count"
}

# Select backup file
select_backup() {
    if [[ -n "$BACKUP_FILE" ]]; then
        # Use specified backup file
        if [[ "$BACKUP_FILE" != /* ]]; then
            BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
        fi

        if [[ ! -f "$BACKUP_FILE" ]]; then
            error_exit "Backup file not found: $BACKUP_FILE"
        fi

        log "INFO" "Using specified backup: $BACKUP_FILE"
    else
        # Use latest backup
        BACKUP_FILE=$(find "$BACKUP_DIR" -name "qdrant-backup-*.tar.gz" -print0 | xargs -0 ls -t | head -1)

        if [[ -z "$BACKUP_FILE" ]]; then
            error_exit "No backup files found"
        fi

        log "INFO" "Using latest backup: $BACKUP_FILE"
    fi
}

# Validate backup file
validate_backup() {
    log "INFO" "Validating backup file..."

    if [[ ! -f "$BACKUP_FILE" ]]; then
        error_exit "Backup file does not exist: $BACKUP_FILE"
    fi

    # Check if file is a valid tar.gz
    if ! tar -tzf "$BACKUP_FILE" > /dev/null 2>&1; then
        error_exit "Invalid backup file: $BACKUP_FILE"
    fi

    # Check backup size
    local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
    log "INFO" "Backup file validated: $(basename "$BACKUP_FILE") (${backup_size})"
}

# Create pre-restore backup
create_pre_restore_backup() {
    log "INFO" "Creating pre-restore backup..."

    local timestamp=$(date +%Y%m%d-%H%M%S)
    local pre_backup_name="pre-restore-backup-${timestamp}.tar.gz"
    local pre_backup_path="$BACKUP_DIR/$pre_backup_name"

    if docker exec "$QDRANT_CONTAINER" tar -czf /tmp/pre_restore_backup.tar.gz -C /qdrant/storage .; then
        docker cp "$QDRANT_CONTAINER:/tmp/pre_restore_backup.tar.gz" "$pre_backup_path"
        docker exec "$QDRANT_CONTAINER" rm -f /tmp/pre_restore_backup.tar.gz

        log "INFO" "Pre-restore backup created: $pre_backup_name"
    else
        log "WARN" "Failed to create pre-restore backup, continuing anyway..."
    fi
}

# Confirm restoration
confirm_restore() {
    if [[ "$FORCE_RESTORE" == "true" ]]; then
        log "INFO" "Force flag set, skipping confirmation"
        return 0
    fi

    echo -e "${YELLOW}WARNING: This will overwrite all current Qdrant data!${NC}"
    echo -e "Backup file: ${BLUE}$(basename "$BACKUP_FILE")${NC}"
    echo -e "Container: ${BLUE}$QDRANT_CONTAINER${NC}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        log "INFO" "Restoration cancelled by user"
        exit 0
    fi
}

# Perform restoration
perform_restore() {
    log "INFO" "Starting Qdrant data restoration..."

    # Stop Qdrant container
    log "INFO" "Stopping Qdrant container..."
    docker stop "$QDRANT_CONTAINER"

    # Wait for container to stop
    sleep 5

    # Copy backup to container
    log "INFO" "Copying backup to container..."
    docker cp "$BACKUP_FILE" "$QDRANT_CONTAINER:/tmp/restore_backup.tar.gz"

    # Extract backup in container
    log "INFO" "Extracting backup data..."
    docker exec "$QDRANT_CONTAINER" rm -rf /qdrant/storage/*
    docker exec "$QDRANT_CONTAINER" tar -xzf /tmp/restore_backup.tar.gz -C /qdrant/storage
    docker exec "$QDRANT_CONTAINER" rm -f /tmp/restore_backup.tar.gz

    # Start Qdrant container
    log "INFO" "Starting Qdrant container..."
    docker start "$QDRANT_CONTAINER"

    # Wait for container to be ready
    log "INFO" "Waiting for Qdrant to be ready..."
    sleep 30

    # Verify restoration
    if docker exec "$QDRANT_CONTAINER" curl -f -s http://localhost:6334/health > /dev/null; then
        log "INFO" "Qdrant health check passed"
    else
        log "WARN" "Qdrant health check failed, but container is running"
    fi
}

# Main execution
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"

    log "INFO" "Starting Qdrant restore process..."

    # Check prerequisites
    check_prerequisites

    # List available backups
    list_backups

    # Select backup file
    select_backup

    # Validate backup file
    validate_backup

    # Create pre-restore backup
    create_pre_restore_backup

    # Confirm restoration
    confirm_restore

    # Perform restoration
    perform_restore

    log "INFO" "Restore process completed successfully"
    log "INFO" "Qdrant data has been restored from: $(basename "$BACKUP_FILE")"
}

# Run main function
main "$@"
