# Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Production Architecture](#production-architecture)
4. [Deployment Options](#deployment-options)
5. [Environment Setup](#environment-setup)
6. [Deployment Process](#deployment-process)
7. [Monitoring & Observability](#monitoring--observability)
8. [Scaling](#scaling)
9. [Backup & Recovery](#backup--recovery)
10. [Security](#security)
11. [Maintenance](#maintenance)
12. [Troubleshooting](#troubleshooting)

## Overview

This guide covers deploying Saathy in production environments with high availability, monitoring, and security best practices.

## Prerequisites

### System Requirements

- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB+ (16GB+ recommended)
- **Storage**: 50GB+ SSD (100GB+ for production)
- **Network**: Stable internet connection
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+

### Software Requirements

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: Latest version
- **Nginx**: 1.18+ (if using reverse proxy)
- **SSL Certificate**: Let's Encrypt or commercial certificate

### External Services

- **Domain Name**: For production deployment
- **Email Service**: For notifications and alerts
- **Monitoring Service**: Optional external monitoring

## Production Architecture

### Recommended Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Load Balancer │    │   Load Balancer │
│   (Optional)    │    │   (Optional)    │    │   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Nginx Proxy   │    │   Nginx Proxy   │
│   (SSL/TLS)     │    │   (SSL/TLS)     │    │   (SSL/TLS)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Saathy API    │    │   Saathy API    │    │   Saathy API    │
│   (Container)   │    │   (Container)   │    │   (Container)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │      Qdrant Cluster     │
                    │   (Vector Database)     │
                    └─────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   Monitoring Stack      │
                    │ (Prometheus + Grafana)  │
                    └─────────────────────────┘
```

### Single Server Deployment

For smaller deployments, a single server setup is sufficient:

```
┌─────────────────────────────────────────────────────────┐
│                    Production Server                    │
├─────────────────────────────────────────────────────────┤
│  Nginx (Reverse Proxy + SSL)                           │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Saathy API    │  │   Monitoring    │              │
│  │   (Container)   │  │   (Containers)  │              │
│  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Qdrant        │  │   OpenTelemetry │              │
│  │   (Container)   │  │   Collector     │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

## Deployment Options

### 1. Docker Compose (Recommended)

Best for single-server deployments and small to medium scale.

**Advantages:**
- Simple setup and management
- Easy backup and restore
- Good for development and staging
- Minimal infrastructure requirements

**Disadvantages:**
- Limited horizontal scaling
- Single point of failure
- Manual failover

### 2. Kubernetes

Best for large-scale deployments and high availability.

**Advantages:**
- Automatic scaling and failover
- High availability
- Advanced orchestration
- Multi-cloud support

**Disadvantages:**
- Complex setup and management
- Higher resource requirements
- Steeper learning curve

### 3. Cloud Platforms

- **AWS ECS/EKS**: Amazon's container services
- **Google Cloud Run/GKE**: Google's container services
- **Azure Container Instances/AKS**: Microsoft's container services
- **DigitalOcean App Platform**: Simple container deployment

## Environment Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx (if using reverse proxy)
sudo apt install nginx -y

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Domain and SSL Setup

```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Environment Configuration

Create production environment file:

```bash
# Create production environment
cp docs/env.example .env.prod

# Edit production environment
nano .env.prod
```

**Production Environment Variables:**

```bash
# Application
APP_NAME=Saathy
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Vector Database
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your-production-qdrant-key

# Embedding Service
OPENAI_API_KEY=your-openai-api-key
DEFAULT_EMBEDDING_MODEL=text-embedding-ada-002
ENABLE_GPU_EMBEDDINGS=false
EMBEDDING_CACHE_SIZE=5000
EMBEDDING_BATCH_SIZE=64

# Connectors
GITHUB_TOKEN=your-github-token
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_REPOSITORIES=username/repo1,username/repo2
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token
SLACK_CHANNELS=C1234567890,C0987654321

# Observability
ENABLE_TRACING=true
JAEGER_HOST=jaeger
JAEGER_PORT=6831

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 4. Secrets Management

```bash
# Create secrets directory
mkdir -p secrets

# Generate secure secrets
openssl rand -hex 32 > secrets/secret_key
openssl rand -hex 32 > secrets/qdrant_api_key

# Set proper permissions
chmod 600 secrets/*
```

## Deployment Process

### 1. Initial Deployment

```bash
# Clone repository
git clone <repository-url>
cd saathy

# Set up environment
cp docs/env.example .env.prod
# Edit .env.prod with your configuration

# Create secrets
mkdir -p secrets
echo "your-qdrant-api-key" > secrets/qdrant_api_key
echo "your-openai-api-key" > secrets/openai_api_key
echo "your-grafana-password" > secrets/grafana_admin_password

# Set permissions
chmod 600 secrets/*

# Deploy with production compose
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Check deployment status
docker-compose -f docker-compose.prod.yml ps
```

### 2. Using Deployment Script

```bash
# Make script executable
chmod +x deploy.sh

# First-time deployment
./deploy.sh --init

# Regular deployment
./deploy.sh

# Deploy with specific configuration
./deploy.sh --env-file .env.prod --compose-file docker-compose.prod.yml
```

### 3. Health Check

```bash
# Check service health
curl -f http://localhost:8000/healthz

# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Nginx Configuration

Create `/etc/nginx/sites-available/saathy`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # API endpoints
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check endpoint
    location /healthz {
        access_log off;
        proxy_pass http://localhost:8000/healthz;
    }

    # Static files (if any)
    location /static/ {
        alias /var/www/saathy/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/saathy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Monitoring & Observability

### 1. Prometheus Configuration

Create `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'saathy-api'
    static_configs:
      - targets: ['saathy-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 2. Grafana Dashboards

Import the following dashboards:

- **Saathy API Dashboard**: Monitor API performance and health
- **Qdrant Dashboard**: Monitor vector database metrics
- **System Dashboard**: Monitor server resources

### 3. Alerting Rules

Create `prometheus/rules/alerts.yml`:

```yaml
groups:
  - name: saathy
    rules:
      - alert: SaathyAPIDown
        expr: up{job="saathy-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Saathy API is down"
          description: "The Saathy API has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: QdrantDown
        expr: up{job="qdrant"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Qdrant is down"
          description: "The Qdrant vector database is not responding"
```

### 4. Log Aggregation

Configure structured logging with log rotation:

```bash
# Create log directory
sudo mkdir -p /var/log/saathy
sudo chown $USER:$USER /var/log/saathy

# Configure logrotate
sudo tee /etc/logrotate.d/saathy << EOF
/var/log/saathy/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f /path/to/saathy/docker-compose.prod.yml restart saathy-api
    endscript
}
EOF
```

## Scaling

### 1. Horizontal Scaling

For Docker Compose deployments:

```bash
# Scale API instances
docker-compose -f docker-compose.prod.yml up -d --scale saathy-api=3

# Scale with load balancer
docker-compose -f docker-compose.prod.yml up -d nginx-proxy
```

### 2. Vertical Scaling

Update resource limits in `docker-compose.prod.yml`:

```yaml
services:
  saathy-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 3. Database Scaling

For Qdrant scaling:

```bash
# Set up Qdrant cluster
docker-compose -f docker-compose.prod.yml up -d qdrant-1 qdrant-2 qdrant-3

# Configure cluster in Qdrant
curl -X PUT http://localhost:6333/cluster \
  -H "Content-Type: application/json" \
  -d '{
    "peers": {
      "1": "qdrant-1:6333",
      "2": "qdrant-2:6333", 
      "3": "qdrant-3:6333"
    }
  }'
```

## Backup & Recovery

### 1. Database Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/saathy"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Qdrant data
docker exec qdrant qdrant snapshot create --collection-name documents /qdrant/backups/documents_$DATE.snapshot
docker cp qdrant:/qdrant/backups/documents_$DATE.snapshot $BACKUP_DIR/

# Backup configuration
cp .env.prod $BACKUP_DIR/env_$DATE.prod
cp -r secrets $BACKUP_DIR/secrets_$DATE

# Compress backup
tar -czf $BACKUP_DIR/saathy_backup_$DATE.tar.gz -C $BACKUP_DIR .

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "saathy_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: saathy_backup_$DATE.tar.gz"
EOF

chmod +x backup.sh
```

### 2. Automated Backups

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/saathy/backup.sh >> /var/log/saathy/backup.log 2>&1
```

### 3. Recovery Process

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore from backup
tar -xzf saathy_backup_20240101_020000.tar.gz
cp env_20240101_020000.prod .env.prod
cp -r secrets_20240101_020000/* secrets/

# Restore Qdrant data
docker cp documents_20240101_020000.snapshot qdrant:/qdrant/backups/
docker exec qdrant qdrant snapshot restore --collection-name documents /qdrant/backups/documents_20240101_020000.snapshot

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

## Security

### 1. Network Security

```bash
# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Configure fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Container Security

```yaml
# docker-compose.prod.yml
services:
  saathy-api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    user: "1000:1000"
```

### 3. Secrets Management

```bash
# Use Docker secrets (for swarm mode)
echo "your-secret" | docker secret create qdrant_api_key -

# Or use external secret management
# - HashiCorp Vault
# - AWS Secrets Manager
# - Azure Key Vault
```

### 4. SSL/TLS Configuration

```nginx
# Enhanced SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

## Maintenance

### 1. Regular Maintenance Tasks

```bash
# Weekly maintenance script
cat > maintenance.sh << 'EOF'
#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker resources
docker system prune -f

# Rotate logs
sudo logrotate /etc/logrotate.d/saathy

# Check disk space
df -h | grep -E "Use%|/$"

# Check service health
curl -f http://localhost:8000/healthz

# Backup
./backup.sh
EOF

chmod +x maintenance.sh
```

### 2. Monitoring Maintenance

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana health
curl http://localhost:3000/api/health

# Check alert manager
curl http://localhost:9093/api/v1/status
```

### 3. Performance Tuning

```bash
# Monitor resource usage
docker stats

# Check slow queries
docker logs saathy-api | grep -i "slow"

# Optimize Qdrant
curl -X POST http://localhost:6333/collections/documents/optimize
```

## Troubleshooting

### 1. Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs saathy-api

# Check resource usage
docker stats

# Check configuration
docker-compose -f docker-compose.prod.yml config
```

#### Database Connection Issues

```bash
# Check Qdrant status
curl http://localhost:6333/collections

# Check network connectivity
docker exec saathy-api ping qdrant

# Check environment variables
docker exec saathy-api env | grep QDRANT
```

#### Performance Issues

```bash
# Check resource usage
htop
docker stats

# Check slow queries
docker logs saathy-api | grep -i "timeout\|slow"

# Check memory usage
free -h
```

### 2. Debug Commands

```bash
# Enter container for debugging
docker exec -it saathy-api bash

# Check application logs
docker logs -f saathy-api

# Check all container logs
docker-compose -f docker-compose.prod.yml logs -f

# Check network
docker network ls
docker network inspect saathy_default
```

### 3. Emergency Procedures

#### Service Recovery

```bash
# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart saathy-api

# Force recreate containers
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

#### Data Recovery

```bash
# Check backup availability
ls -la /backups/saathy/

# Restore from latest backup
./restore.sh latest

# Verify data integrity
curl http://localhost:8000/healthz
```

### 4. Support and Resources

- **Documentation**: Check the `docs/` directory
- **Issues**: Open an issue on GitHub
- **Logs**: Check application and system logs
- **Monitoring**: Use Grafana dashboards for insights

This deployment guide provides comprehensive instructions for deploying Saathy in production environments. Always test deployment procedures in a staging environment before applying to production.