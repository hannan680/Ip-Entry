# Coolify Deployment Instructions

## Quick Setup Guide for Coolify

### 1. Prerequisites
- Coolify instance running
- PostgreSQL database ready
- Git repository with this code

### 2. Environment Variables Required
Set these in your Coolify project:

```env
DATABASE_URL=postgres://username:password@host:port/database
FLASK_SECRET_KEY=your-secure-secret-key-here
```

### 3. Coolify Configuration
- **Build Pack**: Dockerfile
- **Port**: 5005
- **Health Check**: Enabled (built into Dockerfile)
- **Auto Deploy**: Recommended for continuous deployment

### 4. Deployment Steps
1. Create new project in Coolify
2. Connect your Git repository
3. Set environment variables above
4. Configure port to 5000
5. Deploy!

### 5. Post-Deployment
- Check logs for any errors
- Test the application at your assigned URL
- Monitor health checks in Coolify dashboard

### 6. Database Setup
The application will automatically:
- Create required tables on first run
- Set up indexes for optimal performance
- Handle database migrations

### 7. Scaling
- Adjust worker count in Dockerfile if needed
- Monitor resource usage in Coolify
- Scale horizontally by adding more instances

## Troubleshooting

### Common Issues
1. **Database Connection**: Verify DATABASE_URL format and accessibility
2. **Port Issues**: Ensure port 5000 is configured in Coolify
3. **Environment Variables**: Double-check all required variables are set

### Support
- Check application logs in Coolify dashboard
- Verify database connectivity
- Monitor health check status