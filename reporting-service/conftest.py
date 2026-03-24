import pytest
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(scope='session')
def test_db():
    """Create a test database for reporting service"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database='inventory_test',
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        port=os.getenv('DB_PORT', 5432),
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Drop and recreate test database
    try:
        cur.execute('DROP DATABASE IF EXISTS inventory_test')
        cur.execute('CREATE DATABASE inventory_test')
    except psycopg2.Error:
        pass
    finally:
        cur.close()
        conn.close()

    # Connect to test database and set up schema
    test_conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database='inventory_test',
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        port=os.getenv('DB_PORT', 5432),
    )

    cur = test_conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS locations (
        id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE,
        address TEXT, created_at TIMESTAMP DEFAULT NOW())''')

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL, full_name VARCHAR(255) NOT NULL,
        email VARCHAR(255), phone VARCHAR(20),
        role VARCHAR(20) NOT NULL CHECK (role IN ('admin','manager','employee')),
        location_id INTEGER REFERENCES locations(id),
        created_at TIMESTAMP DEFAULT NOW(), last_login TIMESTAMP)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL,
        sku VARCHAR(100) UNIQUE, quantity INTEGER NOT NULL DEFAULT 0,
        min_quantity INTEGER NOT NULL DEFAULT 10,
        price DECIMAL(10,2) DEFAULT 0.00, category VARCHAR(100),
        location_id INTEGER REFERENCES locations(id),
        created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW())''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id SERIAL PRIMARY KEY, item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
        alert_type VARCHAR(50), message TEXT,
        status VARCHAR(20) DEFAULT 'active', created_at TIMESTAMP DEFAULT NOW(),
        resolved_at TIMESTAMP)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(255), details TEXT, created_at TIMESTAMP DEFAULT NOW())''')

    # Seed test data
    cur.execute("INSERT INTO locations (name, address) VALUES ('Test Warehouse','123 Test St')")
    cur.execute('''INSERT INTO users (username,password_hash,full_name,role)
                   VALUES ('testuser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8GwqGvGjS', 'Test User', 'admin')''')

    cur.execute('''INSERT INTO items (name, sku, quantity, min_quantity, price, category)
                   VALUES ('Laptop', 'LAP001', 5, 10, 999.99, 'Electronics')''')
    cur.execute('''INSERT INTO items (name, sku, quantity, min_quantity, price, category)
                   VALUES ('Mouse', 'MOU001', 0, 5, 29.99, 'Electronics')''')
    cur.execute('''INSERT INTO items (name, sku, quantity, min_quantity, price, category)
                   VALUES ('Keyboard', 'KEY001', 25, 10, 79.99, 'Electronics')''')

    cur.execute('''INSERT INTO alerts (item_id, alert_type, message, status)
                   VALUES (1, 'low_stock', 'Laptop is running low', 'active')''')
    cur.execute('''INSERT INTO alerts (item_id, alert_type, message, status)
                   VALUES (2, 'out_of_stock', 'Mouse is out of stock', 'active')''')

    cur.execute('''INSERT INTO activity_log (user_id, action, details)
                   VALUES (1, 'Item added', 'Added: Laptop')''')
    cur.execute('''INSERT INTO activity_log (user_id, action, details)
                   VALUES (1, 'Item updated', 'Updated item ID: 1')''')

    test_conn.commit()
    cur.close()

    yield test_conn
    test_conn.close()

@pytest.fixture
def test_client(test_db):
    """Create a test client for the reporting service"""
    from reporting_services import app

    # Monkey patch the database connection
    import reporting_services
    original_get_db = reporting_services.get_db
    reporting_services.get_db = lambda: test_db

    with app.test_client() as client:
        yield client

    # Restore original
    reporting_services.get_db = original_get_db