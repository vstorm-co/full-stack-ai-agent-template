# Deployment Guide

This guide covers deploying your generated FastAPI project to production.

## Overview

The generated project supports multiple deployment options:

- **Docker Compose** - Simple single-server deployment
- **Kubernetes** - Production-grade orchestration
- **Cloud Platforms** - AWS, GCP, Azure, etc.

---

## Prerequisites

Before deploying, ensure you have:

1. **Docker** installed on your deployment server
2. **Domain name** configured (optional but recommended)
3. **SSL certificate** (Let's Encrypt recommended)
4. **Environment variables** prepared for production

---

## Environment Variables

### Required for Production

```bash
# Core
ENVIRONMENT=production
DEBUG=false

# Security - MUST be changed!
SECRET_KEY=your-secure-secret-key-at-least-32-characters
API_KEY=your-secure-api-key

# Database
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-secure-db-password
POSTGRES_DB=your-db-name

# Redis (if enabled)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Logfire
LOGFIRE_TOKEN=your-logfire-token
LOGFIRE_ENVIRONMENT=production

# AI Agent (if enabled)
OPENAI_API_KEY=sk-your-key
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate API_KEY
openssl rand -hex 32

# Generate database password
openssl rand -base64 24
```

---

## Docker Compose Deployment

### Production Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=production
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - SECRET_KEY=${SECRET_KEY}
      - LOGFIRE_TOKEN=${LOGFIRE_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - BACKEND_URL=http://backend:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Deployment Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/your-project.git
   cd your-project
   ```

2. **Configure `backend/.env`**
   ```bash
   cp backend/.env.example backend/.env
   # Edit with real production values (the same file is used for dev and prod)
   ```

3. **Build and start services**
   ```bash
   make prod
   # equivalent to:
   # docker compose --env-file backend/.env -f docker-compose.prod.yml up -d --build
   ```

4. **Run database migrations**
   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

5. **Create admin user**
   ```bash
   docker compose -f docker-compose.prod.yml exec backend \
     python -m cli.commands user create-admin \
     --email admin@example.com
   ```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (GKE, EKS, AKS, or self-managed)
- `kubectl` configured
- Container registry access

### Manifest Files

The generated project includes Kubernetes manifests in `k8s/`:

```
k8s/
├── namespace.yaml
├── configmap.yaml
├── secret.yaml
├── backend/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── frontend/
│   ├── deployment.yaml
│   └── service.yaml
├── database/
│   ├── statefulset.yaml
│   └── service.yaml
└── ingress.yaml
```

### Deployment Steps

1. **Create namespace**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **Create secrets**
   ```bash
   kubectl create secret generic app-secrets \
     --from-literal=secret-key=$(openssl rand -hex 32) \
     --from-literal=postgres-password=$(openssl rand -base64 24) \
     --from-literal=redis-password=$(openssl rand -base64 24) \
     -n your-namespace
   ```

3. **Apply configurations**
   ```bash
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/database/
   kubectl apply -f k8s/backend/
   kubectl apply -f k8s/frontend/
   kubectl apply -f k8s/ingress.yaml
   ```

4. **Run migrations**
   ```bash
   kubectl exec -it deploy/backend -n your-namespace -- alembic upgrade head
   ```

### Backend Deployment

```yaml
# k8s/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: your-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: your-registry/backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /api/v1/health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

### Horizontal Pod Autoscaler

```yaml
# k8s/backend/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: your-namespace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## Reverse Proxy (Nginx)

### Configuration

```nginx
# /etc/nginx/sites-available/your-project
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # API routes
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support. Must cover the whole /api/v1/ws prefix — a request that
    # falls through to `location /api` above is proxied without the Upgrade
    # headers and the handshake fails.
    location /api/v1/ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # API docs
    location /docs {
        proxy_pass http://backend;
    }

    location /redoc {
        proxy_pass http://backend;
    }

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Database Migrations

### Running Migrations

```bash
# Docker Compose
docker compose exec backend alembic upgrade head

# Kubernetes
kubectl exec -it deploy/backend -- alembic upgrade head

# Direct
cd backend && alembic upgrade head
```

### Creating Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Monitoring

### Logfire

The application is instrumented with Logfire for:

- **Traces** - Request flows and latencies
- **Logs** - Structured application logs
- **Metrics** - Custom metrics and counters

Access the dashboard at [logfire.pydantic.dev](https://logfire.pydantic.dev).

### Health Checks

```bash
# Liveness (is the app running?)
curl https://your-domain.com/api/v1/health

# Readiness (is the app ready to serve?)
curl https://your-domain.com/api/v1/health/ready
```

### Prometheus (if enabled)

Metrics available at `/metrics`:

```bash
curl https://your-domain.com/metrics
```

Configure Prometheus scraping:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['backend:8000']
```

---

## SSL/TLS

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (cron)
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup
docker compose exec db pg_dump -U postgres your_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U postgres your_db < backup.sql
```

### Automated Backups

```bash
# /etc/cron.daily/backup-db
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d)

docker compose exec db pg_dump -U postgres your_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
```

---

## Security Checklist

- [ ] Change `SECRET_KEY` and `API_KEY`
- [ ] Use strong database passwords
- [ ] Enable SSL/TLS everywhere
- [ ] Configure CORS for production domains only
- [ ] Disable debug mode (`DEBUG=false`)
- [ ] Hide API docs in production (automatic when `ENVIRONMENT=production`)
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure Sentry for error tracking
- [ ] Set up log aggregation
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor with Logfire

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend

# Check health
docker compose ps
```

### Database connection issues

```bash
# Verify database is running
docker compose exec db pg_isready

# Check connection string
docker compose exec backend python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### Migration errors

```bash
# Check current version
alembic current

# Check history
alembic history

# Create fresh migration
alembic revision --autogenerate -m "Description"
```
