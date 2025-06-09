# Flask IP Tracker - Deployment Guide

This guide provides instructions for deploying the Flask IP Geolocation Tracker using Coolify with PostgreSQL database.

## Prerequisites

- Coolify instance set up
- PostgreSQL database (hosted)
- Git repository with your code

## Coolify Deployment

1. **Create a new project in Coolify**
2. **Connect your Git repository**
3. **Configure environment variables:**
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `FLASK_SECRET_KEY`: Secure secret key for Flask sessions
4. **Deploy the application**

## Manual Docker Deployment (Local Testing)

### Build the Docker Image

```bash
docker build -t flask-ip-tracker .
```

### Run the Container

```bash
docker run -d \
  --name flask-ip-tracker \
  -p 5000:5000 \
  --env-file .env \
  flask-ip-tracker
```

## Production Deployment with Coolify

### Environment Variables

The application supports the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string (required)
- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- `FLASK_ENV`: Set to `production` for production deployment
- `FLASK_APP`: Application entry point (default: `app.py`)

Example `.env` file:
```env
DATABASE_URL=postgres://username:password@host:port/database
FLASK_SECRET_KEY=your-secure-secret-key-here
```

### Security Considerations

1. **Change the secret key** in `app.py` for production:
   ```python
   app.secret_key = 'your-secure-random-secret-key-here'
   ```

2. **Use HTTPS** in production with a reverse proxy (nginx, Apache, etc.)

3. **Database connection**: The application connects to an external PostgreSQL database. Ensure your DATABASE_URL is properly configured.

### Coolify Configuration

1. **Repository Settings:**
   - Set build context to root directory
   - Dockerfile path: `./Dockerfile`
   - Port: `5000`

2. **Environment Variables:**
   ```
   DATABASE_URL=your_postgresql_connection_string
   FLASK_SECRET_KEY=your_secure_secret_key
   ```

3. **Health Checks:**
   The Docker image includes health checks that verify the application is responding on port 5000.

## Monitoring

### Container Logs

```bash
# View logs in Coolify dashboard or via Docker
docker logs -f flask-ip-tracker
```

### Application Health

The application includes a health check endpoint. You can verify it's running:

```bash
curl http://your-app-url/
```

## Troubleshooting

### Common Issues

1. **Database connection errors**: Verify DATABASE_URL is correct and accessible
2. **Environment variables**: Ensure all required environment variables are set in Coolify
3. **Port configuration**: Application runs on port 5000 by default

### Debug Mode

For local debugging, you can run the container with debug output:

```bash
docker run -it --rm \
  -p 5000:5000 \
  --env-file .env \
  flask-ip-tracker \
  python app.py
```

## Performance Tuning

### Gunicorn Configuration

The production deployment uses Gunicorn with the following settings:
- 2 worker processes (optimized for Coolify)
- 120-second timeout
- Binding to all interfaces (0.0.0.0:5000)
- Access and error logging enabled

To modify these settings, update the CMD in the Dockerfile:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "app:app"]
```

### Resource Limits

Resource limits can be configured in Coolify's dashboard under the application settings.

## Backup and Recovery

### Database Backup

```bash
# Create PostgreSQL backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Or using Docker if pg_dump is not available locally
docker run --rm postgres:15 pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Database Restore

```bash
# Restore PostgreSQL backup
psql $DATABASE_URL < backup.sql

# Or using Docker
docker run --rm -i postgres:15 psql $DATABASE_URL < backup.sql
```

## Updates

To update the application in Coolify:

1. **Push new code to your Git repository**
2. **Trigger a new deployment in Coolify dashboard**
3. **Or enable auto-deployment for automatic updates**

## Support

For issues and questions, check the application logs and ensure all dependencies are properly installed.