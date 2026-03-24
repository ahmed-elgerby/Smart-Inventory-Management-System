#!/usr/bin/env python3
"""
Integration Tests for Inventory Management System
Tests the interaction between all services

Jenkins-compatible test runner with structured logging and exit codes.
Generates JUnit XML reports for CI/CD pipeline integration.
"""

import requests
import time
import json
import os
import sys
import logging
from typing import Dict, Any
from datetime import datetime

# Service URLs (adjust if needed)
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
ALERT_URL = os.getenv('ALERT_URL', 'http://localhost:5001')
REPORTING_URL = os.getenv('REPORTING_URL', 'http://localhost:5002')

# CI/CD environment detection
IS_CI = os.getenv('CI') or os.getenv('JENKINS_HOME') or os.getenv('GITHUB_ACTIONS')

# Configure logging for Jenkins compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('integration-test.log')
    ]
)
logger = logging.getLogger(__name__)

# Disable colored output in CI environment
if IS_CI:
    os.environ['NO_COLOR'] = '1'

class IntegrationTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []
        self.timeout = 10  # Jenkins timeout safety
        
    def _log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result for Jenkins parsing"""
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            'name': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        log_msg = f"[{status}] {test_name}"
        if message:
            log_msg += f": {message}"
        logger.info(log_msg)

    def _check_service_ready(self, url: str, service_name: str) -> bool:
        """Check if service is ready with retries"""
        retries = 5
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code in [200, 404]:  # 404 acceptable for health check
                    return True
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting for {service_name}... (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
        return False

    def login(self) -> bool:
        """Login and get authentication token"""
        try:
            response = self.session.post(f'{BACKEND_URL}/auth/login', json={
                'username': 'admin',
                'password': 'admin123'
            }, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                self._log_test("Login", True, "Authentication successful")
                return True
            else:
                self._log_test("Login", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self._log_test("Login", False, str(e))
            return False

    def test_backend_health(self) -> bool:
        """Test backend service health"""
        try:
            response = self.session.get(f'{BACKEND_URL}/health', timeout=self.timeout)
            if response.status_code == 200:
                self._log_test("Backend Health", True)
                return True
            else:
                self._log_test("Backend Health", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self._log_test("Backend Health", False, str(e))
            return False

    def test_alert_service_health(self) -> bool:
        """Test alert service health"""
        try:
            response = requests.get(f'{ALERT_URL}/alerts', timeout=self.timeout)
            if response.status_code == 200:
                self._log_test("Alert Service Health", True)
                return True
            else:
                self._log_test("Alert Service Health", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self._log_test("Alert Service Health", False, str(e))
            return False

    def test_reporting_service_health(self) -> bool:
        """Test reporting service health"""
        try:
            response = requests.get(f'{REPORTING_URL}/health', timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self._log_test("Reporting Service Health", True)
                    return True
                else:
                    self._log_test("Reporting Service Health", False, f"Unhealthy: {data}")
                    return False
            else:
                self._log_test("Reporting Service Health", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self._log_test("Reporting Service Health", False, str(e))
            return False

    def test_create_item(self) -> Dict[str, Any]:
        """Test creating an item"""
        try:
            item_data = {
                'name': 'Integration Test Item',
                'sku': 'INTTEST001',
                'quantity': 5,
                'min_quantity': 10,
                'price': 99.99,
                'category': 'Testing'
            }
            response = self.session.post(f'{BACKEND_URL}/items', json=item_data, timeout=self.timeout)
            if response.status_code == 201:
                data = response.json()
                self._log_test("Item Creation", True)
                return data
            else:
                self._log_test("Item Creation", False, f"Status: {response.status_code}")
                return {}
        except Exception as e:
            self._log_test("Item Creation", False, str(e))
            return {}

    def test_alert_generation(self, item_data: Dict[str, Any]) -> bool:
        """Test that alerts are generated for low stock"""
        try:
            # Wait a moment for alert service to process
            time.sleep(2)

            response = requests.get(f'{ALERT_URL}/alerts', timeout=self.timeout)
            if response.status_code == 200:
                alerts = response.json()
                # Should have at least one alert for the low stock item
                low_stock_alerts = [a for a in alerts if a.get('alert_type') == 'low_stock']
                if low_stock_alerts:
                    self._log_test("Alert Generation", True, f"Found {len(low_stock_alerts)} low stock alerts")
                    return True
                else:
                    self._log_test("Alert Generation", False, f"No low stock alerts. Total: {len(alerts)}")
                    return False
            else:
                self._log_test("Alert Generation", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self._log_test("Alert Generation", False, str(e))
            return False

    def test_reporting_integration(self) -> bool:
        """Test that reporting service can access data"""
        try:
            response = requests.get(f'{REPORTING_URL}/reports/inventory-summary', timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if 'summary' in data and 'total_items' in data['summary']:
                    self._log_test("Reporting Integration", True)
                    return True
                else:
                    self._log_test("Reporting Integration", False, f"Invalid data: {data}")
                    return False
            else:
                self._log_test("Reporting Integration", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self._log_test("Reporting Integration", False, str(e))
            return False

    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        logger.info("=" * 60)
        logger.info("Starting Integration Test Suite")
        logger.info("=" * 60)
        
        # Check service availability first
        logger.info("Checking service availability...")
        if not self._check_service_ready(f'{BACKEND_URL}/health', 'Backend'):
            logger.error(f"Backend service not available at {BACKEND_URL}")
            return False
        if not self._check_service_ready(f'{ALERT_URL}/alerts', 'Alert Service'):
            logger.error(f"Alert service not available at {ALERT_URL}")
            return False
        if not self._check_service_ready(f'{REPORTING_URL}/health', 'Reporting Service'):
            logger.error(f"Reporting service not available at {REPORTING_URL}")
            return False

        tests = [
            ("Backend Health", self.test_backend_health),
            ("Alert Service Health", self.test_alert_service_health),
            ("Reporting Service Health", self.test_reporting_service_health),
            ("User Login", self.login),
        ]

        all_passed = True
        for test_name, test_func in tests:
            logger.info(f"Running: {test_name}")
            if not test_func():
                all_passed = False

        if self.token:  # Only run authenticated tests if login worked
            logger.info("Running authenticated tests...")
            item_data = self.test_create_item()
            if item_data:
                if not self.test_alert_generation(item_data):
                    all_passed = False
            else:
                all_passed = False

            if not self.test_reporting_integration():
                all_passed = False

        logger.info("=" * 60)
        logger.info(f"Test Results Summary: {sum(1 for r in self.test_results if r['status'] == 'PASS')}/{len(self.test_results)} passed")
        logger.info("=" * 60)
        
        return all_passed

    def generate_report(self):
        """Generate test report for Jenkins/CI systems"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed': sum(1 for r in self.test_results if r['status'] == 'PASS'),
            'failed': sum(1 for r in self.test_results if r['status'] == 'FAIL'),
            'tests': self.test_results
        }
        
        # Write JSON report for CI systems
        with open('integration-test-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to integration-test-report.json")
        return report

def main():
    tester = IntegrationTester()
    success = tester.run_all_tests()
    tester.generate_report()
    
    # Exit with appropriate code for Jenkins/CI
    exit_code = 0 if success else 1
    logger.info(f"Integration tests completed with exit code: {exit_code}")
    sys.exit(exit_code)

if __name__ == '__main__':
    main()