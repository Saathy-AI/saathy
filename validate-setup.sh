#!/bin/bash

# Saathy Infrastructure Migration Validation Script
# This script validates the migration from Ansible to Docker Compose

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_file() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} $description - File not found: $file"
        ((TESTS_FAILED++))
    fi
}

# Test executable function
test_executable() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" && -x "$file" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} $description - File not found or not executable: $file"
        ((TESTS_FAILED++))
    fi
}

# Test content function
test_content() {
    local file="$1"
    local pattern="$2"
    local description="$3"
    
    if [[ -f "$file" && grep -q "$pattern" "$file" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} $description - Pattern not found in $file"
        ((TESTS_FAILED++))
    fi
}

# Test absence function
test_absence() {
    local file="$1"
    local description="$2"
    
    if [[ ! -f "$file" && ! -d "$file" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} $description - File/directory still exists: $file"
        ((TESTS_FAILED++))
    fi
}

echo "🔍 Validating Saathy Infrastructure Migration"
echo "============================================="
echo ""

# Phase 1: Ansible Removal Tests
echo "📋 Phase 1: Ansible Infrastructure Removal"
echo "-------------------------------------------"
test_absence "infra/playbook.yml" "Ansible playbook removed"
test_absence "infra/inventory.ini" "Ansible inventory removed"
test_absence "infra/" "Ansible directory removed"
echo ""

# Phase 2: Production Docker Compose Tests
echo "🐳 Phase 2: Production Docker Compose Setup"
echo "-------------------------------------------"
test_file "docker-compose.prod.yml" "Production Docker Compose file created"
test_content "docker-compose.prod.yml" "saathy-api" "Saathy API service defined"
test_content "docker-compose.prod.yml" "qdrant" "Qdrant service defined"
test_content "docker-compose.prod.yml" "nginx" "Nginx service defined"
test_content "docker-compose.prod.yml" "restart: unless-stopped" "Restart policy configured"
test_content "docker-compose.prod.yml" "healthcheck" "Health checks configured"
test_content "docker-compose.prod.yml" "user: \"1000:1000\"" "Non-root user configured"
test_content "docker-compose.prod.yml" "qdrant_data" "Named volumes configured"
echo ""

# Phase 3: Nginx Configuration Tests
echo "🌐 Phase 3: Nginx Reverse Proxy Configuration"
echo "---------------------------------------------"
test_file "nginx/nginx.conf" "Nginx configuration file created"
test_content "nginx/nginx.conf" "upstream saathy_backend" "Upstream backend configured"
test_content "nginx/nginx.conf" "ssl_certificate" "SSL configuration present"
test_content "nginx/nginx.conf" "X-Frame-Options" "Security headers configured"
test_content "nginx/nginx.conf" "limit_req_zone" "Rate limiting configured"
test_content "nginx/nginx.conf" "gzip on" "Gzip compression enabled"
test_content "nginx/nginx.conf" "/healthz" "Health check endpoint configured"
test_file "nginx/ssl/.gitkeep" "SSL directory created"
echo ""

# Phase 4: Deployment Script Tests
echo "🚀 Phase 4: Production Deployment Script"
echo "----------------------------------------"
test_executable "deploy.sh" "Deployment script created and executable"
test_content "deploy.sh" "git pull" "Git pull functionality"
test_content "deploy.sh" "docker-compose.*build.*--no-cache" "Docker build with no-cache"
test_content "deploy.sh" "health_check" "Health check functionality"
test_content "deploy.sh" "rollback" "Rollback capability"
test_content "deploy.sh" "log.*timestamp" "Logging with timestamps"
test_content "deploy.sh" "set -e" "Error handling configured"
test_content "deploy.sh" "docker image prune" "Cleanup functionality"
test_content "deploy.sh" "--init" "Initial setup mode"
test_content "deploy.sh" "--dry-run" "Dry run mode"
test_content "deploy.sh" "--rollback" "Rollback mode"
echo ""

# Phase 5: Environment and Backup Management Tests
echo "💾 Phase 5: Environment and Backup Management"
echo "---------------------------------------------"
test_file ".env.example" "Environment example file created"
test_executable "scripts/backup.sh" "Backup script created and executable"
test_executable "scripts/restore.sh" "Restore script created and executable"
test_content "scripts/backup.sh" "QDRANT_CONTAINER" "Qdrant container backup"
test_content "scripts/backup.sh" "tar.*-czf" "Compression functionality"
test_content "scripts/backup.sh" "cleanup_old_backups" "Backup retention"
test_content "scripts/restore.sh" "validate_backup" "Backup validation"
test_content "scripts/restore.sh" "confirm_restore" "Restore confirmation"
test_content "scripts/restore.sh" "--force" "Force restore option"
echo ""

# Phase 6: Documentation Tests
echo "📚 Phase 6: Documentation Updates"
echo "---------------------------------"
test_file "docs/vps-setup.md" "VPS setup documentation created"
test_content "docs/vps-setup.md" "Ubuntu 20.04" "VPS requirements documented"
test_content "docs/vps-setup.md" "Docker.*install" "Docker installation documented"
test_content "docs/vps-setup.md" "SSL.*certificate" "SSL setup documented"
test_content "docs/vps-setup.md" "firewall" "Firewall configuration documented"
test_content "docs/vps-setup.md" "backup" "Backup procedures documented"
test_content "docs/vps-setup.md" "troubleshooting" "Troubleshooting section"
test_content "README.md" "Quick Deploy" "README updated with quick deploy"
test_content "README.md" "3-Step Deployment" "3-step deployment process documented"
test_content "README.md" "Monitoring and Maintenance" "Maintenance section added"
test_content "README.md" "docs/vps-setup.md" "VPS setup guide linked"
echo ""

# Security Tests
echo "🔒 Security Configuration Tests"
echo "-------------------------------"
test_content "docker-compose.prod.yml" "user: \"1000:1000\"" "Non-root containers"
test_content "nginx/nginx.conf" "X-Frame-Options.*SAMEORIGIN" "X-Frame-Options header"
test_content "nginx/nginx.conf" "X-Content-Type-Options.*nosniff" "X-Content-Type-Options header"
test_content "nginx/nginx.conf" "X-XSS-Protection" "X-XSS-Protection header"
test_content "nginx/nginx.conf" "limit_req_zone.*100r/m" "Rate limiting configured"
test_content "nginx/nginx.conf" "ssl_protocols.*TLSv1.2.*TLSv1.3" "Strong SSL protocols"
test_content "deploy.sh" "check_root" "Root execution prevention"
echo ""

# Summary
echo "📊 Validation Summary"
echo "===================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 All tests passed! Infrastructure migration completed successfully.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Copy .env.example to .env and configure your environment variables"
    echo "2. Follow the VPS setup guide: docs/vps-setup.md"
    echo "3. Run: ./deploy.sh --init"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the issues above.${NC}"
    exit 1
fi 