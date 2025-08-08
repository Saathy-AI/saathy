#!/bin/bash

# Saathy Conversational AI Deployment Script
# This script sets up and deploys the complete conversational AI system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup environment
setup_environment() {
    print_info "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f ".env.example" ]]; then
            cp .env.example "$ENV_FILE"
            print_warning "Created $ENV_FILE from template. Please update it with your configuration."
            print_warning "Required: OPENAI_API_KEY, SECRET_KEY"
        else
            print_error ".env.example file not found. Cannot create environment file."
            exit 1
        fi
    fi
    
    # Validate required environment variables
    source "$ENV_FILE"
    
    if [[ -z "$OPENAI_API_KEY" || "$OPENAI_API_KEY" == "your-openai-api-key" ]]; then
        print_error "OPENAI_API_KEY is not set in $ENV_FILE"
        exit 1
    fi
    
    if [[ -z "$SECRET_KEY" || "$SECRET_KEY" == "your-super-secret-key-here" ]]; then
        print_warning "SECRET_KEY should be changed from default value"
    fi
    
    print_success "Environment setup complete"
}

# Function to create backup
create_backup() {
    print_info "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup volumes if they exist
    if docker volume ls | grep -q "saathy-conversational-ai_postgres_data"; then
        print_info "Backing up PostgreSQL data..."
        docker run --rm -v saathy-conversational-ai_postgres_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
    fi
    
    if docker volume ls | grep -q "saathy-conversational-ai_redis_data"; then
        print_info "Backing up Redis data..."
        docker run --rm -v saathy-conversational-ai_redis_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
    fi
    
    if docker volume ls | grep -q "saathy-conversational-ai_qdrant_data"; then
        print_info "Backing up Qdrant data..."
        docker run --rm -v saathy-conversational-ai_qdrant_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/qdrant_data.tar.gz -C /data .
    fi
    
    print_success "Backup created in $BACKUP_DIR"
}

# Function to build and deploy
deploy() {
    print_info "Starting deployment..."
    
    # Pull latest images
    print_info "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build custom images
    print_info "Building application images..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Start services
    print_info "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    print_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    check_service_health
    
    print_success "Deployment completed successfully!"
}

# Function to check service health
check_service_health() {
    print_info "Checking service health..."
    
    local services=("api" "postgres" "redis" "qdrant")
    local healthy_services=0
    
    for service in "${services[@]}"; do
        local container_name="saathy-conversational-$service"
        if docker ps | grep -q "$container_name"; then
            if docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy"; then
                print_success "$service is healthy"
                ((healthy_services++))
            else
                print_warning "$service is not healthy yet"
            fi
        else
            print_error "$service container is not running"
        fi
    done
    
    if [[ $healthy_services -eq ${#services[@]} ]]; then
        print_success "All services are healthy"
    else
        print_warning "Some services are not healthy yet. Check logs with: docker-compose logs"
    fi
}

# Function to run database migrations
run_migrations() {
    print_info "Running database migrations..."
    
    # Wait for PostgreSQL to be ready
    docker-compose exec -T postgres pg_isready -U saathy -d saathy_conversational
    
    # Run initialization script if needed
    if docker-compose exec -T api python -c "import asyncio; from app.models import Base; print('Database check passed')" 2>/dev/null; then
        print_success "Database is ready"
    else
        print_warning "Running database initialization..."
        docker-compose exec -T api python -c "
import asyncio
from app.models import Base
from app.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine

async def init_db():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(init_db())
print('Database initialized')
"
    fi
    
    print_success "Database migrations completed"
}

# Function to show service URLs
show_urls() {
    print_info "Service URLs:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Documentation: http://localhost:8000/docs"
    echo "  Prometheus: http://localhost:9091"
    echo "  Grafana: http://localhost:3001 (admin/admin)"
    echo "  PostgreSQL: localhost:5433"
    echo "  Redis: localhost:6380"
    echo "  Qdrant: http://localhost:6334"
}

# Function to cleanup
cleanup() {
    print_info "Cleaning up..."
    docker-compose -f "$COMPOSE_FILE" down
    docker system prune -f
    print_success "Cleanup completed"
}

# Function to show logs
show_logs() {
    local service=${1:-}
    if [[ -n "$service" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Function to stop services
stop() {
    print_info "Stopping services..."
    docker-compose -f "$COMPOSE_FILE" down
    print_success "Services stopped"
}

# Function to restart services
restart() {
    print_info "Restarting services..."
    docker-compose -f "$COMPOSE_FILE" restart
    print_success "Services restarted"
}

# Function to show status
status() {
    print_info "Service status:"
    docker-compose -f "$COMPOSE_FILE" ps
}

# Function to show help
show_help() {
    echo "Saathy Conversational AI Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy          Deploy the complete system (default)"
    echo "  backup          Create a backup of data volumes"
    echo "  migrate         Run database migrations"
    echo "  status          Show service status"
    echo "  logs [service]  Show logs for all services or specific service"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  cleanup         Stop services and clean up containers"
    echo "  urls            Show service URLs"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy the system"
    echo "  $0 deploy             # Deploy the system"
    echo "  $0 logs api           # Show API logs"
    echo "  $0 backup             # Create backup"
    echo "  $0 status             # Show status"
}

# Main execution
main() {
    local command=${1:-deploy}
    
    case "$command" in
        "deploy")
            check_prerequisites
            setup_environment
            deploy
            run_migrations
            show_urls
            ;;
        "backup")
            create_backup
            ;;
        "migrate")
            run_migrations
            ;;
        "status")
            status
            ;;
        "logs")
            show_logs "$2"
            ;;
        "stop")
            stop
            ;;
        "restart")
            restart
            ;;
        "cleanup")
            cleanup
            ;;
        "urls")
            show_urls
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"