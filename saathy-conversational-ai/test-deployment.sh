#!/bin/bash

# Saathy Conversational AI - Deployment Validation Script
# This script validates that the system is correctly deployed and functioning

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              Saathy Conversational AI                       ║"
    echo "║                 Deployment Validation                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

validate_services() {
    print_info "Checking service health..."
    
    local services=(
        "saathy-conversational-api:8000:/health"
        "saathy-conversational-frontend:80:/health"
        "saathy-conversational-db:5432"
        "saathy-conversational-redis:6379"
        "saathy-conversational-qdrant:6333:/health"
        "saathy-conversational-prometheus:9090/-/healthy"
        "saathy-conversational-grafana:3000/api/health"
    )
    
    local healthy=0
    local total=${#services[@]}
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r container port endpoint <<< "$service_info"
        
        if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
            if [[ -n "$endpoint" ]]; then
                if curl -sf "http://localhost:${port#*:}$endpoint" >/dev/null 2>&1; then
                    print_success "$container is healthy"
                    ((healthy++))
                else
                    print_warning "$container is running but health check failed"
                fi
            else
                print_success "$container is running"
                ((healthy++))
            fi
        else
            print_error "$container is not running"
        fi
    done
    
    echo
    print_info "Service Health: $healthy/$total services healthy"
    
    if [[ $healthy -eq $total ]]; then
        print_success "All services are healthy!"
        return 0
    else
        print_warning "Some services need attention"
        return 1
    fi
}

test_api_endpoints() {
    print_info "Testing API endpoints..."
    
    local base_url="http://localhost:8000"
    
    # Test health endpoint
    if curl -sf "$base_url/health" >/dev/null; then
        print_success "Health endpoint working"
    else
        print_error "Health endpoint failed"
        return 1
    fi
    
    # Test API documentation
    if curl -sf "$base_url/docs" >/dev/null; then
        print_success "API documentation accessible"
    else
        print_warning "API documentation not accessible"
    fi
    
    # Test chat session creation
    local session_response
    session_response=$(curl -s -X POST "$base_url/api/v2/chat/sessions" \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test_user"}' || echo "")
    
    if [[ -n "$session_response" ]] && echo "$session_response" | grep -q "id"; then
        print_success "Chat session creation working"
        
        # Extract session ID for further testing
        local session_id
        session_id=$(echo "$session_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        
        if [[ -n "$session_id" ]]; then
            # Test message sending (this might fail if OpenAI key is not configured)
            local message_response
            message_response=$(curl -s -X POST "$base_url/api/v2/chat/sessions/$session_id/messages" \
                -H "Content-Type: application/json" \
                -d '{"content": "Hello, this is a test message"}' || echo "")
            
            if [[ -n "$message_response" ]]; then
                print_success "Message processing working"
            else
                print_warning "Message processing failed (check OpenAI API key)"
            fi
        fi
    else
        print_error "Chat session creation failed"
        return 1
    fi
    
    return 0
}

test_frontend() {
    print_info "Testing frontend..."
    
    if curl -sf "http://localhost:3000" >/dev/null; then
        print_success "Frontend is accessible"
    else
        print_error "Frontend is not accessible"
        return 1
    fi
    
    # Test API proxy through frontend
    if curl -sf "http://localhost:3000/api/health" >/dev/null; then
        print_success "Frontend API proxy working"
    else
        print_warning "Frontend API proxy not working"
    fi
    
    return 0
}

test_databases() {
    print_info "Testing databases..."
    
    # Test PostgreSQL
    if docker exec saathy-conversational-db pg_isready -U saathy -d saathy_conversational >/dev/null 2>&1; then
        print_success "PostgreSQL is ready"
        
        # Test if tables exist
        local table_count
        table_count=$(docker exec saathy-conversational-db psql -U saathy -d saathy_conversational -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
        
        if [[ $table_count -gt 0 ]]; then
            print_success "Database tables initialized ($table_count tables)"
        else
            print_warning "Database tables not found (run ./deploy.sh migrate)"
        fi
    else
        print_error "PostgreSQL connection failed"
        return 1
    fi
    
    # Test Redis
    if docker exec saathy-conversational-redis redis-cli ping >/dev/null 2>&1; then
        print_success "Redis is responding"
    else
        print_error "Redis connection failed"
        return 1
    fi
    
    # Test Qdrant
    if curl -sf "http://localhost:6334/health" >/dev/null; then
        print_success "Qdrant is healthy"
    else
        print_error "Qdrant connection failed"
        return 1
    fi
    
    return 0
}

test_monitoring() {
    print_info "Testing monitoring stack..."
    
    # Test Prometheus
    if curl -sf "http://localhost:9091/-/healthy" >/dev/null; then
        print_success "Prometheus is healthy"
        
        # Check if targets are being scraped
        local targets_response
        targets_response=$(curl -s "http://localhost:9091/api/v1/targets" || echo "")
        
        if echo "$targets_response" | grep -q '"health":"up"'; then
            print_success "Prometheus targets are being scraped"
        else
            print_warning "Some Prometheus targets may be down"
        fi
    else
        print_error "Prometheus is not accessible"
        return 1
    fi
    
    # Test Grafana
    if curl -sf "http://localhost:3001/api/health" >/dev/null; then
        print_success "Grafana is accessible"
    else
        print_error "Grafana is not accessible"
        return 1
    fi
    
    return 0
}

show_service_urls() {
    print_info "Service URLs:"
    echo "  🌐 Frontend:           http://localhost:3000"
    echo "  🔧 API:                http://localhost:8000"
    echo "  📚 API Documentation:  http://localhost:8000/docs"
    echo "  📊 Grafana:            http://localhost:3001 (admin/admin)"
    echo "  📈 Prometheus:         http://localhost:9091"
    echo "  🔍 Qdrant Dashboard:   http://localhost:6334/dashboard"
    echo "  🗄️  PostgreSQL:        localhost:5433"
    echo "  💾 Redis:              localhost:6380"
}

check_environment() {
    print_info "Checking environment configuration..."
    
    if [[ -f ".env" ]]; then
        print_success ".env file exists"
        
        # Check if OpenAI API key is configured
        if grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
            print_success "OpenAI API key appears to be configured"
        elif grep -q "OPENAI_API_KEY=your-openai-api-key" .env 2>/dev/null; then
            print_warning "OpenAI API key needs to be updated in .env"
        else
            print_warning "OpenAI API key configuration unclear"
        fi
        
        # Check if secret key is changed from default
        if grep -q "SECRET_KEY=your-super-secret-key-here" .env 2>/dev/null; then
            print_warning "SECRET_KEY should be changed from default"
        else
            print_success "SECRET_KEY appears to be customized"
        fi
    else
        print_error ".env file not found (copy from .env.example)"
        return 1
    fi
    
    return 0
}

performance_check() {
    print_info "Basic performance check..."
    
    # Test response time
    local start_time=$(date +%s.%N)
    curl -sf "http://localhost:8000/health" >/dev/null
    local end_time=$(date +%s.%N)
    local response_time=$(echo "$end_time - $start_time" | bc -l)
    
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        print_success "API response time: ${response_time}s (good)"
    else
        print_warning "API response time: ${response_time}s (consider optimization)"
    fi
    
    # Check Docker resource usage
    local containers=$(docker ps --filter "name=saathy-conversational" --format "table {{.Names}}\t{{.CPUPerc}}\t{{.MemUsage}}" | tail -n +2)
    
    if [[ -n "$containers" ]]; then
        print_info "Container resource usage:"
        echo "$containers"
    fi
}

main() {
    print_header
    
    local overall_status=0
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Run all checks
    check_environment || overall_status=1
    echo
    
    validate_services || overall_status=1
    echo
    
    test_databases || overall_status=1
    echo
    
    test_api_endpoints || overall_status=1
    echo
    
    test_frontend || overall_status=1
    echo
    
    test_monitoring || overall_status=1
    echo
    
    performance_check
    echo
    
    show_service_urls
    echo
    
    # Final status
    if [[ $overall_status -eq 0 ]]; then
        print_success "🎉 All checks passed! System is ready for use."
        echo
        print_info "Quick start:"
        echo "  1. Open http://localhost:3000 to start chatting"
        echo "  2. View API docs at http://localhost:8000/docs"
        echo "  3. Monitor with Grafana at http://localhost:3001"
        echo
        print_info "For production deployment:"
        echo "  - Update .env with production credentials"
        echo "  - Configure domain and HTTPS"
        echo "  - Set up backup schedules"
        echo "  - Review security checklist in PRODUCTION_SETUP.md"
    else
        print_error "❌ Some checks failed. Review the output above."
        echo
        print_info "Common fixes:"
        echo "  - Run: ./deploy.sh"
        echo "  - Check: ./deploy.sh logs"
        echo "  - Update: .env configuration"
        exit 1
    fi
}

main "$@"