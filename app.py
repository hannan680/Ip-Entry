from flask import Flask, request, render_template_string, redirect, url_for, flash, jsonify
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
import re
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import logging

# Logging configuration for testing
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app_test.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ip-tracker-2024-secure-key-f8d9a7b3c1e5')  # Used for flash messages

def get_country_flag(country_code):
    """Convert country code to flag emoji"""
    if not country_code or len(country_code) != 2:
        return "🌍"
    
    # Convert country code to flag emoji
    flag = "".join(chr(ord(c) + 127397) for c in country_code.upper())
    return flag

def validate_ip(ip):
    """Validate IP address format"""
    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(pattern, ip) is not None

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
IPAPI_TOKEN = os.getenv('IPAPI_TOKEN')

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    """Initialize PostgreSQL database with required tables"""
    logger.info("Initializing database and ensuring required tables exist.")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_records (
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
            )
        ''')
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_address ON ip_records(ip_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON ip_records(country)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON ip_records(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vpn_detected ON ip_records(vpn_detected)')
        conn.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()

def is_ip_in_database(ip):
    """Check if IP exists in PostgreSQL database"""
    logger.debug(f"Checking if IP {ip} exists in database.")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM ip_records WHERE ip_address = %s', (ip,))
    result = cursor.fetchone()
    count = result['count'] if result else 0
    conn.close()
    logger.debug(f"IP {ip} exists: {count > 0}")
    return count > 0

def save_ip_to_database(ip_data):
    """Save IP data to PostgreSQL database"""
    logger.info(f"Saving IP data to database: {ip_data['ip']}")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO ip_records
            (ip_address, country, region, city, org, vpn_detected, vpn_type, raw_geo_data, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (ip_address) DO UPDATE SET
                country = EXCLUDED.country,
                region = EXCLUDED.region,
                city = EXCLUDED.city,
                org = EXCLUDED.org,
                vpn_detected = EXCLUDED.vpn_detected,
                vpn_type = EXCLUDED.vpn_type,
                raw_geo_data = EXCLUDED.raw_geo_data,
                timestamp = CURRENT_TIMESTAMP
        ''', (
            ip_data['ip'],
            ip_data['location']['country'],
            ip_data['location']['region'],
            ip_data['location']['city'],
            ip_data['location']['org'],
            ip_data['vpn_detected'],
            ip_data['vpn_type'],
            json.dumps(ip_data)  # Store complete data as JSON
        ))
        conn.commit()
        logger.info(f"IP {ip_data['ip']} saved/updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Error saving IP {ip_data['ip']} to database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# Initialize database on startup
init_db()

def get_user_ip():
    """Get the user's actual IP address"""
    # Check X-Forwarded-For header for real client IP (if behind proxy)
    x_forwarded_for = request.headers.get('X-Forwarded-For', '')
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs, take the first one
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.remote_addr

    # If testing locally, override with external IP (for demo only)
    if ip == '127.0.0.1':
        try:
            ip = requests.get("https://api.ipify.org", timeout=5).text
        except:
            pass  # Keep localhost if external IP fetch fails
    
    return ip

def get_ip_info(custom_ip=None):
    # Use custom IP if provided, otherwise get user's IP
    if custom_ip:
        if not validate_ip(custom_ip):
            logger.warning(f"Invalid IP address format received: {custom_ip}")
            return {
                "error": "Invalid IP address format",
                "ip": custom_ip
            }
        ip = custom_ip
    else:
        ip = get_user_ip()

    try:
        # Geolocation lookup using ipinfo.io lite endpoint with optional token
        geo_url = f"https://api.ipinfo.io/lite/{ip}"
        if IPAPI_TOKEN:
            geo_url += f"?token={IPAPI_TOKEN}"
        logger.debug(f"Requesting geolocation for IP: {ip} from ipinfo.io lite: {geo_url}")
        geo_data = requests.get(geo_url, timeout=5).json()
        logger.debug(f"Geo data: {geo_data}")
    except Exception as e:
        logger.error(f"Error fetching geolocation info for IP {ip}: {e}")
        # Fallback data if API fails
        geo_data = {
            "ip": ip,
            "asn": "Unknown",
            "as_name": "Unknown",
            "as_domain": "Unknown",
            "country_code": "",
            "country": "Unknown",
            "continent_code": "",
            "continent": "Unknown"
        }

    # Check if IP exists in database
    status = "duplicate" if is_ip_in_database(ip) else "new"
    logger.info(f"IP {ip} status: {status}")
    
    # Get country code and flag
    country_code = geo_data.get("country_code", "")
    country_flag = get_country_flag(country_code)

    return {
        "status": status,
        "ip": geo_data.get("ip", ip),
        "location": {
            "country": geo_data.get("country", "Unknown"),
            "country_code": country_code,
            "country_flag": country_flag,
            "continent": geo_data.get("continent", "Unknown"),
            "continent_code": geo_data.get("continent_code", ""),
            "asn": geo_data.get("asn", "Unknown"),
            "as_name": geo_data.get("as_name", "Unknown"),
            "as_domain": geo_data.get("as_domain", "Unknown")
        },
        "vpn_detected": False,
        "vpn_type": None
    }

@app.route('/', methods=['GET', 'POST'])
def home():
    user_ip = get_user_ip()
    custom_ip = None
    error_message = None
    
    if request.method == 'POST':
        custom_ip = request.form.get('ip_address', '').strip()
        if custom_ip and custom_ip != user_ip:
            data = get_ip_info(custom_ip)
            if 'error' in data:
                error_message = data['error']
                data = get_ip_info()  # Fall back to user's IP
        else:
            data = get_ip_info()
    else:
        data = get_ip_info()
    
    # Set the IP to display in the input field
    display_ip = custom_ip if custom_ip and not error_message else user_ip
    
    # Modern professional HTML template with AJAX
    html_template = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IP Geolocation Tracker</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 480px;
            width: 100%;
            text-align: center;
        }
        
        .header {
            margin-bottom: 20px;
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 4px;
        }
        
        .header p {
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 400;
        }
        
        .ip-input-form {
            background: white;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #f1f5f9;
        }
        
        .input-group {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        
        .input-field {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 500;
            color: #1e293b;
            background: #f8fafc;
            transition: all 0.2s ease;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .input-btn {
            padding: 12px 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 100px;
        }
        
        .input-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .input-btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-new {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }
        
        .status-duplicate {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
        }
        
        .info-card {
            background: white;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #f1f5f9;
        }
        
        .vpn-alert {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border: 1px solid #f59e0b;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .vpn-alert i {
            color: #d97706;
            font-size: 1.25rem;
        }
        
        .vpn-alert-text {
            color: #92400e;
            font-weight: 600;
        }
        
        .info-grid {
            display: grid;
            gap: 8px;
            text-align: left;
        }
        
        .info-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .info-item:last-child {
            border-bottom: none;
        }
        
        .info-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.9rem;
        }
        
        .info-content {
            flex: 1;
        }
        
        .info-label {
            font-size: 0.875rem;
            color: #64748b;
            font-weight: 500;
            margin-bottom: 2px;
        }
        
        .info-value {
            font-size: 1rem;
            color: #1e293b;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .country-flag {
            font-size: 1.25rem;
        }
        
        .actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 16px;
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
            min-height: 42px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
        }
        
        .btn-primary:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-outline {
            background: transparent;
            color: #667eea;
            border: 2px solid #667eea;
        }
        
        .btn-outline:hover {
            background: #667eea;
            color: white;
            transform: translateY(-1px);
        }
        
        .flash-message {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 500;
            font-size: 0.9rem;
        }
        
        .error-message {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 500;
            font-size: 0.9rem;
        }
        
        .duplicate-notice {
            background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
            border: 2px solid #d1d5db;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 14px;
            color: #374151;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9rem;
        }
        
        @media (max-width: 640px) {
            .container {
                padding: 20px;
                margin: 8px;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
            
            .header {
                margin-bottom: 16px;
            }
            
            .input-group {
                flex-direction: column;
                gap: 8px;
            }
            
            .input-field {
                width: 100%;
            }
            
            .input-btn {
                width: 100%;
            }
            
            .actions {
                gap: 6px;
            }
            
            .btn {
                padding: 10px 16px;
                font-size: 0.85rem;
                min-height: 38px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-globe-americas"></i> IP Entry</h1>
        </div>
        
        <!-- IP Input Form -->
        <form method="POST" class="ip-input-form" id="ip-form">
            <div class="input-group">
                <input 
                    type="text" 
                    name="ip_address" 
                    id="ip-input"
                    class="input-field" 
                    placeholder="Enter IP address to analyze..."
                    value="{{ display_ip }}"
                    pattern="^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
                    title="Please enter a valid IP address (e.g., 192.168.1.1)"
                >
                <button type="submit" class="input-btn" id="analyze-btn">
                    <i class="fas fa-search"></i>
                    <span>Analyze</span>
                </button>
            </div>
        </form>
        
        <div id="message-container">
            {% if error_message %}
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    {{ error_message }}
                </div>
            {% endif %}
            
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="flash-message">
                            <i class="fas fa-check-circle"></i>
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        
        <div class="status-badge status-{{ status }}" id="status-badge">
            {% if status == 'new' %}
                <i class="fas fa-star"></i> New IP Address
            {% else %}
                <i class="fas fa-history"></i> Known IP Address
            {% endif %}
        </div>
        
        <div id="vpn-alert" class="vpn-alert" style="display: {% if vpn_detected %}flex{% else %}none{% endif %};">
            <i class="fas fa-shield-alt"></i>
            <div>
                <div class="vpn-alert-text">{{ vpn_type }} Detected</div>
                <div style="font-size: 0.875rem; color: #92400e; margin-top: 4px;">
                    Privacy service detected on this connection
                </div>
            </div>
        </div>
        
        <div class="info-card" id="info-card">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-icon">
                        <i class="fas fa-network-wired"></i>
                    </div>
                    <div class="info-content">
                        <div class="info-label">IP Address</div>
                        <div class="info-value" id="ip-value">{{ ip }}</div>
                    </div>
                </div>
                
                <div class="info-item">
                    <div class="info-icon">
                        <i class="fas fa-flag"></i>
                    </div>
                    <div class="info-content">
                        <div class="info-label">Country</div>
                        <div class="info-value" id="country-value">
                            <span class="country-flag">{{ location.country_flag }}</span>
                            {{ location.country }}
                        </div>
                    </div>
                </div>
                
                <div class="info-item">
                    <div class="info-icon">
                        <i class="fas fa-map-marker-alt"></i>
                    </div>
                    <div class="info-content">
                        <div class="info-label">Location</div>
                        <div class="info-value" id="location-value">
                            {{ location.country }}{% if location.continent %}, {{ location.continent }}{% endif %}
                        </div>
                    </div>
                </div>
                
                <div class="info-item">
                    <div class="info-icon">
                        <i class="fas fa-building"></i>
                    </div>
                    <div class="info-content">
                        <div class="info-label">Organization</div>
                        <div class="info-value" id="org-value">
                            {% if location.as_name %}{{ location.as_name }}{% elif location.org %}{{ location.org }}{% else %}Unknown{% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="actions" id="actions-section">
            {% if status == 'new' %}
                <button id="save-btn" class="btn btn-primary" style="width: 100%;" data-ip="{{ ip }}">
                    <i class="fas fa-save"></i>
                    <span>Save</span>
                </button>
            {% else %}
                <div class="duplicate-notice">
                    <i class="fas fa-database"></i>
                    This IP address is already saved in the database
                </div>
            {% endif %}
            
            <a href="/" class="btn btn-outline">
                <i class="fas fa-sync-alt"></i>
                Refresh Analysis
            </a>
        </div>
    </div>

    <script>
        // AJAX functionality for modern UX
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('ip-form');
            const analyzeBtn = document.getElementById('analyze-btn');
            const ipInput = document.getElementById('ip-input');

            // Analyze IP with AJAX
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const ipAddress = ipInput.value.trim();
                if (!ipAddress) return;

                // Show loading state
                const btnText = analyzeBtn.querySelector('span');
                const btnIcon = analyzeBtn.querySelector('i');
                btnText.textContent = 'Analyzing...';
                btnIcon.className = 'fas fa-spinner fa-spin';
                analyzeBtn.disabled = true;

                try {
                    const response = await fetch('/api/analyze-ip', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ ip_address: ipAddress })
                    });

                    const result = await response.json();

                    if (result.success) {
                        updatePageContent(result.data);
                        showMessage('IP analysis completed!', 'success');
                    } else {
                        showMessage(result.error || 'Analysis failed', 'error');
                    }
                } catch (error) {
                    showMessage('Network error occurred', 'error');
                } finally {
                    // Reset button state
                    btnText.textContent = 'Analyze';
                    btnIcon.className = 'fas fa-search';
                    analyzeBtn.disabled = false;
                }
            });

            // Save IP with AJAX (delegated event listener)
            document.addEventListener('click', async function(e) {
                if (e.target.closest('#save-btn')) {
                    e.preventDefault();
                    
                    const saveBtn = e.target.closest('#save-btn');
                    const ipAddress = saveBtn.dataset.ip;
                    
                    // Show loading state
                    const btnText = saveBtn.querySelector('span');
                    const btnIcon = saveBtn.querySelector('i');
                    btnText.textContent = 'Saving...';
                    btnIcon.className = 'fas fa-spinner fa-spin';
                    saveBtn.disabled = true;

                    try {
                        const response = await fetch('/api/save-ip', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ ip_address: ipAddress })
                        });

                        const result = await response.json();

                        if (result.success) {
                            showMessage(result.message, 'success');
                            updateSaveButton(false);
                        } else {
                            showMessage(result.message || 'Save failed', 'error');
                        }
                    } catch (error) {
                        showMessage('Network error occurred', 'error');
                    } finally {
                        // Reset button state
                        btnText.textContent = 'Save to Database';
                        btnIcon.className = 'fas fa-save';
                        saveBtn.disabled = false;
                    }
                }
            });

            function updatePageContent(data) {
                // Update status badge
                const statusBadge = document.getElementById('status-badge');
                statusBadge.className = `status-badge status-${data.status}`;
                statusBadge.innerHTML = data.status === 'new' 
                    ? '<i class="fas fa-star"></i> New IP Address'
                    : '<i class="fas fa-history"></i> Known IP Address';

                // Update IP info
                document.getElementById('ip-value').textContent = data.ip;
                document.getElementById('country-value').innerHTML = `<span class="country-flag">${data.location.country_flag}</span> ${data.location.country}`;
                document.getElementById('location-value').textContent = `${data.location.city}, ${data.location.region}`;
                document.getElementById('org-value').textContent = data.location.org;

                // Update VPN alert
                const vpnAlert = document.getElementById('vpn-alert');
                if (data.vpn_detected) {
                    vpnAlert.style.display = 'flex';
                    vpnAlert.querySelector('.vpn-alert-text').textContent = `${data.vpn_type} Detected`;
                } else {
                    vpnAlert.style.display = 'none';
                }

                // Update save button
                updateSaveButton(data.status === 'new', data.ip);
            }

            function updateSaveButton(isNew, ip = '') {
                const actionsSection = document.getElementById('actions-section');
                
                if (isNew) {
                    actionsSection.innerHTML = `
                        <button id="save-btn" class="btn btn-primary" style="width: 100%;" data-ip="${ip}">
                            <i class="fas fa-save"></i>
                            <span>Save to Database</span>
                        </button>
                        <a href="/" class="btn btn-outline">
                            <i class="fas fa-sync-alt"></i>
                            Refresh Analysis
                        </a>
                    `;
                } else {
                    actionsSection.innerHTML = `
                        <div class="duplicate-notice">
                            <i class="fas fa-database"></i>
                            This IP address is already saved in the database
                        </div>
                        <a href="/" class="btn btn-outline">
                            <i class="fas fa-sync-alt"></i>
                            Refresh Analysis
                        </a>
                    `;
                }
            }

            function showMessage(message, type) {
                // Remove existing messages
                const messageContainer = document.getElementById('message-container');
                messageContainer.innerHTML = '';

                // Create new message
                const messageDiv = document.createElement('div');
                messageDiv.className = type === 'success' ? 'flash-message' : 'error-message';
                messageDiv.innerHTML = `
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
                    ${message}
                `;

                messageContainer.appendChild(messageDiv);

                // Auto-remove after 5 seconds
                setTimeout(() => {
                    messageDiv.remove();
                }, 5000);
            }
        });
    </script>
</body>
</html>
    """
    
    return render_template_string(html_template, display_ip=display_ip, error_message=error_message, **data)

@app.route('/save-ip', methods=['POST'])
def save_ip():
    ip_to_save = request.form.get('ip_to_save')
    if ip_to_save:
        data = get_ip_info(ip_to_save)
    else:
        data = get_ip_info()
    
    if data['status'] == 'new':
        if save_ip_to_database(data):
            flash(f"IP {data['ip']} saved successfully!")
        else:
            flash("Error saving IP to database.")
    else:
        flash("IP already exists in database.")
    
    return redirect(url_for('home'))

# AJAX API Endpoints
@app.route('/api/analyze-ip', methods=['POST'])
def api_analyze_ip():
    """AJAX endpoint for IP analysis"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address', '').strip()
        logger.info(f"API /api/analyze-ip called with IP: {ip_address}")
        
        if not ip_address:
            logger.warning("No IP address provided to /api/analyze-ip")
            return jsonify({'error': 'IP address is required'}), 400
        
        result = get_ip_info(ip_address)
        
        if 'error' in result:
            logger.warning(f"Error in IP analysis: {result['error']}")
            return jsonify({'error': result['error']}), 400
        
        logger.info(f"IP analysis successful for {ip_address}")
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Exception in /api/analyze-ip: {e}")
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/api/save-ip', methods=['POST'])
def api_save_ip():
    """AJAX endpoint for saving IP to database"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address', '').strip()
        logger.info(f"API /api/save-ip called with IP: {ip_address}")
        
        if not ip_address:
            logger.warning("No IP address provided to /api/save-ip")
            return jsonify({'error': 'IP address is required'}), 400
        
        ip_data = get_ip_info(ip_address)
        
        if 'error' in ip_data:
            logger.warning(f"Error in IP data: {ip_data['error']}")
            return jsonify({'error': ip_data['error']}), 400
        
        if ip_data['status'] == 'new':
            if save_ip_to_database(ip_data):
                logger.info(f"IP {ip_data['ip']} saved successfully via API.")
                return jsonify({
                    'success': True,
                    'message': f"IP {ip_data['ip']} saved successfully!",
                    'data': ip_data
                })
            else:
                logger.error(f"Failed to save IP {ip_data['ip']} to database via API.")
                return jsonify({'error': 'Failed to save IP to database'}), 500
        else:
            logger.info(f"IP {ip_data['ip']} already exists in database.")
            return jsonify({
                'success': False,
                'message': 'IP already exists in database',
                'data': ip_data
            })
            
    except Exception as e:
        logger.error(f"Exception in /api/save-ip: {e}")
        return jsonify({'error': 'Server error occurred'}), 500


if __name__ == '__main__':
    logger.info("Starting Flask app for local testing on http://0.0.0.0:5005")
    # For development only - in production, use Gunicorn
    app.run(host='0.0.0.0', port=5005, debug=False)
