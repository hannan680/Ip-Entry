# Flask IP Tracker - Deployment Guide

This guide provides instructions for deploying the Flask IP Geolocation Tracker using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier management)

## Quick Start with Docker Compose

1. **Clone or download the project files**
2. **Build and run the application:**
   ```bash
   docker-compose up -d
   ```
3. **Access the application:**
   - Open your browser and navigate to `http://localhost:8000`

## Manual Docker Deployment

### Build the Docker Image

```bash
docker build -t flask-ip-tracker .
```

### Run the Container

```bash
docker run -d \
  --name flask-ip-tracker \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  flask-ip-tracker
```

## Production Deployment

### Environment Variables

The application supports the following environment variables:

- `FLASK_ENV`: Set to `production` for production deployment
- `FLASK_APP`: Application entry point (default: `app.py`)

### Security Considerations

1. **Change the secret key** in `app.py` for production:
   ```python
   app.secret_key = 'your-secure-random-secret-key-here'
   ```

2. **Use HTTPS** in production with a reverse proxy (nginx, Apache, etc.)

3. **Database persistence**: The SQLite database is stored in the `/app/data` directory inside the container. Mount this as a volume for data persistence.

### Scaling with Docker Swarm

For high-availability deployment:

```bash
docker service create \
  --name flask-ip-tracker \
  --replicas 3 \
  --publish 8000:8000 \
  --mount type=volume,source=ip-tracker-data,target=/app/data \
  flask-ip-tracker
```

### Health Checks

The Docker image includes health checks that verify the application is responding on port 8000.

## Monitoring

### Container Logs

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f flask-ip-tracker
```

### Application Health

The application includes a health check endpoint. You can verify it's running:

```bash
curl http://localhost:8000/
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port mapping in docker-compose.yml or docker run command
2. **Permission issues**: Ensure the data directory has proper permissions
3. **Database errors**: Check that the data volume is properly mounted

### Debug Mode

For debugging, you can run the container with debug output:

```bash
docker run -it --rm \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  flask-ip-tracker \
  python app.py
```

## Performance Tuning

### Gunicorn Configuration

The production deployment uses Gunicorn with the following settings:
- 4 worker processes
- 120-second timeout
- Binding to all interfaces (0.0.0.0:8000)

To modify these settings, update the CMD in the Dockerfile:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "8", "--timeout", "60", "app:app"]
```

### Resource Limits

For production, consider setting resource limits:

```yaml
# docker-compose.yml
services:
  ip-tracker:
    # ... other settings
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

## Backup and Recovery

### Database Backup

```bash
# Copy database from running container
docker cp flask-ip-tracker:/app/data/ip_tracker.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

### Database Restore

```bash
# Copy database to running container
docker cp ./backup.db flask-ip-tracker:/app/data/ip_tracker.db
docker restart flask-ip-tracker
```

## Updates

To update the application:

1. **Pull new code**
2. **Rebuild the image:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Support

For issues and questions, check the application logs and ensure all dependencies are properly installed.