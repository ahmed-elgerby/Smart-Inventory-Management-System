# Alert Service for Real-time Notifications
# Handles alert generation, retrieval, and status management

import psycopg2
import psycopg2.extras
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'inventory'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )
    return conn

def get_active_alerts():
    """Get all active alerts across the system"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT 
            a.id,
            a.alert_type,
            a.message,
            a.created_at,
            i.id as item_id,
            i.name as item_name,
            i.quantity,
            i.min_quantity,
            i.category
        FROM alerts a
        JOIN items i ON a.item_id = i.id
        WHERE a.status = 'active'
        ORDER BY 
            CASE 
                WHEN a.alert_type = 'out_of_stock' THEN 1
                WHEN a.alert_type = 'low_stock' THEN 2
                ELSE 3
            END,
            a.created_at DESC
    ''')
    alerts = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(a) for a in alerts]

def create_alert_for_item(item_id, alert_type, message):
    """Create a new alert"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO alerts (item_id, alert_type, message, status, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        ''', (item_id, alert_type, message, 'active'))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def resolve_alert(alert_id):
    """Mark alert as resolved"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE alerts 
            SET status = 'resolved', resolved_at = NOW()
            WHERE id = %s
        ''', (alert_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def check_and_create_alerts_for_item(item_id, item_name, quantity, min_quantity):
    """Check if item needs alerts and create them"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Check existing active alerts for this item
        cur.execute('''
            SELECT alert_type FROM alerts 
            WHERE item_id = %s AND status = 'active'
        ''', (item_id,))
        existing_alerts = [row['alert_type'] for row in cur.fetchall()]
        
        # Determine what alerts are needed
        if quantity == 0:
            # Out of stock
            if 'out_of_stock' not in existing_alerts:
                cur.execute('''
                    INSERT INTO alerts (item_id, alert_type, message, status, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                ''', (item_id, 'out_of_stock', f'{item_name} is OUT OF STOCK!', 'active'))
            # Resolve low stock if it was there
            cur.execute('''
                UPDATE alerts 
                SET status = 'resolved', resolved_at = NOW()
                WHERE item_id = %s AND alert_type = 'low_stock' AND status = 'active'
            ''', (item_id,))
        elif quantity < min_quantity:
            # Low stock
            if 'low_stock' not in existing_alerts:
                cur.execute('''
                    INSERT INTO alerts (item_id, alert_type, message, status, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                ''', (item_id, 'low_stock', f'{item_name} is running low (Current: {quantity}, Min: {min_quantity})', 'active'))
            # Resolve out of stock if it was there
            cur.execute('''
                UPDATE alerts 
                SET status = 'resolved', resolved_at = NOW()
                WHERE item_id = %s AND alert_type = 'out_of_stock' AND status = 'active'
            ''', (item_id,))
        else:
            # In stock - resolve any alerts
            cur.execute('''
                UPDATE alerts 
                SET status = 'resolved', resolved_at = NOW()
                WHERE item_id = %s AND status = 'active'
            ''', (item_id,))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_alert_count():
    """Get count of active alerts"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as count FROM alerts WHERE status = %s', ('active',))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count
