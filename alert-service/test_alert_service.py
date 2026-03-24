import pytest
from alert_service import (
    get_active_alerts, create_alert_for_item, resolve_alert,
    check_and_create_alerts_for_item, get_alert_count
)

def test_get_active_alerts_empty(test_db):
    """Test getting alerts when none exist"""
    alerts = get_active_alerts()
    assert isinstance(alerts, list)
    assert len(alerts) == 0

def test_create_and_get_alerts(test_db):
    """Test creating and retrieving alerts"""
    # Create an alert
    create_alert_for_item(1, 'low_stock', 'Test Item 1 is low on stock')

    # Get active alerts
    alerts = get_active_alerts()
    assert len(alerts) == 1
    assert alerts[0]['alert_type'] == 'low_stock'
    assert alerts[0]['item_name'] == 'Test Item 1'
    assert alerts[0]['quantity'] == 5
    assert alerts[0]['min_quantity'] == 10

def test_resolve_alert(test_db):
    """Test resolving an alert"""
    # Create an alert
    create_alert_for_item(1, 'low_stock', 'Test alert')

    # Get the alert ID
    alerts = get_active_alerts()
    assert len(alerts) == 1
    alert_id = alerts[0]['id']

    # Resolve it
    resolve_alert(alert_id)

    # Check it's resolved
    alerts = get_active_alerts()
    assert len(alerts) == 0

def test_check_and_create_alerts_for_item(test_db):
    """Test the automatic alert creation logic"""
    # Test low stock alert creation
    check_and_create_alerts_for_item(1, 'Test Item 1', 5, 10)
    alerts = get_active_alerts()
    assert len(alerts) == 1
    assert alerts[0]['alert_type'] == 'low_stock'

    # Test out of stock alert creation
    check_and_create_alerts_for_item(2, 'Test Item 2', 0, 5)
    alerts = get_active_alerts()
    assert len(alerts) == 2
    out_of_stock_alerts = [a for a in alerts if a['alert_type'] == 'out_of_stock']
    assert len(out_of_stock_alerts) == 1

    # Test alert resolution when stock is sufficient
    check_and_create_alerts_for_item(1, 'Test Item 1', 15, 10)
    alerts = get_active_alerts()
    # Should still have the out of stock alert, but low stock should be resolved
    low_stock_alerts = [a for a in alerts if a['alert_type'] == 'low_stock']
    assert len(low_stock_alerts) == 0

def test_get_alert_count(test_db):
    """Test getting alert count"""
    # Initially 0
    assert get_alert_count() == 0

    # Create some alerts
    create_alert_for_item(1, 'low_stock', 'Alert 1')
    create_alert_for_item(2, 'out_of_stock', 'Alert 2')

    assert get_alert_count() == 2

    # Resolve one
    alerts = get_active_alerts()
    resolve_alert(alerts[0]['id'])

    assert get_alert_count() == 1

def test_alert_service_api(test_client):
    """Test the Flask API endpoints"""
    # Test health endpoint (if exists)
    response = test_client.get('/alerts')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

    # Create an alert via the service
    from alert_service import create_alert_for_item
    create_alert_for_item(1, 'test_alert', 'Test message')

    # Check it appears in API
    response = test_client.get('/alerts')
    data = response.get_json()
    assert len(data) >= 1

    # Test resolve endpoint
    if data:
        alert_id = data[0]['id']
        response = test_client.post(f'/alerts/{alert_id}/resolve')
        assert response.status_code == 200

        # Check it's resolved
        response = test_client.get('/alerts')
        data = response.get_json()
        resolved_alerts = [a for a in data if a['id'] == alert_id]
        assert len(resolved_alerts) == 0