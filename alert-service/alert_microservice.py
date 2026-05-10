from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from prometheus_client import Gauge, generate_latest

# Import the alert logic
from alert_service import get_active_alerts, resolve_alert

app = Flask(__name__)
CORS(app)

# Prometheus metrics
active_alerts = Gauge('alert_service_active_alerts', 'Number of active alerts')

@app.route('/metrics')
def metrics():
    # Update metrics
    try:
        alerts = get_active_alerts()
        active_alerts.set(len(alerts))
    except:
        active_alerts.set(0)
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/alerts', methods=['GET'])
def alerts():
    try:
        data = get_active_alerts()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve(alert_id):
    try:
        resolve_alert(alert_id)
        return jsonify({'message': 'Alert resolved'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
