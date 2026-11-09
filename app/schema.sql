CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('cliente', 'mesero', 'admin'))
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price REAL NOT NULL CHECK (price > 0),
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE (category_id, name)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number INTEGER NOT NULL,
    customer_id INTEGER REFERENCES users(id),
    created_by INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'recibido',
    total REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    dish_id INTEGER NOT NULL REFERENCES dishes(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL,
    notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    status TEXT NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES users(id),
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    table_number INTEGER NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    guests INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'activa'
);
CREATE TABLE IF NOT EXISTS cash_registers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_by INTEGER NOT NULL REFERENCES users(id),
    opening_amount REAL NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    counted_amount REAL,
    expected_amount REAL,
    difference REAL
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
    register_id INTEGER NOT NULL REFERENCES cash_registers(id),
    method TEXT NOT NULL CHECK (method IN ('efectivo', 'tarjeta', 'transferencia')),
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
