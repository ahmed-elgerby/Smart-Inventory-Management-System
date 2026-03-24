import pytest
import json

def test_health_check(test_client):
    """Test the health endpoint"""
    response = test_client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'inventory'

def test_login_success(test_client):
    """Test successful login"""
    response = test_client.post('/auth/login', json={
        'username': 'testadmin',
        'password': 'admin123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'token' in data
    assert 'user' in data
    assert data['user']['username'] == 'testadmin'
    assert data['user']['role'] == 'admin'

def test_login_invalid_credentials(test_client):
    """Test login with invalid credentials"""
    response = test_client.post('/auth/login', json={
        'username': 'testadmin',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401
    data = response.get_json()
    assert 'error' in data

def test_get_me(auth_token, test_client):
    """Test getting current user info"""
    response = test_client.get('/auth/me',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['username'] == 'testadmin'
    assert data['role'] == 'admin'

def test_get_locations(auth_token, test_client):
    """Test getting locations list"""
    response = test_client.get('/locations',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1  # At least the test warehouse

def test_create_location(auth_token, test_client):
    """Test creating a new location"""
    response = test_client.post('/locations',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={'name': 'New Test Location', 'address': '456 Test Ave'})
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data

def test_get_items(auth_token, test_client):
    """Test getting items list"""
    response = test_client.get('/items',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_create_item(auth_token, test_client):
    """Test creating a new item"""
    response = test_client.post('/items',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Test Item',
            'sku': 'TEST001',
            'quantity': 10,
            'min_quantity': 5,
            'price': 29.99,
            'category': 'Electronics'
        })
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data

    # Store item ID for other tests
    pytest.item_id = data['id']

def test_update_item(auth_token, test_client):
    """Test updating an item"""
    # First create an item
    response = test_client.post('/items',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Update Test Item',
            'sku': 'UPDATE001',
            'quantity': 20,
            'min_quantity': 10
        })
    assert response.status_code == 201
    item_data = response.get_json()
    item_id = item_data['id']

    # Now update it
    response = test_client.put(f'/items/{item_id}',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={'quantity': 25, 'price': 39.99})
    assert response.status_code == 200

def test_get_analytics(auth_token, test_client):
    """Test getting analytics summary"""
    response = test_client.get('/analytics/summary',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'total_items' in data
    assert 'low_stock_count' in data
    assert 'inventory_value' in data

def test_get_users(auth_token, test_client):
    """Test getting users list (admin only)"""
    response = test_client.get('/users',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 3  # testadmin, testmgr, testemp

def test_create_user(auth_token, test_client):
    """Test creating a new user"""
    response = test_client.post('/users',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'username': 'newtestuser',
            'password': 'testpass123',
            'full_name': 'New Test User',
            'role': 'employee'
        })
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data

def test_get_contacts(auth_token, test_client):
    """Test getting contacts"""
    response = test_client.get('/contacts',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_metrics_endpoint(test_client):
    """Test metrics endpoint"""
    response = test_client.get('/metrics')
    assert response.status_code == 200
    # Should return Prometheus-style metrics
    assert b'inventory_' in response.data

def test_unauthorized_access(test_client):
    """Test that endpoints require authentication"""
    endpoints = ['/items', '/locations', '/users', '/analytics/summary']
    for endpoint in endpoints:
        response = test_client.get(endpoint)
        assert response.status_code == 401