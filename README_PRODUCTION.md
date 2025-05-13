# Krishna AI Production Deployment Guide

This guide explains how to prepare the Krishna AI application for production deployment and publishing to app stores.

## Environment Setup

### 1. Create a Production Environment File

Create a `.env.production` file in the root directory with the following settings:

```
# Production Environment Configuration

# OpenAI API Settings
OPENAI_API_KEY=your_production_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.6
OPENAI_MAX_TOKENS=500

# Database Settings
DATABASE_TYPE=postgres
DATABASE_URL=postgresql://user:password@localhost:5432/krishna_db

# Flask Settings
FLASK_SECRET_KEY=generate_a_secure_random_key_here
FLASK_ENV=production
DEBUG=False

# CORS Settings - Configure for your production domain
CORS_ALLOWED_ORIGINS=https://your-production-domain.com,https://api.your-production-domain.com

# Feature Flags
ENABLE_USER_ACCOUNTS=True
ENABLE_ANALYTICS=True

# Security Settings
RATE_LIMIT_DEFAULT=50/day;15/hour;3/minute
```

### 2. Install Required Production Dependencies

```bash
pip install psycopg2-binary gunicorn
```

## Database Setup

### 1. Set Up PostgreSQL Database

For production, it's recommended to use PostgreSQL instead of SQLite:

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
postgres=# CREATE DATABASE krishna_db;
postgres=# CREATE USER krishnauser WITH PASSWORD 'your_secure_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE krishna_db TO krishnauser;
postgres=# \q
```

### 2. Update DATABASE_URL in your .env.production file

```
DATABASE_URL=postgresql://krishnauser:your_secure_password@localhost:5432/krishna_db
```

## Server Deployment

### 1. Set Up a Production Web Server

For production, use Gunicorn with a reverse proxy like Nginx:

```bash
# Install Nginx
sudo apt-get install nginx

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/krishna-ai
```

Add the following configuration:

```
server {
    listen 80;
    server_name your-production-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/krishna-ai /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

### 2. Start the Production Server

Use the production startup script:

```bash
bash start_app_prod.sh
```

For a more robust deployment, create a systemd service file:

```bash
sudo nano /etc/systemd/system/krishna-ai.service
```

Add the following:

```
[Unit]
Description=Krishna AI Backend
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/KrishnaAI
Environment="ENVIRONMENT=production"
ExecStart=/usr/local/bin/gunicorn -w 4 -b 127.0.0.1:5000 "krishna_backend.main:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable krishna-ai
sudo systemctl start krishna-ai
```

## Mobile App Configuration

### 1. Update API Endpoint

Before building the mobile app, make sure to update the API endpoint to point to your production server:

1. Edit `krishna_ai_app/lib/services/api_service.dart` and update the `baseUrl` to your production domain:

```dart
final String baseUrl = 'https://your-production-domain.com';
```

### 2. Build for Production

For Android:

```bash
cd krishna_ai_app
flutter build appbundle
```

For iOS:

```bash
cd krishna_ai_app
flutter build ios --release
```

## Security Considerations

1. **API Keys**: Never include API keys in the mobile app. Always use the backend server to make API calls.

2. **User Data**: Set up proper data retention and deletion policies to comply with privacy regulations.

3. **SSL/TLS**: Configure HTTPS on your server to encrypt data in transit.

4. **Rate Limiting**: Implement rate limiting to prevent abuse.

5. **Database Backups**: Set up regular automated backups of your production database.

## Testing the Production Environment Locally

You can test the production environment locally before deploying:

```bash
# Create and populate .env.production file
cp .env.production.example .env.production
# Edit the file with your settings

# Install production dependencies
pip install psycopg2-binary gunicorn

# Run the production startup script
bash start_app_prod.sh
```

## Deployment Checklist

- [ ] Created and configured `.env.production`
- [ ] Set up PostgreSQL database
- [ ] Updated database connection URL
- [ ] Installed required production dependencies
- [ ] Configured web server and reverse proxy
- [ ] Updated mobile app API endpoint
- [ ] Generated production builds for mobile apps
- [ ] Set up SSL/TLS encryption
- [ ] Implemented data backup solution
- [ ] Tested the production environment 