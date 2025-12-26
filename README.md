# MySQL-Admin

A web-based database management tool for MySQL with a modern interface.

This project using FastAPI as the backend, because I don't want to install PHP when I use phpmyadmin

If you have any idea, please feel free and make your PR, thank you!

## Features

- Database management (create, delete, view DDL)
- Table management (list, delete, view data)
- Data manipulation (insert, update, delete rows)
- Filter table data with conditions
- Execute custom SQL queries
- Modern web interface with Vue.js and Element Plus

## Requirements

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- Linux operating system

## Installation

1. Create a virtual environment:
```bash
cd mysql-admin
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database connection (optional):
```bash
cp .env.example .env
vim .env
```

## Running the Application

Start the server:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Access the application at: http://localhost:8000

## Development

Run tests:
```bash
pytest
```

## Configuration

Environment variables:
- `MYSQL_HOST`: MySQL server host (default: localhost)
- `MYSQL_PORT`: MySQL server port (default: 3306)
- `MYSQL_USER`: MySQL username (default: root)
- `MYSQL_PASSWORD`: MySQL password (default: 123456)
- `MYSQL_POOL_MIN`: Minimum pool size (default: 1)
- `MYSQL_POOL_MAX`: Maximum pool size (default: 10)
- `ADMIN_SECRET_KEY`: Admin authentication key (default: admin123)

## Security Features

### Authentication
- Admin secret key required for all database operations
- Key can be configured via `ADMIN_SECRET_KEY` environment variable
- Login page at `/login.html`

### Rate Limiting
- Maximum 3 login attempts per minute per IP address
- Automatic lockout after exceeding limit
- Prevents brute force attacks

### Login Logging
- All login attempts are logged to `logs/login.txt`
- Log format: `YYYY-MM-DD HH:MM:SS   IP_ADDRESS   RESULT`
- Results: `success` or `failed`
- Useful for security auditing and monitoring

Example log entries:
```
2025-12-04 19:22:03   113.89.104.100   success
2025-12-04 19:23:15   192.168.1.100   failed
2025-12-04 19:24:30   10.0.0.50   success
```
