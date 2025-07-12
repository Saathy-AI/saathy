# VPS Setup Guide for Saathy

This guide covers the complete setup of a VPS for running Saathy in production.

## Prerequisites

- Ubuntu 20.04+ VPS
- Root or sudo access
- Domain name (optional, for HTTPS)
- SSH key access configured

## Initial Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw fail2ban
```

### 2. Create Non-Root User

```bash
# Create user (replace 'saathy' with your preferred username)
sudo adduser saathy
sudo usermod -aG sudo saathy

# Switch to new user
su - saathy
```

### 3. Configure SSH Security

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Add/modify these lines:
Port 2222  # Change default port
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

```bash
# Restart SSH service
sudo systemctl restart sshd

# Test SSH connection before closing current session
ssh -p 2222 saathy@your-server-ip
```

### 4. Configure Firewall

```bash
# Enable UFW
sudo ufw enable

# Allow SSH (use your custom port)
sudo ufw allow 2222/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### 5. Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
exit
# SSH back in
```

### 6. Clone Saathy Repository

```bash
# Clone the repository
git clone https://github.com/your-username/saathy.git
cd saathy

# Make scripts executable
chmod +x deploy.sh scripts/*.sh
```

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install -y certbot

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Create symbolic links for nginx
sudo mkdir -p nginx/ssl
sudo ln -s /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo ln -s /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# Set up auto-renewal
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 2: Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate
sudo mkdir -p nginx/ssl
cd nginx/ssl

sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout key.pem -out cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

cd ../..
```

## Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env

# Required variables to set:
# - OPENAI_API_KEY=your_openai_api_key
# - SSL_DOMAIN=your-domain.com (if using Let's Encrypt)
```

## Initial Deployment

```bash
# Run initial setup and deployment
./deploy.sh --init

# Check deployment status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check application health
curl -f http://localhost/healthz

# Check container health
docker-compose -f docker-compose.prod.yml ps
```

### Logs

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f saathy-api

# View nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx

# View system logs
sudo journalctl -u docker.service -f
```

### Backups

```bash
# Create backup
./scripts/backup.sh

# List backups
./scripts/backup.sh --help

# Restore from backup
./scripts/restore.sh qdrant-backup-20241207-143022.tar.gz
```

### Updates

```bash
# Regular deployment
./deploy.sh

# Dry run (test without making changes)
./deploy.sh --dry-run

# Rollback if needed
./deploy.sh --rollback
```

## Security Hardening

### 1. Fail2ban Configuration

```bash
# Configure fail2ban for SSH
sudo nano /etc/fail2ban/jail.local

# Add:
[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
```

```bash
# Restart fail2ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### 2. Regular Security Updates

```bash
# Set up automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Monitor System Resources

```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Check disk usage
df -h

# Check memory usage
free -h

# Check running processes
htop
```

## Troubleshooting

### Common Issues

1. **Port 80/443 already in use**
   ```bash
   sudo netstat -tlnp | grep :80
   sudo systemctl stop apache2  # if Apache is running
   ```

2. **SSL certificate issues**
   ```bash
   # Check certificate validity
   openssl x509 -in nginx/ssl/cert.pem -text -noout
   
   # Test nginx configuration
   docker exec saathy-nginx-1 nginx -t
   ```

3. **Container won't start**
   ```bash
   # Check container logs
   docker-compose -f docker-compose.prod.yml logs saathy-api
   
   # Check disk space
   df -h
   
   # Check Docker daemon
   sudo systemctl status docker
   ```

4. **Health check failures**
   ```bash
   # Check if containers are running
   docker ps
   
   # Check internal connectivity
   docker exec saathy-nginx-1 curl -f http://saathy-api:8000/healthz
   ```

### Performance Tuning

1. **Increase file descriptors**
   ```bash
   # Edit limits
   sudo nano /etc/security/limits.conf
   
   # Add:
   * soft nofile 65536
   * hard nofile 65536
   ```

2. **Optimize Docker storage**
   ```bash
   # Check Docker storage driver
   docker info | grep "Storage Driver"
   
   # Clean up unused resources
   docker system prune -a
   ```

## Backup Strategy

### Automated Backups

```bash
# Set up cron job for daily backups
crontab -e

# Add this line for daily backups at 2 AM:
0 2 * * * /home/saathy/saathy/scripts/backup.sh
```

### Backup Verification

```bash
# Test backup restoration
./scripts/restore.sh --force qdrant-backup-YYYYMMDD-HHMMSS.tar.gz
```

## Support

For issues and questions:

1. Check the logs: `docker-compose -f docker-compose.prod.yml logs`
2. Verify configuration: `docker-compose -f docker-compose.prod.yml config`
3. Check system resources: `htop`, `df -h`, `free -h`
4. Review this guide for common solutions
5. Open an issue on GitHub with detailed error information 