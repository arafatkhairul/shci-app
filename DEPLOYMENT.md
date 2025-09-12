# 🚀 SHCI Voice Assistant - Ubuntu VPS Deployment Guide

This guide will help you deploy the complete SHCI Voice Assistant application to an Ubuntu VPS with Nginx reverse proxy, Docker containers, and SSL certificates.

## 📋 Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04 LTS or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: Minimum 20GB SSD
- **CPU**: 2+ cores
- **Network**: Public IP with domain name pointing to server

### Domain Setup
- Domain name (e.g., `your-domain.com`)
- DNS A record pointing to your server's IP
- Email address for SSL certificate

## 🛠️ Quick Deployment

### Option 1: Automated Deployment Script

1. **Clone the repository on your VPS:**
   ```bash
   git clone https://github.com/arafatkhairul/shci-app.git
   cd shci-app
   ```

2. **Edit the deployment script:**
   ```bash
   nano deploy.sh
   ```
   Update these variables:
   ```bash
   DOMAIN_NAME="nodecel.cloud"  # Your actual domain
   EMAIL="office.khairul@gmail.com"  # Your email for SSL
   ```

3. **Run the deployment script:**
   ```bash
   ./deploy.sh
   ```

The script will automatically:
- Install Docker and Docker Compose
- Configure Nginx reverse proxy
- Set up SSL certificates
- Deploy all services
- Configure firewall
- Set up auto-start service

### Option 2: Manual Deployment

#### Step 1: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl wget git nginx certbot python3-certbot-nginx ufw

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Step 2: Configure Firewall

```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

#### Step 3: Deploy Application

```bash
# Clone repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Update domain in configuration
sed -i "s/your-domain.com/your-actual-domain.com/g" nginx/conf.d/shci.conf

# Build and start services
docker-compose up -d --build
```

#### Step 4: Setup SSL Certificate

```bash
# Stop nginx container temporarily
docker-compose stop nginx

# Install SSL certificate
sudo certbot --nginx -d nodecel.cloud -d www.nodecel.cloud --email office.khairul@gmail.com --agree-tos --non-interactive

# Restart nginx
docker-compose up -d nginx
```

## 🏗️ Architecture Overview

```
Internet → Nginx (Port 80/443) → Docker Containers
                                    ├── Frontend (Next.js :3000)
                                    ├── Backend (FastAPI :8000)
                                    └── Database (SQLite)
```

### Services

1. **Frontend (Next.js)**
   - Port: 3000 (internal)
   - Serves the voice interface
   - Handles WebSocket connections

2. **Backend (FastAPI)**
   - Port: 8000 (internal)
   - API endpoints (`/api/`)
   - WebSocket server (`/ws`)
   - TTS/STT processing

3. **Nginx (Reverse Proxy)**
   - Port: 80 (HTTP)
   - Port: 443 (HTTPS)
   - SSL termination
   - Load balancing
   - Rate limiting

## 🔧 Configuration Files

### Environment Variables

Update these files with your domain:

- `env.production` - Production environment variables
- `nginx/conf.d/shci.conf` - Nginx configuration
- `docker-compose.yml` - Container orchestration

### Key Configuration Points

1. **Domain Configuration:**
   ```bash
   # In nginx/conf.d/shci.conf
   server_name your-domain.com www.your-domain.com;
   ```

2. **Environment Variables:**
   ```bash
   # In env.production
   NEXT_PUBLIC_API_BASE_URL=https://your-domain.com
   NEXT_PUBLIC_WS_BASE_URL=wss://your-domain.com
   ```

3. **SSL Configuration:**
   ```bash
   # SSL certificates will be automatically configured
   ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
   ```

## 📊 Monitoring & Management

### Service Management

```bash
# View all services
docker-compose ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Start services
docker-compose up -d

# Update application
git pull origin main
docker-compose up -d --build
```

### Health Checks

```bash
# Check backend health
curl https://your-domain.com/health

# Check frontend
curl https://your-domain.com

# Check WebSocket
wscat -c wss://your-domain.com/ws
```

### Log Monitoring

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

## 🔒 Security Configuration

### Firewall Rules

```bash
# Check firewall status
sudo ufw status

# Allow specific ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
```

### SSL Security

The deployment automatically configures:
- TLS 1.2 and 1.3
- Strong cipher suites
- HSTS headers
- Security headers

### Rate Limiting

Nginx is configured with:
- API rate limiting: 10 requests/second
- WebSocket rate limiting: 5 requests/second
- Burst handling for temporary spikes

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting:**
   ```bash
   docker-compose logs -f
   # Check for port conflicts or missing dependencies
   ```

2. **SSL certificate issues:**
   ```bash
   sudo certbot certificates
   sudo certbot renew --dry-run
   ```

3. **Domain not resolving:**
   ```bash
   nslookup your-domain.com
   dig your-domain.com
   ```

4. **Firewall blocking connections:**
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

### Performance Optimization

1. **Increase worker processes:**
   ```bash
   # In nginx/nginx.conf
   worker_processes auto;
   ```

2. **Enable caching:**
   ```bash
   # Static files are automatically cached
   # API responses can be cached based on requirements
   ```

3. **Monitor resources:**
   ```bash
   docker stats
   htop
   ```

## 📈 Scaling & Updates

### Horizontal Scaling

```bash
# Scale backend services
docker-compose up -d --scale backend=3

# Update nginx upstream configuration
# Add multiple backend instances
```

### Application Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Zero-downtime deployment (with multiple instances)
docker-compose up -d --scale backend=2
docker-compose restart nginx
```

### Backup Strategy

```bash
# Backup database
docker-compose exec backend cp /app/roleplay.db /app/backup/roleplay-$(date +%Y%m%d).db

# Backup configuration
tar -czf shci-backup-$(date +%Y%m%d).tar.gz nginx/ docker-compose.yml env.production
```

## 🎯 Production Checklist

- [ ] Domain DNS configured
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Services running
- [ ] Health checks passing
- [ ] Logs monitoring setup
- [ ] Backup strategy implemented
- [ ] Performance monitoring configured
- [ ] Security headers verified
- [ ] Rate limiting tested

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Verify configuration files
3. Test individual services
4. Check network connectivity
5. Review firewall settings

## 🎉 Success!

Once deployed, your SHCI Voice Assistant will be available at:
- **Frontend**: https://your-domain.com
- **API**: https://your-domain.com/api/
- **WebSocket**: wss://your-domain.com/ws
- **Health Check**: https://your-domain.com/health

The application is now ready for production use with:
- ✅ Automatic SSL certificates
- ✅ Reverse proxy with Nginx
- ✅ Docker containerization
- ✅ Auto-start on boot
- ✅ Security headers
- ✅ Rate limiting
- ✅ Health monitoring
