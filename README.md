# Flask IP Geolocation Tracker

A modern Flask web application for tracking and analyzing IP addresses with geolocation data, VPN/proxy detection, and PostgreSQL database storage.

## 🚀 Features

- **IP Geolocation**: Get country, region, city, and organization information
- **VPN/Proxy Detection**: Identify VPN, proxy, and Tor connections
- **Modern UI**: Responsive design with AJAX functionality
- **PostgreSQL Database**: Robust data storage with JSON support
- **Docker Ready**: Complete containerization for easy deployment
- **Duplicate Detection**: Prevent storing duplicate IP records

## 🏗️ Architecture

- **Backend**: Flask 2.3.3 with PostgreSQL
- **Frontend**: Modern HTML/CSS/JavaScript with AJAX
- **Database**: PostgreSQL with INET and JSONB support
- **APIs**: ipinfo.io for geolocation and privacy detection
- **Deployment**: Docker with Gunicorn WSGI server

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL database (hosted or local)
- Docker (optional, for containerized deployment)

## 🔧 Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd flask-ip-tracker
```

### 2. Environment Configuration

Create a `.env` file with your database configuration:

```env
# PostgreSQL Configuration
DATABASE_URL=postgres://username:password@host:port/database

# Flask Configuration
FLASK_SECRET_KEY=your-secure-secret-key-here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

Run the database test and setup script:

```bash
python test_db.py
```

This will:
- Test the PostgreSQL connection
- Create the required tables and indexes
- Display the database schema

### 5. Data Migration (Optional)

If you have existing SQLite data to migrate:

```bash
python migrate_data.py
```

### 6. Run the Application

#### Local Development
```bash
python app.py
```

#### Docker Deployment
```bash
# Build and run manually
docker build -t flask-ip-tracker .
docker run -d -p 5000:5000 --env-file .env flask-ip-tracker
```

#### Coolify Deployment
1. Create a new project in Coolify
2. Connect your Git repository
3. Set environment variables (DATABASE_URL, FLASK_SECRET_KEY)
4. Deploy with default Dockerfile

## 🌐 Usage

1. **Access the Application**: Open `http://localhost:5000` in your browser
2. **Analyze IP**: Enter an IP address or use your current IP
3. **View Results**: See geolocation data and VPN/proxy detection
4. **Save Data**: Store IP information in the PostgreSQL database

## 📊 Database Schema

```sql
CREATE TABLE ip_records (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL UNIQUE,
    country VARCHAR(100),
    region VARCHAR(100),
    city VARCHAR(100),
    org TEXT,
    vpn_detected BOOLEAN DEFAULT FALSE,
    vpn_type VARCHAR(50),
    raw_geo_data JSONB,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

## 🔍 API Endpoints

### Web Interface
- `GET/POST /` - Main IP analysis interface

### AJAX API
- `POST /api/analyze-ip` - Analyze IP address
- `POST /api/save-ip` - Save IP to database

## 🐳 Docker Configuration

The application includes:
- **Optimized build** for production deployment
- **Non-root user** for security
- **Health checks** for monitoring
- **Environment variable** support
- **Gunicorn WSGI server** with logging

## 📈 PostgreSQL Benefits

- **Native IP Types**: INET type for efficient IP storage
- **JSON Support**: JSONB for storing complete API responses
- **Better Performance**: Optimized for concurrent reads
- **Scalability**: Handle larger datasets efficiently
- **Advanced Queries**: Complex filtering and analytics

## 🔒 Security Features

- Input validation for IP addresses
- Environment variable configuration
- Non-root Docker execution
- SQL injection prevention with parameterized queries

## 🛠️ Development

### Project Structure
```
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── .env              # Environment variables
├── .dockerignore     # Docker ignore file
├── DEPLOYMENT.md     # Deployment guide
└── README.md         # Project documentation
```

### Adding Features

The modular design allows easy extension:
- Add new API endpoints in `app.py`
- Extend database schema as needed
- Enhance frontend with additional JavaScript
- Add new geolocation providers

## 📚 Dependencies

- **Flask**: Web framework
- **psycopg2-binary**: PostgreSQL adapter
- **requests**: HTTP client for API calls
- **python-dotenv**: Environment variable management
- **gunicorn**: WSGI server for production

## 🚀 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions including:
- Docker deployment
- Environment configuration
- Scaling considerations
- Backup and recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.