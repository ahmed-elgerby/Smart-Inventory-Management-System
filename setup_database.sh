#!/bin/bash
# Database Setup Script for Inventory Management System
# This script helps you set up PostgreSQL database

set -e  # Exit on error

echo "================================================"
echo "Inventory Management System - Database Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DB_NAME=${DB_NAME:-inventory}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-yourpassword}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo "Configuration:"
echo "  Database Name: $DB_NAME"
echo "  Database User: $DB_USER"
echo "  Database Host: $DB_HOST"
echo "  Database Port: $DB_PORT"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: PostgreSQL is not installed${NC}"
    echo "Please install PostgreSQL first:"
    echo "  Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "  macOS: brew install postgresql"
    echo "  CentOS/RHEL: sudo yum install postgresql-server"
    exit 1
fi

echo -e "${GREEN}✓ PostgreSQL is installed${NC}"

# Check if PostgreSQL service is running
if command -v systemctl &> /dev/null; then
    if ! systemctl is-active --quiet postgresql; then
        echo -e "${YELLOW}PostgreSQL service is not running. Starting it...${NC}"
        sudo systemctl start postgresql
    fi
    echo -e "${GREEN}✓ PostgreSQL service is running${NC}"
fi

# Function to execute SQL
execute_sql() {
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$1"
}

# Create database if it doesn't exist
echo ""
echo "Step 1: Creating database..."
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U postgres -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo -e "${YELLOW}Database '$DB_NAME' already exists${NC}"
    read -p "Do you want to DROP and recreate it? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        echo "Dropping existing database..."
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE DATABASE $DB_NAME;"
        echo -e "${GREEN}✓ Database recreated${NC}"
    else
        echo "Keeping existing database"
    fi
else
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE DATABASE $DB_NAME;"
    echo -e "${GREEN}✓ Database created${NC}"
fi

# Initialize database with schema
echo ""
echo "Step 2: Initializing database schema..."
if [ -f "init_database_UPDATED_v2.sql" ]; then
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f init_database_UPDATED_v2.sql
    echo -e "${GREEN}✓ Database schema initialized${NC}"
else
    echo -e "${RED}Error: init_database_UPDATED_v2.sql not found${NC}"
    echo "Please make sure init_database_UPDATED_v2.sql is in the current directory"
    exit 1
fi

# Verify setup
echo ""
echo "Step 3: Verifying setup..."
USER_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM users;")
ITEM_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM items;")
ALERT_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM alerts;")

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Database Statistics:"
echo "  Users: $USER_COUNT"
echo "  Items: $ITEM_COUNT"
echo "  Alerts: $ALERT_COUNT"

# Show default credentials
echo ""
echo "================================================"
echo "DEFAULT LOGIN CREDENTIALS"
echo "================================================"
echo ""
echo "Admin Account:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Manager Account:"
echo "  Username: manager"
echo "  Password: manager123"
echo ""
echo -e "${YELLOW}⚠ IMPORTANT: Change these passwords after first login!${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Step 4: Creating .env file..."
    cat > .env << EOF
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-this-secret-key")
FLASK_ENV=development
FLASK_DEBUG=True
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
    echo "  Location: $(pwd)/.env"
else
    echo -e "${YELLOW}.env file already exists, skipping creation${NC}"
fi

echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo "1. Review and update .env file if needed"
echo "2. Install Python dependencies: pip install -r requirements.txt"
echo "3. Run the backend: python enhanced_inventory_service.py"
echo "4. Open complete_dashboard.html in your browser"
echo "5. Login with the credentials above"
echo ""
echo "For Docker deployment:"
echo "  docker-compose up -d"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}"
