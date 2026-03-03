# Enhanced Inventory Service v2
# NEW FEATURES vs previous version:
#   1. Multi-warehouse: item_locations table — one product in many warehouses
#   2. Admin: DELETE /users/<id> and full user edit
#   3. Alert microservice fully integrated (check_and_create_alerts_for_item)
#   4. Reports endpoints bridge (REPORT_BASE forwarding kept in alert service)
#   5. /items/<id>/locations CRUD endpoints

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os, jwt, datetime, io
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# ── Alert service integration ────────────────────────────────────────────────
try:
    from alert_service import check_and_create_alerts_for_item, get_alert_count
except ImportError:
    def check_and_create_alerts_for_item(*a, **k): pass
    def get_alert_count(): return 0

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY']          = os.getenv('SECRET_KEY', 'change-this-secret-key')
app.config['UPLOAD_FOLDER']       = '/tmp/uploads'
app.config['MAX_CONTENT_LENGTH']  = 5 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'inventory'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'yourpassword'),
        port=os.getenv('DB_PORT', 5432),
    )

# ── Schema bootstrap ─────────────────────────────────────────────────────────
def init_db():
    conn = get_db(); cur = conn.cursor()

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
        created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW())''')

    # ── NEW: multi-warehouse stock table ──────────────────────────────────────
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

    conn.commit()

    # Seed default location
    cur.execute('SELECT COUNT(*) FROM locations')
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO locations (name, address) VALUES ('Main Warehouse','123 Main St')")
        conn.commit()

    # Seed default admin
    cur.execute('SELECT COUNT(*) FROM users')
    if cur.fetchone()[0] == 0:
        cur.execute('INSERT INTO users (username,password_hash,full_name,role) VALUES (%s,%s,%s,%s)',
                    ('admin', generate_password_hash('admin123'), 'System Administrator', 'admin'))
        conn.commit()
        print('Default admin created: admin / admin123')

    cur.close(); conn.close()

# ── Auth decorators ───────────────────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '): token = token[7:]
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return f(data['user_id'], data['role'], data.get('location_id'), *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    return decorated

def manager_required(f):
    @wraps(f)
    @token_required
    def decorated(uid, role, loc, *args, **kwargs):
        if role not in ('admin', 'manager'):
            return jsonify({'error': 'Manager or admin required'}), 403
        return f(uid, role, loc, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(uid, role, loc, *args, **kwargs):
        if role != 'admin':
            return jsonify({'error': 'Admin required'}), 403
        return f(uid, role, loc, *args, **kwargs)
    return decorated

# helper
def log_activity(cur, user_id, action, details=None):
    cur.execute('INSERT INTO activity_log (user_id,action,details) VALUES (%s,%s,%s)',
                (user_id, action, details))

# ═════════════════════════════════════════════════════════════════════════════
# AUTH
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''SELECT u.*, l.name AS location_name
                   FROM users u LEFT JOIN locations l ON u.location_id = l.id
                   WHERE u.username = %s''', (data['username'],))
    user = cur.fetchone()

    if not user or not check_password_hash(user['password_hash'], data['password']):
        cur.close(); conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401

    cur.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user['id'],))
    log_activity(cur, user['id'], 'User logged in')
    conn.commit(); cur.close(); conn.close()

    token = jwt.encode({
        'user_id': user['id'], 'username': user['username'],
        'role': user['role'], 'location_id': user['location_id'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token, 'user': {
        'id': user['id'], 'username': user['username'],
        'full_name': user['full_name'], 'email': user['email'],
        'phone': user['phone'], 'role': user['role'],
        'location_id': user['location_id'], 'location_name': user.get('location_name'),
        'photo_filename': user.get('photo_filename'),
    }}), 200

@app.route('/auth/me', methods=['GET'])
@token_required
def get_me(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''SELECT u.*, l.name AS location_name
                   FROM users u LEFT JOIN locations l ON u.location_id = l.id WHERE u.id=%s''', (uid,))
    user = cur.fetchone(); cur.close(); conn.close()
    if not user: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(user)), 200

# ═════════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/locations', methods=['GET'])
@token_required
def get_locations(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM locations ORDER BY name')
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/locations', methods=['POST'])
@manager_required
def create_location(uid, role, loc):
    data = request.get_json()
    if not data.get('name'): return jsonify({'error': 'Name required'}), 400
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute('INSERT INTO locations (name,address) VALUES (%s,%s) RETURNING id',
                    (data['name'], data.get('address')))
        lid = cur.fetchone()[0]
        log_activity(cur, uid, 'Location created', f"Created: {data['name']}")
        conn.commit(); cur.close(); conn.close()
        return jsonify({'id': lid, 'message': 'Location created'}), 201
    except psycopg2.IntegrityError:
        conn.rollback(); cur.close(); conn.close()
        return jsonify({'error': 'Location name already exists'}), 400

@app.route('/locations/<int:lid>', methods=['PUT'])
@manager_required
def update_location(uid, role, loc, lid):
    data = request.get_json()
    conn = get_db(); cur = conn.cursor()
    updates, vals = [], []
    if 'name'    in data: updates.append('name=%s');    vals.append(data['name'])
    if 'address' in data: updates.append('address=%s'); vals.append(data['address'])
    if not updates: return jsonify({'error': 'Nothing to update'}), 400
    vals.append(lid)
    cur.execute(f"UPDATE locations SET {','.join(updates)} WHERE id=%s", vals)
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Updated'}), 200

# ═════════════════════════════════════════════════════════════════════════════
# USERS
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/users', methods=['GET'])
@manager_required
def get_users(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''SELECT u.id,u.username,u.full_name,u.email,u.phone,u.role,
                          u.location_id,u.photo_filename,u.created_at,u.last_login,
                          l.name as location_name
                   FROM users u LEFT JOIN locations l ON u.location_id=l.id
                   ORDER BY u.created_at DESC''')
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/users', methods=['POST'])
@manager_required
def create_user(uid, role, loc):
    data = request.get_json()
    username  = data.get('username')
    password  = data.get('password')
    full_name = data.get('full_name')
    if not username or not password or not full_name:
        return jsonify({'error': 'username, password, full_name required'}), 400

    new_role = data.get('role', 'employee')
    if new_role not in ('admin','manager','employee'):
        return jsonify({'error': 'Invalid role'}), 400
    if new_role == 'admin' and role != 'admin':
        return jsonify({'error': 'Only admins can create admin accounts'}), 403

    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE username=%s', (username,))
    if cur.fetchone():
        cur.close(); conn.close()
        return jsonify({'error': 'Username already taken'}), 400

    cur.execute('''INSERT INTO users (username,password_hash,full_name,email,phone,role,location_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                (username, generate_password_hash(password), full_name,
                 data.get('email'), data.get('phone'), new_role, data.get('location_id')))
    new_id = cur.fetchone()[0]
    log_activity(cur, uid, 'User created', f'Created user: {username}')
    conn.commit(); cur.close(); conn.close()
    return jsonify({'id': new_id, 'message': 'User created'}), 201

@app.route('/users/<int:target_id>', methods=['PUT'])
@token_required
def update_user(uid, role, loc, target_id):
    # Users can edit themselves; admins can edit anyone
    if uid != target_id and role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json()
    conn = get_db(); cur = conn.cursor()
    updates, vals = [], []

    editable = ['full_name','email','phone']
    for f in editable:
        if f in data:
            updates.append(f'{f}=%s'); vals.append(data[f])

    if 'password' in data and data['password']:
        updates.append('password_hash=%s')
        vals.append(generate_password_hash(data['password']))

    # Only admins can change role and location_id of other users
    if role == 'admin':
        if 'role' in data and data['role'] in ('admin','manager','employee'):
            updates.append('role=%s'); vals.append(data['role'])
        if 'location_id' in data:
            updates.append('location_id=%s'); vals.append(data['location_id'] or None)
    elif 'location_id' in data:
        # managers can change their own location? We'll allow it
        updates.append('location_id=%s'); vals.append(data['location_id'] or None)

    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400

    vals.append(target_id)
    cur.execute(f"UPDATE users SET {','.join(updates)} WHERE id=%s", vals)
    log_activity(cur, uid, 'User updated', f'Updated user ID: {target_id}')
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'User updated'}), 200

@app.route('/users/<int:target_id>', methods=['DELETE'])
@admin_required
def delete_user(uid, role, loc, target_id):
    if uid == target_id:
        return jsonify({'error': "Cannot delete your own account"}), 400

    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT id,username FROM users WHERE id=%s', (target_id,))
    user = cur.fetchone()
    if not user:
        cur.close(); conn.close()
        return jsonify({'error': 'User not found'}), 404

    cur.execute('DELETE FROM users WHERE id=%s', (target_id,))
    log_activity(cur, uid, 'User deleted', f'Deleted user ID: {target_id}')
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'User deleted'}), 200

@app.route('/users/<int:target_id>/photo', methods=['POST'])
@token_required
def upload_photo(uid, role, loc, target_id):
    if uid != target_id and role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo'}), 400

    file = request.files['photo']
    data = file.read()
    conn = get_db(); cur = conn.cursor()
    cur.execute('UPDATE users SET photo=%s, photo_filename=%s WHERE id=%s',
                (psycopg2.Binary(data), file.filename, target_id))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Photo uploaded'}), 200

@app.route('/users/<int:target_id>/photo', methods=['GET'])
def get_photo(target_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT photo, photo_filename FROM users WHERE id=%s', (target_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row or not row[0]:
        return jsonify({'error': 'No photo'}), 404
    return send_file(io.BytesIO(bytes(row[0])), mimetype='image/jpeg',
                     as_attachment=False, download_name=row[1] or 'photo.jpg')

# ═════════════════════════════════════════════════════════════════════════════
# CONTACTS
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/contacts', methods=['GET'])
@manager_required
def get_contacts(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''SELECT u.id, u.full_name, u.email, u.phone, u.role,
                          l.name as location_name, l.address as location_address
                   FROM users u LEFT JOIN locations l ON u.location_id=l.id
                   WHERE u.role IN ('manager','employee')
                   ORDER BY l.name, u.full_name''')
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows]), 200

# ═════════════════════════════════════════════════════════════════════════════
# ITEMS
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/items', methods=['GET'])
@token_required
def get_items(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if role == 'employee' and loc:
        # Employees see items that exist in their location (via item_locations or legacy location_id)
        cur.execute('''
            SELECT DISTINCT i.*, l.name as location_name,
                   COALESCE(
                     (SELECT SUM(il.quantity) FROM item_locations il WHERE il.item_id = i.id),
                     i.quantity
                   ) as total_quantity
            FROM items i
            LEFT JOIN locations l ON i.location_id = l.id
            WHERE i.location_id = %s
               OR i.id IN (SELECT item_id FROM item_locations WHERE location_id = %s)
            ORDER BY i.name
        ''', (loc, loc))
    else:
        cur.execute('''
            SELECT i.*, l.name as location_name,
                   COALESCE(
                     (SELECT SUM(il.quantity) FROM item_locations il WHERE il.item_id = i.id),
                     i.quantity
                   ) as total_quantity
            FROM items i
            LEFT JOIN locations l ON i.location_id = l.id
            ORDER BY i.name
        ''')
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/items', methods=['POST'])
@token_required
def add_item(uid, role, loc):
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Item name required'}), 400

    item_loc = data.get('location_id') or (loc if role == 'employee' else None)
    qty      = int(data.get('quantity', 0))
    conn = get_db(); cur = conn.cursor()

    try:
        cur.execute('''INSERT INTO items (name,sku,quantity,min_quantity,price,category,location_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                    (data['name'], data.get('sku'), qty,
                     int(data.get('min_quantity', 10)),
                     float(data.get('price', 0)),
                     data.get('category'), item_loc))
        item_id = cur.fetchone()[0]

        # Seed item_locations if we have a location
        if item_loc and qty > 0:
            cur.execute('INSERT INTO item_locations (item_id,location_id,quantity) VALUES (%s,%s,%s)',
                        (item_id, item_loc, qty))

        log_activity(cur, uid, 'Item added', f"Added: {data['name']}")
        conn.commit()

        check_and_create_alerts_for_item(item_id, data['name'], qty, int(data.get('min_quantity', 10)))
    except psycopg2.IntegrityError:
        conn.rollback(); cur.close(); conn.close()
        return jsonify({'error': 'SKU already exists'}), 400

    cur.close(); conn.close()
    return jsonify({'id': item_id, 'message': 'Item added'}), 201

@app.route('/items/<int:item_id>', methods=['PUT'])
@token_required
def update_item(uid, role, loc, item_id):
    data = request.get_json()
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute('SELECT * FROM items WHERE id=%s', (item_id,))
    item = cur.fetchone()
    if not item:
        cur.close(); conn.close()
        return jsonify({'error': 'Item not found'}), 404

    if role == 'employee' and loc and item['location_id'] != loc:
        cur.close(); conn.close()
        return jsonify({'error': 'Access denied'}), 403

    updates, vals = [], []
    for field in ('name','sku','min_quantity','price','category'):
        if field in data:
            updates.append(f'{field}=%s'); vals.append(data[field])

    if 'quantity' in data:
        new_qty = max(0, int(data['quantity']))
        updates.append('quantity=%s'); vals.append(new_qty)

    if role in ('admin','manager') and 'location_id' in data:
        updates.append('location_id=%s'); vals.append(data['location_id'])

    if not updates:
        cur.close(); conn.close()
        return jsonify({'error': 'Nothing to update'}), 400

    updates.append('updated_at=NOW()')
    vals.append(item_id)
    cur.execute(f"UPDATE items SET {','.join(updates)} WHERE id=%s", vals)
    log_activity(cur, uid, 'Item updated', f'Updated item ID: {item_id}')
    conn.commit()

    cur.execute('SELECT name,quantity,min_quantity FROM items WHERE id=%s', (item_id,))
    updated = cur.fetchone()
    cur.close(); conn.close()

    check_and_create_alerts_for_item(item_id, updated['name'], updated['quantity'], updated['min_quantity'])
    return jsonify({'message': 'Item updated'}), 200

@app.route('/items/<int:item_id>', methods=['DELETE'])
@token_required
def delete_item(uid, role, loc, item_id):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM items WHERE id=%s', (item_id,))
    item = cur.fetchone()
    if not item:
        cur.close(); conn.close()
        return jsonify({'error': 'Item not found'}), 404

    if role == 'employee' and loc and item['location_id'] != loc:
        cur.close(); conn.close()
        return jsonify({'error': 'Access denied'}), 403

    cur.execute('DELETE FROM items WHERE id=%s', (item_id,))
    log_activity(cur, uid, 'Item deleted', f"Deleted: {item['name']} (ID: {item_id})")
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Item deleted'}), 200

@app.route('/items/low-stock', methods=['GET'])
@token_required
def get_low_stock(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if role == 'employee' and loc:
        cur.execute('''SELECT i.*, l.name as location_name FROM items i
                       LEFT JOIN locations l ON i.location_id=l.id
                       WHERE i.quantity < i.min_quantity AND i.location_id=%s
                       ORDER BY i.quantity''', (loc,))
    else:
        cur.execute('''SELECT i.*, l.name as location_name FROM items i
                       LEFT JOIN locations l ON i.location_id=l.id
                       WHERE i.quantity < i.min_quantity ORDER BY i.quantity''')
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows]), 200

# ═════════════════════════════════════════════════════════════════════════════
# ITEM-LOCATION STOCK (multi-warehouse)
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/items/<int:item_id>/locations', methods=['GET'])
@token_required
def get_item_locations(uid, role, loc, item_id):
    """Return per-warehouse stock for one item."""
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''SELECT il.*, l.name as location_name, l.address as location_address
                   FROM item_locations il
                   JOIN locations l ON il.location_id = l.id
                   WHERE il.item_id = %s
                   ORDER BY l.name''', (item_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/items/<int:item_id>/locations', methods=['POST'])
@token_required
def add_item_to_location(uid, role, loc, item_id):
    """Assign an item to a new warehouse with a given quantity."""
    data = request.get_json()
    location_id = data.get('location_id')
    quantity    = int(data.get('quantity', 0))
    if not location_id:
        return jsonify({'error': 'location_id required'}), 400

    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute('''INSERT INTO item_locations (item_id, location_id, quantity)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (item_id, location_id) DO UPDATE SET quantity = EXCLUDED.quantity, updated_at = NOW()
                       RETURNING id''',
                    (item_id, location_id, quantity))
        new_id = cur.fetchone()[0]

        # Keep items.quantity in sync (sum of all locations)
        _sync_item_total(cur, item_id)
        log_activity(cur, uid, 'Stock assigned to location', f'Item {item_id} → location {location_id}: qty {quantity}')
        conn.commit()
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return jsonify({'error': str(e)}), 500

    # re-check alerts
    cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if False else get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur2.execute('SELECT name,quantity,min_quantity FROM items WHERE id=%s', (item_id,))
    it = cur2.fetchone(); cur2.close()
    if it: check_and_create_alerts_for_item(item_id, it['name'], it['quantity'], it['min_quantity'])

    cur.close(); conn.close()
    return jsonify({'id': new_id, 'message': 'Stock assigned'}), 201

@app.route('/items/<int:item_id>/locations/<int:location_id>', methods=['PUT'])
@token_required
def update_item_location_stock(uid, role, loc, item_id, location_id):
    """Update quantity for a specific warehouse."""
    data = request.get_json()
    quantity = max(0, int(data.get('quantity', 0)))

    conn = get_db(); cur = conn.cursor()
    cur.execute('''INSERT INTO item_locations (item_id, location_id, quantity)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (item_id, location_id) DO UPDATE SET quantity=%s, updated_at=NOW()''',
                (item_id, location_id, quantity, quantity))

    _sync_item_total(cur, item_id)
    log_activity(cur, uid, 'Stock updated', f'Item {item_id} @ location {location_id}: qty → {quantity}')
    conn.commit()

    cur.execute('SELECT name,quantity,min_quantity FROM items WHERE id=%s', (item_id,))
    it = cur.fetchone(); cur.close(); conn.close()
    if it: check_and_create_alerts_for_item(item_id, it[0], it[1], it[2])
    return jsonify({'message': 'Stock updated'}), 200

@app.route('/items/<int:item_id>/locations/<int:location_id>', methods=['DELETE'])
@token_required
def remove_item_from_location(uid, role, loc, item_id, location_id):
    """Remove item from a specific warehouse."""
    conn = get_db(); cur = conn.cursor()
    cur.execute('DELETE FROM item_locations WHERE item_id=%s AND location_id=%s', (item_id, location_id))
    _sync_item_total(cur, item_id)
    log_activity(cur, uid, 'Stock removed from location', f'Item {item_id} removed from location {location_id}')
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Removed from location'}), 200

def _sync_item_total(cur, item_id):
    """Keep items.quantity = SUM of item_locations.quantity."""
    cur.execute('SELECT COALESCE(SUM(quantity),0) FROM item_locations WHERE item_id=%s', (item_id,))
    total = cur.fetchone()[0]
    cur.execute('UPDATE items SET quantity=%s, updated_at=NOW() WHERE id=%s', (total, item_id))

# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/analytics/summary', methods=['GET'])
@token_required
def get_summary(uid, role, loc):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    where   = 'WHERE i.location_id = %s' if (role == 'employee' and loc) else ''
    params  = (loc,)                      if (role == 'employee' and loc) else ()
    and_kw  = 'AND'                       if where else 'WHERE'

    cur.execute(f'SELECT COUNT(*) as c FROM items i {where}', params)
    total_items = cur.fetchone()['c']

    cur.execute(f'SELECT COUNT(*) as c FROM items i {where} {and_kw} quantity < min_quantity', params)
    low_stock = cur.fetchone()['c']

    cur.execute(f'SELECT COUNT(*) as c FROM items i {where} {and_kw} quantity = 0', params)
    out_of_stock = cur.fetchone()['c']

    cur.execute(f'SELECT COALESCE(SUM(quantity*price),0) as v FROM items i {where}', params)
    inv_value = float(cur.fetchone()['v'])

    cur.execute("SELECT COUNT(*) as c FROM alerts WHERE status='active'")
    active_alerts = cur.fetchone()['c']

    cur.execute(f'''SELECT category, COUNT(*) as count FROM items i {where}
                    {and_kw} category IS NOT NULL GROUP BY category ORDER BY count DESC''', params)
    categories = cur.fetchall()

    cur.execute('''SELECT al.*, u.username, u.full_name FROM activity_log al
                   LEFT JOIN users u ON al.user_id=u.id ORDER BY al.created_at DESC LIMIT 10''')
    recent = cur.fetchall()
    cur.close(); conn.close()

    return jsonify({
        'total_items': total_items, 'low_stock_count': low_stock,
        'out_of_stock': out_of_stock, 'inventory_value': inv_value,
        'active_alerts': active_alerts,
        'categories': [dict(c) for c in categories],
        'recent_activity': [dict(a) for a in recent],
    }), 200

# ═════════════════════════════════════════════════════════════════════════════
# HEALTH / METRICS
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'inventory', 'version': '2.0'}), 200

@app.route('/metrics', methods=['GET'])
def metrics():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM items');          ti = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM items WHERE quantity < min_quantity'); ls = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM users');          tu = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM locations');      tl = cur.fetchone()[0]
        cur.close(); conn.close()
        out = f"""# inventory metrics
inventory_total_items {ti}
inventory_low_stock {ls}
inventory_total_users {tu}
inventory_total_locations {tl}
"""
        return out, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return f"# error: {e}\n", 500, {'Content-Type': 'text/plain'}

# ═════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print('='*55)
    print('Inventory Service v2 ready')
    print('  Ports: main=5000  alerts=5001  reports=5002')
    print('  New:   Multi-warehouse item_locations table')
    print('  New:   Admin user edit/delete')
    print('  New:   Full alert microservice integration')
    print('='*55)
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
