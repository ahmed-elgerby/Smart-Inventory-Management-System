-- ============================================================
-- Inventory Management System — Database v2
-- NEW: item_locations (multi-warehouse stock per product)
-- NEW: Admin user delete support (ON DELETE SET NULL on activity_log)
-- ============================================================

DROP TABLE IF EXISTS activity_log  CASCADE;
DROP TABLE IF EXISTS alerts        CASCADE;
DROP TABLE IF EXISTS item_locations CASCADE;
DROP TABLE IF EXISTS items         CASCADE;
DROP TABLE IF EXISTS users         CASCADE;
DROP TABLE IF EXISTS locations     CASCADE;

-- ── Locations ────────────────────────────────────────────────────────────────
CREATE TABLE locations (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    address    TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id             SERIAL PRIMARY KEY,
    username       VARCHAR(100) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(255) NOT NULL,
    email          VARCHAR(255),
    phone          VARCHAR(20),
    role           VARCHAR(20) NOT NULL CHECK (role IN ('admin','manager','employee')),
    location_id    INTEGER REFERENCES locations(id),
    photo          BYTEA,
    photo_filename VARCHAR(255),
    created_at     TIMESTAMP DEFAULT NOW(),
    last_login     TIMESTAMP
);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role     ON users(role);
CREATE INDEX idx_users_location ON users(location_id);

-- ── Items ────────────────────────────────────────────────────────────────────
CREATE TABLE items (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    sku          VARCHAR(100) UNIQUE,
    quantity     INTEGER NOT NULL DEFAULT 0,   -- kept in sync with SUM(item_locations.quantity)
    min_quantity INTEGER NOT NULL DEFAULT 10,
    price        DECIMAL(10,2) DEFAULT 0.00,
    category     VARCHAR(100),
    location_id  INTEGER REFERENCES locations(id),  -- legacy / primary location
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_items_category  ON items(category);
CREATE INDEX idx_items_low_stock ON items(quantity, min_quantity);
CREATE INDEX idx_items_sku       ON items(sku);
CREATE INDEX idx_items_location  ON items(location_id);

-- ── Item-Locations (multi-warehouse) ─────────────────────────────────────────
CREATE TABLE item_locations (
    id          SERIAL PRIMARY KEY,
    item_id     INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    quantity    INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (item_id, location_id)
);
CREATE INDEX idx_il_item     ON item_locations(item_id);
CREATE INDEX idx_il_location ON item_locations(location_id);

-- ── Alerts ───────────────────────────────────────────────────────────────────
CREATE TABLE alerts (
    id          SERIAL PRIMARY KEY,
    item_id     INTEGER REFERENCES items(id) ON DELETE CASCADE,
    alert_type  VARCHAR(50) NOT NULL,
    message     TEXT NOT NULL,
    status      VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','resolved')),
    created_at  TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);
CREATE INDEX idx_alerts_status  ON alerts(status);
CREATE INDEX idx_alerts_item_id ON alerts(item_id);

-- ── Activity Log ──────────────────────────────────────────────────────────────
CREATE TABLE activity_log (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     VARCHAR(255) NOT NULL,
    details    TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_al_user_id    ON activity_log(user_id);
CREATE INDEX idx_al_created_at ON activity_log(created_at DESC);

-- ══════════════════════════════════════════════════════════════════════════════
-- SEED DATA
-- ══════════════════════════════════════════════════════════════════════════════

INSERT INTO locations (name, address) VALUES
    ('Warehouse A', '123 Main Street, Downtown'),
    ('Warehouse B', '456 Industrial Blvd, North Side'),
    ('Warehouse C', '789 Storage Ave, South District');

-- Passwords: admin123 / manager123 / employee123
INSERT INTO users (username, password_hash, full_name, email, phone, role, location_id) VALUES
('admin',
 'scrypt:32768:8:1$f0tkDfwylkeMIeHN$74896fa5d07ab5f9f848e576f54d25e5c9e21793de226d1d716df44d302c97cc6e97f53613d5850692536cd129f5e00184fd309b20ab65a01768b193db2c5f75',
 'System Administrator', 'admin@inventory.com', '+1 (555) 001-0001', 'admin', NULL),

('manager',
 'scrypt:32768:8:1$iS2QmaW8zwKN99WA$a06bfeb430596ebbf66017a8d8e560247a716647bb4a2751f3335b6b5b7338e2119ee04c95bcd0f85fede963022e4d59819e7653a58c564cac54a5cd68a2e5cb',
 'Warehouse Manager', 'manager@inventory.com', '+1 (555) 002-0002', 'manager',
 (SELECT id FROM locations WHERE name='Warehouse A')),

('employee1',
 'scrypt:32768:8:1$6c857KhPBf9dOjjv$4fda47c728225360d03132f9be249910102ee949d2e63686d2c0c911471b71aded99a101ddbe00411772e9a7074f05bc6c650af8b9ea542b18003e2cde81fc17',
 'John Employee A', 'john@inventory.com', '+1 (555) 111-1111', 'employee',
 (SELECT id FROM locations WHERE name='Warehouse A')),

('employee2',
 'scrypt:32768:8:1$ivaRJm7hhVbWqTcM$7e0418863e3e59f27f25599953a803d7314108e630a301eafe98d244228f812c2b35c32265a9cfaf07af1bc54b4465aa30e88f012eabce699244390325a520a7',
 'Sarah Employee B', 'sarah@inventory.com', '+1 (555) 222-2222', 'employee',
 (SELECT id FROM locations WHERE name='Warehouse B'));

-- ── Items (15 products) ───────────────────────────────────────────────────────
INSERT INTO items (name, sku, quantity, min_quantity, price, category, location_id) VALUES
('Laptop Dell XPS 15',        'LPT-001', 70,  10, 1299.99, 'Electronics', (SELECT id FROM locations WHERE name='Warehouse A')),
('Wireless Mouse Logitech',   'MOU-001', 200, 50,   29.99, 'Electronics', (SELECT id FROM locations WHERE name='Warehouse A')),
('USB-C Cable 2m',            'CBL-001',   8, 20,   12.99, 'Accessories', (SELECT id FROM locations WHERE name='Warehouse B')),
('Office Chair Ergonomic',    'CHR-001',  40, 15,  249.99, 'Furniture',   (SELECT id FROM locations WHERE name='Warehouse C')),
('Notebook A4 100 Pages',     'NBK-001',   0, 50,    3.99, 'Stationery',  (SELECT id FROM locations WHERE name='Warehouse B')),
('Mechanical Keyboard RGB',   'KBD-001',  55, 20,   89.99, 'Electronics', (SELECT id FROM locations WHERE name='Warehouse A')),
('27" Monitor 4K',            'MON-001',  30, 10,  399.99, 'Electronics', (SELECT id FROM locations WHERE name='Warehouse A')),
('Desk Lamp LED',             'LMP-001',  90, 30,   34.99, 'Furniture',   (SELECT id FROM locations WHERE name='Warehouse C')),
('Printer Paper A4 (500)',    'PPR-001',   5, 15,    8.99, 'Stationery',  (SELECT id FROM locations WHERE name='Warehouse B')),
('Ethernet Cable Cat6 5m',    'CBL-002', 130, 40,   15.99, 'Accessories', (SELECT id FROM locations WHERE name='Warehouse B')),
('Webcam HD 1080p',           'CAM-001',  22, 10,   79.99, 'Electronics', (SELECT id FROM locations WHERE name='Warehouse A')),
('Desk Organizer',            'ORG-001',  40, 20,   19.99, 'Stationery',  (SELECT id FROM locations WHERE name='Warehouse B')),
('Standing Desk Converter',   'DSK-001',  18,  8,  199.99, 'Furniture',   (SELECT id FROM locations WHERE name='Warehouse C')),
('HDMI Cable 3m',             'CBL-003',  95, 30,   18.99, 'Accessories', (SELECT id FROM locations WHERE name='Warehouse B')),
('Wireless Headphones',       'AUD-001',  45, 15,  149.99, 'Electronics', (SELECT id FROM locations WHERE name='Warehouse A'));

-- ── item_locations: each item distributed across warehouses ──────────────────
-- Laptops: A=45, B=25
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='LPT-001'), (SELECT id FROM locations WHERE name='Warehouse A'), 45),
((SELECT id FROM items WHERE sku='LPT-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 25);

-- Mice: A=150, C=50
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='MOU-001'), (SELECT id FROM locations WHERE name='Warehouse A'), 150),
((SELECT id FROM items WHERE sku='MOU-001'), (SELECT id FROM locations WHERE name='Warehouse C'), 50);

-- USB-C Cable: B=8
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='CBL-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 8);

-- Chair: C=40
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='CHR-001'), (SELECT id FROM locations WHERE name='Warehouse C'), 40);

-- Notebook: B=0 (out of stock)
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='NBK-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 0);

-- Keyboards: A=35, B=20
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='KBD-001'), (SELECT id FROM locations WHERE name='Warehouse A'), 35),
((SELECT id FROM items WHERE sku='KBD-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 20);

-- Monitors: A=18, B=12
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='MON-001'), (SELECT id FROM locations WHERE name='Warehouse A'), 18),
((SELECT id FROM items WHERE sku='MON-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 12);

-- Desk Lamp: C=60, B=30
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='LMP-001'), (SELECT id FROM locations WHERE name='Warehouse C'), 60),
((SELECT id FROM items WHERE sku='LMP-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 30);

-- Printer Paper: B=5
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='PPR-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 5);

-- Ethernet Cable: B=95, C=35
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='CBL-002'), (SELECT id FROM locations WHERE name='Warehouse B'), 95),
((SELECT id FROM items WHERE sku='CBL-002'), (SELECT id FROM locations WHERE name='Warehouse C'), 35);

-- Webcam: A=22
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='CAM-001'), (SELECT id FROM locations WHERE name='Warehouse A'), 22);

-- Desk Organizer: B=40
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='ORG-001'), (SELECT id FROM locations WHERE name='Warehouse B'), 40);

-- Standing Desk: C=12, A=6
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='DSK-001'), (SELECT id FROM locations WHERE name='Warehouse C'), 12),
((SELECT id FROM items WHERE sku='DSK-001'), (SELECT id FROM locations WHERE name='Warehouse A'),  6);

-- HDMI Cable: B=65, A=30
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='CBL-003'), (SELECT id FROM locations WHERE name='Warehouse B'), 65),
((SELECT id FROM items WHERE sku='CBL-003'), (SELECT id FROM locations WHERE name='Warehouse A'), 30);

-- Headphones: A=28, C=17
INSERT INTO item_locations (item_id, location_id, quantity) VALUES
((SELECT id FROM items WHERE sku='AUD-001'), (SELECT id FROM locations WHERE name='Warehouse A'), 28),
((SELECT id FROM items WHERE sku='AUD-001'), (SELECT id FROM locations WHERE name='Warehouse C'), 17);

-- Sync items.quantity with sum of item_locations
UPDATE items i
SET quantity = (
    SELECT COALESCE(SUM(il.quantity), i.quantity)
    FROM item_locations il
    WHERE il.item_id = i.id
);

-- ── Alerts ────────────────────────────────────────────────────────────────────
INSERT INTO alerts (item_id, alert_type, message, status)
SELECT id, 'low_stock',
       CONCAT(name, ' is running low (Current: ', quantity, ', Min: ', min_quantity, ')'),
       'active'
FROM items WHERE quantity < min_quantity AND quantity > 0;

INSERT INTO alerts (item_id, alert_type, message, status)
SELECT id, 'out_of_stock', CONCAT(name, ' is OUT OF STOCK!'), 'active'
FROM items WHERE quantity = 0;

-- ── Activity Log ─────────────────────────────────────────────────────────────
INSERT INTO activity_log (user_id, action, details) VALUES
((SELECT id FROM users WHERE username='admin'),   'Database initialized', 'v2 setup with item_locations'),
((SELECT id FROM users WHERE username='admin'),   'Sample data created',  '15 items across 3 locations with multi-warehouse stock'),
((SELECT id FROM users WHERE username='manager'), 'User account created',  'Manager assigned to Warehouse A');

-- ── Auto-update trigger ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_item_locations_updated_at
    BEFORE UPDATE ON item_locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── Views ─────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW inventory_by_location AS
SELECT l.id AS location_id, l.name AS location_name, l.address,
       COUNT(DISTINCT il.item_id)                       AS unique_items,
       COALESCE(SUM(il.quantity), 0)                    AS total_quantity,
       COALESCE(SUM(il.quantity * i.price), 0)          AS total_value,
       COUNT(CASE WHEN il.quantity < i.min_quantity THEN 1 END) AS low_stock_count,
       COUNT(CASE WHEN il.quantity = 0             THEN 1 END) AS out_of_stock_count
FROM locations l
LEFT JOIN item_locations il ON l.id = il.location_id
LEFT JOIN items i           ON il.item_id = i.id
GROUP BY l.id, l.name, l.address
ORDER BY l.name;

-- ── Permissions ──────────────────────────────────────────────────────────────
GRANT ALL PRIVILEGES ON ALL TABLES   IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ── Summary ───────────────────────────────────────────────────────────────────
SELECT '✓ Database v2 ready!' AS status;
SELECT COUNT(*) AS locations  FROM locations;
SELECT COUNT(*) AS users      FROM users;
SELECT COUNT(*) AS items      FROM items;
SELECT COUNT(*) AS item_stocks FROM item_locations;
SELECT COUNT(*) AS alerts      FROM alerts WHERE status='active';

SELECT '📋 CREDENTIALS' AS info, username,
    CASE WHEN username='admin'      THEN 'admin123'
         WHEN username='manager'    THEN 'manager123'
         WHEN username LIKE 'employee%' THEN 'employee123'
    END AS password, role, phone,
    (SELECT name FROM locations WHERE id=users.location_id) AS location
FROM users
ORDER BY CASE role WHEN 'admin' THEN 1 WHEN 'manager' THEN 2 ELSE 3 END;
