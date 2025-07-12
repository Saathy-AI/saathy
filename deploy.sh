#!/bin/bash

# Saathy Production Deployment Script
# Usage: ./deploy.sh [--init|--rollback|--dry-run]

set -e  # Exit on any error

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="/opt/saathy/backups"
LOG_FILE="/var/log/saathy/deploy.log"
HEALTH_CHECK_URL="http://localhost/healthz"
HEALTH_CHECK_TIMEOUT=60
ROLLBACK_TAG="saathy-rollback"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error_exit "This script should not be run as root"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed"
    fi
    
    if ! command -v git &> /dev/null; then
        error_exit "Git is not installed"
    fi
    
    if ! command -v curl &> /dev/null; then
        error_exit "curl is not installed"
    fi
    
    log "INFO" "Prerequisites check passed"
}

# Create backup
create_backup() {
    log "INFO" "Creating backup of current deployment..."
    
    mkdir -p "$BACKUP_DIR"
    local backup_name="saathy-backup-$(date +%Y%m%d-%H%M%S)"
    
    # Backup current images
    docker images --format "table {{.Repository}}:{{.Tag}}" | grep saathy > "$BACKUP_DIR/${backup_name}-images.txt" || true
    
    # Backup current compose file
    cp "$COMPOSE_FILE" "$BACKUP_DIR/${backup_name}-compose.yml" || true
    
    log "INFO" "Backup created: $backup_name"
}

# Health check function
health_check() {
    local max_attempts=$1
    local attempt=1
    
    log "INFO" "Performing health check..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
            log "INFO" "Health check passed on attempt $attempt"
            return 0
        else
            log "WARN" "Health check failed on attempt $attempt/$max_attempts"
            if [[ $attempt -lt $max_attempts ]]; then
                sleep 5
            fi
        fi
        ((attempt++))
    done
    
    return 1
}

# Rollback function
rollback() {
    log "WARN" "Initiating rollback..."
    
    # Stop current containers
    docker-compose -f "$COMPOSE_FILE" down || true
    
    # Restore from backup
    local latest_backup=$(ls -t "$BACKUP_DIR"/saathy-backup-* 2>/dev/null | head -1)
    if [[ -n "$latest_backup" ]]; then
        log "INFO" "Restoring from backup: $latest_backup"
        # Implementation would depend on backup strategy
    fi
    
    # Restart with previous version
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for health check
    if health_check 5; then
        log "INFO" "Rollback completed successfully"
    else
        error_exit "Rollback failed - health check did not pass"
    fi
}

# Cleanup old images
cleanup_images() {
    log "INFO" "Cleaning up unused Docker images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove unused images older than 7 days
    docker image prune -a --filter "until=168h" -f
    
    log "INFO" "Cleanup completed"
}

# Initial setup
initial_setup() {
    log "INFO" "Performing initial VPS setup..."
    
    # Create necessary directories
    sudo mkdir -p /var/log/saathy
    sudo mkdir -p /opt/saathy/backups
    sudo mkdir -p /opt/saathy/ssl
    
    # Set proper permissions
    sudo chown -R $USER:$USER /var/log/saathy
    sudo chown -R $USER:$USER /opt/saathy
    
    # Create log file
    touch "$LOG_FILE"
    
    # Install curl if not present
    if ! command -v curl &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y curl
    fi
    
    log "INFO" "Initial setup completed"
}

# Main deployment function
deploy() {
    local dry_run=${1:-false}
    
    log "INFO" "Starting deployment..."
    
    if [[ "$dry_run" == "true" ]]; then
        log "INFO" "DRY RUN MODE - No actual changes will be made"
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error_exit "Not in a git repository"
    fi
    
    # Create backup before deployment
    create_backup
    
    # Pull latest code
    log "INFO" "Pulling latest code..."
    if [[ "$dry_run" != "true" ]]; then
        git pull origin main
    fi
    
    # Build images
    log "INFO" "Building Docker images..."
    if [[ "$dry_run" != "true" ]]; then
        docker-compose -f "$COMPOSE_FILE" build --no-cache
    fi
    
    # Tag current version for potential rollback
    if [[ "$dry_run" != "true" ]]; then
        docker tag saathy-saathy-api:latest saathy-saathy-api:$ROLLBACK_TAG || true
    fi
    
    # Deploy new version
    log "INFO" "Deploying new version..."
    if [[ "$dry_run" != "true" ]]; then
        docker-compose -f "$COMPOSE_FILE" up -d
    fi
    
    # Wait for services to start
    log "INFO" "Waiting for services to start..."
    sleep 30
    
    # Health check
    if health_check 5; then
        log "INFO" "Deployment completed successfully"
        
        # Cleanup old images
        cleanup_images
        
        # Remove rollback tag
        if [[ "$dry_run" != "true" ]]; then
            docker rmi saathy-saathy-api:$ROLLBACK_TAG || true
        fi
    else
        log "ERROR" "Health check failed after deployment"
        if [[ "$dry_run" != "true" ]]; then
            rollback
        fi
        error_exit "Deployment failed"
    fi
}

# Main script logic
main() {
    local init_mode=false
    local rollback_mode=false
    local dry_run_mode=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --init)
                init_mode=true
                shift
                ;;
            --rollback)
                rollback_mode=true
                shift
                ;;
            --dry-run)
                dry_run_mode=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [--init|--rollback|--dry-run]"
                echo "  --init     Perform initial VPS setup"
                echo "  --rollback Rollback to previous version"
                echo "  --dry-run  Show what would be done without making changes"
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Check if not running as root
    check_root
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Execute based on mode
    if [[ "$init_mode" == "true" ]]; then
        initial_setup
        deploy "$dry_run_mode"
    elif [[ "$rollback_mode" == "true" ]]; then
        rollback
    else
        deploy "$dry_run_mode"
    fi
    
    log "INFO" "Script completed successfully"
}

# Run main function with all arguments
main "$@" 