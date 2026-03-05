# Reporting Microservice v2 — port 5002
# Fixed: uses l.name via JOIN instead of i.location column
# Fixed: activity_log now shows item names from details parsing
# Added: /reports/activity-log returns item_name extracted from details

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2, psycopg2.extras, os, re
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST','localhost'),
        database=os.getenv('DB_NAME','inventory'),
        user=os.getenv('DB_USER','postgres'),
        password=os.getenv('DB_PASSWORD','postgres'),
        port=os.getenv('DB_PORT', 5432),
    )

# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reports/inventory-summary', methods=['GET'])
def inventory_summary():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('''
            SELECT COUNT(*) as total_items,
                   COALESCE(SUM(quantity),0) as total_quantity,
                   COALESCE(SUM(price*quantity),0) as total_value,
                   COUNT(CASE WHEN quantity=0 THEN 1 END) as out_of_stock_count,
                   COUNT(CASE WHEN quantity<min_quantity THEN 1 END) as low_stock_count,
                   COUNT(CASE WHEN quantity>=min_quantity THEN 1 END) as healthy_stock_count
            FROM items''')
        summary = dict(cur.fetchone())

        cur.execute('''
            SELECT i.category, COUNT(*) as item_count,
                   COALESCE(SUM(i.quantity),0) as total_qty,
                   COALESCE(SUM(i.price*i.quantity),0) as total_value,
                   COUNT(CASE WHEN i.quantity<i.min_quantity THEN 1 END) as low_stock,
                   COUNT(CASE WHEN i.quantity=0 THEN 1 END) as out_of_stock
            FROM items i WHERE i.category IS NOT NULL
            GROUP BY i.category ORDER BY total_value DESC''')
        categories = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT i.id, i.name, i.quantity, i.min_quantity, i.price,
                   (i.quantity*i.price) as total_value, i.category,
                   l.name as location_name
            FROM items i LEFT JOIN locations l ON i.location_id=l.id
            ORDER BY (i.quantity*i.price) DESC LIMIT 10''')
        top_items = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT i.id, i.name, i.quantity, i.min_quantity,
                   (i.min_quantity-i.quantity) as needed,
                   i.category, l.name as location_name
            FROM items i LEFT JOIN locations l ON i.location_id=l.id
            WHERE i.quantity < i.min_quantity
            ORDER BY (i.min_quantity-i.quantity) DESC''')
        low_stock = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT i.id, i.name, i.min_quantity, i.category, l.name as location_name
            FROM items i LEFT JOIN locations l ON i.location_id=l.id
            WHERE i.quantity=0 ORDER BY i.min_quantity DESC''')
        out_of_stock = [dict(r) for r in cur.fetchall()]

        cur.close(); conn.close()
        return jsonify({
            'report_type': 'inventory_summary', 'generated_at': datetime.now().isoformat(),
            'summary': summary, 'categories': categories,
            'top_10_items': top_items, 'low_stock_items': low_stock, 'out_of_stock_items': out_of_stock,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════════════════════
# ALERTS REPORT
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reports/alerts-detail', methods=['GET'])
def alerts_detail():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('''
            SELECT a.id, a.alert_type, a.message, a.created_at,
                   i.id as item_id, i.name as item_name, i.quantity, i.min_quantity,
                   i.category, l.name as location_name,
                   EXTRACT(EPOCH FROM (NOW()-a.created_at))/3600 as hours_active
            FROM alerts a
            JOIN items i ON a.item_id=i.id
            LEFT JOIN locations l ON i.location_id=l.id
            WHERE a.status='active' ORDER BY a.created_at DESC''')
        active = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT COUNT(*) as total_alerts,
                   COUNT(CASE WHEN status='active' THEN 1 END) as active_count,
                   COUNT(CASE WHEN status='resolved' THEN 1 END) as resolved_count,
                   COUNT(CASE WHEN alert_type='out_of_stock' THEN 1 END) as out_of_stock_count,
                   COUNT(CASE WHEN alert_type='low_stock' THEN 1 END) as low_stock_count
            FROM alerts''')
        stats = dict(cur.fetchone())

        cur.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count,
                   COUNT(CASE WHEN alert_type='out_of_stock' THEN 1 END) as out_of_stock,
                   COUNT(CASE WHEN alert_type='low_stock' THEN 1 END) as low_stock
            FROM alerts WHERE created_at >= NOW()-INTERVAL '30 days'
            GROUP BY DATE(created_at) ORDER BY date''')
        trend = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT a.id, a.alert_type, a.message, a.created_at, a.resolved_at,
                   EXTRACT(EPOCH FROM (a.resolved_at-a.created_at))/3600 as hours_to_resolve,
                   i.name as item_name
            FROM alerts a JOIN items i ON a.item_id=i.id
            WHERE a.status='resolved' ORDER BY a.resolved_at DESC LIMIT 10''')
        resolved = [dict(r) for r in cur.fetchall()]

        cur.close(); conn.close()
        return jsonify({
            'report_type': 'alerts_detail', 'generated_at': datetime.now().isoformat(),
            'statistics': stats, 'active_alerts': active,
            'alert_trend_30days': trend, 'recently_resolved': resolved,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITY LOG — includes item names extracted from details
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reports/activity-log', methods=['GET'])
def activity_log():
    limit = request.args.get('limit', 1000, type=int)
    days  = request.args.get('days',  30,   type=int)

    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('''
            SELECT al.id, al.action, al.details, al.created_at,
                   u.username, u.full_name, u.role
            FROM activity_log al
            LEFT JOIN users u ON al.user_id=u.id
            WHERE al.created_at >= NOW() - INTERVAL %s
            ORDER BY al.created_at DESC
            LIMIT %s
        ''', (f'{days} days', limit))
        logs_raw = [dict(r) for r in cur.fetchall()]

        # Enrich: for item-related actions, try to pull item name
        for log in logs_raw:
            log['item_name'] = None
            if log.get('details'):
                # Try to extract item ID from details like "Updated item ID: 5" or "Added: Laptop Dell XPS 15"
                id_match   = re.search(r'[Ii]tem\s+(?:ID[:\s]+)?(\d+)', log['details'])
                name_match = re.search(r'(?:Added|Deleted|Updated item|Stock)[:,]?\s+(.+?)(?:\s+\(ID|\s*$)', log['details'])
                if name_match:
                    log['item_name'] = name_match.group(1).strip()
                elif id_match:
                    item_id = int(id_match.group(1))
                    cur.execute('SELECT name FROM items WHERE id=%s', (item_id,))
                    row = cur.fetchone()
                    if row: log['item_name'] = row['name']

        # Per-user stats
        cur.execute('''
            SELECT u.username, u.full_name, COUNT(*) as action_count
            FROM activity_log al LEFT JOIN users u ON al.user_id=u.id
            WHERE al.created_at >= NOW()-INTERVAL %s
            GROUP BY u.username, u.full_name ORDER BY action_count DESC
        ''', (f'{days} days',))
        by_user = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT action, COUNT(*) as count
            FROM activity_log WHERE created_at >= NOW()-INTERVAL %s
            GROUP BY action ORDER BY count DESC LIMIT 20
        ''', (f'{days} days',))
        by_action = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as total_actions
            FROM activity_log WHERE created_at >= NOW()-INTERVAL %s
            GROUP BY DATE(created_at) ORDER BY date
        ''', (f'{days} days',))
        daily = [dict(r) for r in cur.fetchall()]

        cur.close(); conn.close()
        return jsonify({
            'report_type': 'activity_log', 'generated_at': datetime.now().isoformat(),
            'period_days': days, 'log_entries': logs_raw,
            'activity_by_user': by_user, 'action_distribution': by_action, 'daily_trend': daily,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE REPORT
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reports/comprehensive', methods=['GET'])
def comprehensive():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('''SELECT COUNT(*) as total_items, COALESCE(SUM(quantity),0) as total_qty,
                              COALESCE(SUM(price*quantity),0) as total_value,
                              COUNT(CASE WHEN quantity=0 THEN 1 END) as out_of_stock,
                              COUNT(CASE WHEN quantity<min_quantity THEN 1 END) as low_stock
                       FROM items''')
        inventory = dict(cur.fetchone())

        cur.execute('''SELECT COUNT(*) as total_alerts,
                              COUNT(CASE WHEN status='active' THEN 1 END) as active,
                              COUNT(CASE WHEN status='resolved' THEN 1 END) as resolved
                       FROM alerts''')
        alerts = dict(cur.fetchone())

        cur.execute('''SELECT COUNT(*) as total_users,
                              COUNT(CASE WHEN role='admin' THEN 1 END) as admins,
                              COUNT(CASE WHEN role='manager' THEN 1 END) as managers,
                              COUNT(CASE WHEN role='employee' THEN 1 END) as employees
                       FROM users''')
        users = dict(cur.fetchone())

        cur.execute('''SELECT i.category, COUNT(*) as items,
                              COALESCE(SUM(i.quantity),0) as total_qty,
                              COALESCE(SUM(i.price*i.quantity),0) as value
                       FROM items i WHERE i.category IS NOT NULL
                       GROUP BY i.category ORDER BY value DESC LIMIT 5''')
        top_cats = [dict(r) for r in cur.fetchall()]

        cur.execute('''SELECT
                        (SELECT COUNT(*) FROM alerts WHERE status='active') as active_alerts,
                        (SELECT COUNT(*) FROM items WHERE quantity=0) as out_of_stock_items,
                        (SELECT COUNT(*) FROM activity_log WHERE created_at>=NOW()-INTERVAL '1 day') as actions_24h''')
        health = dict(cur.fetchone())

        cur.close(); conn.close()
        return jsonify({
            'report_type': 'comprehensive', 'generated_at': datetime.now().isoformat(),
            'inventory_overview': inventory, 'alerts_overview': alerts,
            'users_overview': users, 'top_categories': top_cats, 'system_health': health,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════════════════════
# PERIOD COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reports/period-comparison', methods=['GET'])
def period_comparison():
    p1 = request.args.get('period1_days', 7, type=int)
    p2 = request.args.get('period2_days', 7, type=int)
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        def get_period(start_days, end_days=0):
            if end_days:
                cur.execute('''SELECT COUNT(*) as total_actions, COUNT(DISTINCT user_id) as active_users
                               FROM activity_log WHERE created_at >= NOW()-INTERVAL %s AND created_at < NOW()-INTERVAL %s''',
                            (f'{start_days} days', f'{end_days} days'))
            else:
                cur.execute('''SELECT COUNT(*) as total_actions, COUNT(DISTINCT user_id) as active_users
                               FROM activity_log WHERE created_at >= NOW()-INTERVAL %s''',
                            (f'{start_days} days',))
            return dict(cur.fetchone() or {})

        period1 = get_period(p1)
        period2 = get_period(p1+p2, p1)
        cur.close(); conn.close()
        return jsonify({
            'report_type': 'period_comparison', 'generated_at': datetime.now().isoformat(),
            f'period1_last_{p1}_days': period1,
            f'period2_days_{p1}_to_{p1+p2}': period2,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'reporting', 'version': '2.0'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    print(f'Reporting service v2 running on port {port}')
    app.run(host='0.0.0.0', port=port, debug=True)
