import pytest

def test_inventory_summary(test_client):
    """Test inventory summary report"""
    response = test_client.get('/reports/inventory-summary')
    assert response.status_code == 200
    data = response.get_json()

    assert 'report_type' in data
    assert data['report_type'] == 'inventory_summary'
    assert 'summary' in data
    assert 'categories' in data
    assert 'top_10_items' in data
    assert 'low_stock_items' in data
    assert 'out_of_stock_items' in data

    # Check summary data
    summary = data['summary']
    assert 'total_items' in summary
    assert 'total_quantity' in summary
    assert 'total_value' in summary
    assert 'out_of_stock_count' in summary
    assert 'low_stock_count' in summary

def test_alerts_detail(test_client):
    """Test alerts detail report"""
    response = test_client.get('/reports/alerts-detail')
    assert response.status_code == 200
    data = response.get_json()

    assert 'report_type' in data
    assert data['report_type'] == 'alerts_detail'
    assert 'statistics' in data
    assert 'active_alerts' in data
    assert 'alert_trend_30days' in data
    assert 'recently_resolved' in data

    # Check statistics
    stats = data['statistics']
    assert 'total_alerts' in stats
    assert 'active_count' in stats
    assert 'resolved_count' in stats

def test_activity_log(test_client):
    """Test activity log report"""
    response = test_client.get('/reports/activity-log')
    assert response.status_code == 200
    data = response.get_json()

    assert 'report_type' in data
    assert data['report_type'] == 'activity_log'
    assert 'log_entries' in data
    assert 'activity_by_user' in data
    assert 'action_distribution' in data
    assert 'daily_trend' in data

    # Should have test data
    assert len(data['log_entries']) >= 2

def test_comprehensive_report(test_client):
    """Test comprehensive report"""
    response = test_client.get('/reports/comprehensive')
    assert response.status_code == 200
    data = response.get_json()

    assert 'report_type' in data
    assert data['report_type'] == 'comprehensive'
    assert 'inventory_overview' in data
    assert 'alerts_overview' in data
    assert 'users_overview' in data
    assert 'top_categories' in data
    assert 'system_health' in data

def test_period_comparison(test_client):
    """Test period comparison report"""
    response = test_client.get('/reports/period-comparison?period1_days=7&period2_days=7')
    assert response.status_code == 200
    data = response.get_json()

    assert 'report_type' in data
    assert data['report_type'] == 'period_comparison'
    assert 'period1_last_7_days' in data
    assert 'period2_days_7_to_14' in data

def test_health_endpoint(test_client):
    """Test health endpoint"""
    response = test_client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'reporting'

def test_activity_log_with_limits(test_client):
    """Test activity log with custom limits"""
    response = test_client.get('/reports/activity-log?limit=1&days=30')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['log_entries']) <= 1

def test_inventory_summary_data_integrity(test_client):
    """Test that inventory summary data makes sense"""
    response = test_client.get('/reports/inventory-summary')
    data = response.get_json()

    summary = data['summary']
    items = data['top_10_items']

    # Total items should match the count of items
    assert summary['total_items'] >= len(items)

    # Out of stock count should be >= 0
    assert summary['out_of_stock_count'] >= 0
    assert summary['low_stock_count'] >= 0

def test_alerts_detail_data_integrity(test_client):
    """Test that alerts detail data is consistent"""
    response = test_client.get('/reports/alerts-detail')
    data = response.get_json()

    stats = data['statistics']
    active_alerts = data['active_alerts']

    # Active count should match the number of active alerts returned
    assert stats['active_count'] == len(active_alerts)

def test_comprehensive_report_calculations(test_client):
    """Test that comprehensive report calculations are correct"""
    response = test_client.get('/reports/comprehensive')
    data = response.get_json()

    inventory = data['inventory_overview']
    alerts = data['alerts_overview']

    # Total alerts should be active + resolved
    assert inventory['total_items'] >= 0
    assert alerts['total_alerts'] == alerts['active'] + alerts['resolved']