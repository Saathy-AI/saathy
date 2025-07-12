#!/bin/bash

# Saathy Qdrant Backup Script
# Usage: ./scripts/backup.sh [--retention-days N]

set -e

# Configuration
BACKUP_DIR="/opt/saathy/backups"
QDRANT_CONTAINER="saathy-qdrant-1"
RETENTION_DAYS=30
LOG_FILE="/var/log/saathy/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
while [[ $# -gt 0 ]]; do
    case $1 in
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--retention-days N]"
            echo "  --retention-days N  Keep backups for N days (default: 30)"
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
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
    
    log "INFO" "Prerequisites check passed"
}

# Create backup
create_backup() {
    log "INFO" "Creating Qdrant backup..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Generate backup filename with timestamp
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_name="qdrant-backup-${timestamp}.tar.gz"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    # Create backup using docker exec
    log "INFO" "Creating backup: $backup_name"
    
    if docker exec "$QDRANT_CONTAINER" tar -czf /tmp/backup.tar.gz -C /qdrant/storage .; then
        # Copy backup from container to host
        docker cp "$QDRANT_CONTAINER:/tmp/backup.tar.gz" "$backup_path"
        
        # Clean up temporary file in container
        docker exec "$QDRANT_CONTAINER" rm -f /tmp/backup.tar.gz
        
        # Get backup size
        local backup_size=$(du -h "$backup_path" | cut -f1)
        log "INFO" "Backup created successfully: $backup_name (${backup_size})"
        
        # Create backup metadata
        cat > "$BACKUP_DIR/${backup_name}.meta" << EOF
Backup created: $(date)
Container: $QDRANT_CONTAINER
Size: ${backup_size}
Version: $(docker exec $QDRANT_CONTAINER qdrant --version 2>/dev/null || echo "unknown")
EOF
        
        return 0
    else
        error_exit "Failed to create backup"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "INFO" "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    
    # Find and delete old backup files
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            rm -f "$file"
            rm -f "${file}.meta"
            ((deleted_count++))
            log "INFO" "Deleted old backup: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "qdrant-backup-*.tar.gz" -mtime +$RETENTION_DAYS -print0)
    
    log "INFO" "Cleanup completed: $deleted_count old backups removed"
}

# List existing backups
list_backups() {
    log "INFO" "Listing existing backups:"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_count=0
        while IFS= read -r -d '' file; do
            if [[ -f "$file" ]]; then
                local size=$(du -h "$file" | cut -f1)
                local date=$(stat -c %y "$file" | cut -d' ' -f1)
                echo "  $(basename "$file") - ${size} - $date"
                ((backup_count++))
            fi
        done < <(find "$BACKUP_DIR" -name "qdrant-backup-*.tar.gz" -print0 | sort -z)
        
        if [[ $backup_count -eq 0 ]]; then
            log "INFO" "No backups found"
        else
            log "INFO" "Total backups: $backup_count"
        fi
    else
        log "INFO" "Backup directory does not exist"
    fi
}

# Main execution
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "INFO" "Starting Qdrant backup process..."
    
    # Check prerequisites
    check_prerequisites
    
    # List existing backups
    list_backups
    
    # Create new backup
    create_backup
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "INFO" "Backup process completed successfully"
}

# Run main function
main "$@" 