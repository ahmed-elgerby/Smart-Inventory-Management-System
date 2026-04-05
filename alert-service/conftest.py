import pytest
import psycopg2
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

@pytest.fixture(scope='session')
def test_db():
    """Create a test database for alert service"""
    # First connect to default postgres database to create test database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database='postgres',  # Connect to default postgres db
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
    cur.execute('''CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL,
        sku VARCHAR(100) UNIQUE, quantity INTEGER NOT NULL DEFAULT 0,
        min_quantity INTEGER NOT NULL DEFAULT 10,
        price DECIMAL(10,2) DEFAULT 0.00, category VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW())''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id SERIAL PRIMARY KEY, item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
        alert_type VARCHAR(50), message TEXT,
        status VARCHAR(20) DEFAULT 'active', created_at TIMESTAMP DEFAULT NOW(),
        resolved_at TIMESTAMP)''')

    # Seed test data
    cur.execute('''INSERT INTO items (name, sku, quantity, min_quantity, category)
                   VALUES ('Test Item 1', 'TEST001', 5, 10, 'Electronics')''')
    cur.execute('''INSERT INTO items (name, sku, quantity, min_quantity, category)
                   VALUES ('Test Item 2', 'TEST002', 0, 5, 'Electronics')''')
    cur.execute('''INSERT INTO items (name, sku, quantity, min_quantity, category)
                   VALUES ('Test Item 3', 'TEST003', 15, 10, 'Electronics')''')

    test_conn.commit()
    cur.close()

    yield test_conn
    test_conn.close()

@pytest.fixture
def test_client(test_db):
    """Create a test client for the alert service"""
    from alert_microservice import app

    # Monkey patch the database connection
    import alert_service
    original_get_db = alert_service.get_db_connection
    alert_service.get_db_connection = lambda: test_db

    with app.test_client() as client:
        yield client

    # Restore original
    alert_service.get_db_connection = original_get_db