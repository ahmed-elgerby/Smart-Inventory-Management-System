import pytest
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(scope='session')
def test_db():
    """Create a test database connection"""
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
        pass  # Database might be in use
    finally:
        cur.close()
        conn.close()

    # Connect to test database
    test_conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database='inventory_test',
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        port=os.getenv('DB_PORT', 5432),
    )

    # Initialize schema
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
        photo BYTEA, photo_filename VARCHAR(255),
        created_at TIMESTAMP DEFAULT NOW(), last_login TIMESTAMP)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL,
        sku VARCHAR(100) UNIQUE, quantity INTEGER NOT NULL DEFAULT 0,
        min_quantity INTEGER NOT NULL DEFAULT 10,
        price DECIMAL(10,2) DEFAULT 0.00, category VARCHAR(100),
        location_id INTEGER REFERENCES locations(id),
        picture BYTEA, picture_filename VARCHAR(255),
        created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW())''')

    cur.execute('''CREATE TABLE IF NOT EXISTS item_locations (
        id SERIAL PRIMARY KEY,
        item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
        location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(item_id, location_id))''')

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
                   VALUES ('testadmin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8GwqGvGjS', 'Test Admin', 'admin')''')
    cur.execute('''INSERT INTO users (username,password_hash,full_name,role)
                   VALUES ('testmgr', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8GwqGvGjS', 'Test Manager', 'manager')''')
    cur.execute('''INSERT INTO users (username,password_hash,full_name,role)
                   VALUES ('testemp', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8GwqGvGjS', 'Test Employee', 'employee')''')

    test_conn.commit()
    cur.close()

    yield test_conn

    # Cleanup
    test_conn.close()

@pytest.fixture
def test_client(test_db):
    """Create a test client for the Flask app"""
    from backend import app

    # Override DB connection for tests
    original_get_db = app.config.get('get_db_func')
    def mock_get_db():
        return test_db

    # Monkey patch the get_db function
    import backend
    backend.get_db = mock_get_db

    with app.test_client() as client:
        yield client

    # Restore original if it existed
    if original_get_db:
        backend.get_db = original_get_db

@pytest.fixture
def auth_token(test_client):
    """Get an authentication token for testing"""
    response = test_client.post('/auth/login', json={
        'username': 'testadmin',
        'password': 'admin123'
    })
    data = response.get_json()
    return data['token']