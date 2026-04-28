import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "procurement.db")


def connect_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def create_schema():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendor (
        vendor_id   TEXT PRIMARY KEY,
        name        TEXT,
        email       TEXT,
        phone       TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_order (
        po_number   TEXT PRIMARY KEY,
        vendor_id   TEXT,
        order_date  DATE,
        FOREIGN KEY (vendor_id) REFERENCES vendor(vendor_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_order_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number   TEXT,
        item_code   TEXT,
        quantity    REAL,
        unit_price  REAL,
        FOREIGN KEY (po_number) REFERENCES purchase_order(po_number)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goods_receipt (
        gr_number   TEXT PRIMARY KEY,
        po_number   TEXT,
        receipt_date DATE,
        FOREIGN KEY (po_number) REFERENCES purchase_order(po_number)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goods_receipt_items (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        gr_number           TEXT,
        item_code           TEXT,
        quantity_received   REAL,
        FOREIGN KEY (gr_number) REFERENCES goods_receipt(gr_number)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice (
        invoice_no      TEXT PRIMARY KEY,
        po_number       TEXT,
        vendor_id       TEXT,
        invoice_date    DATE,
        total_amount    REAL,
        status          TEXT DEFAULT 'Pending',
        date_received   DATE,
        amount_paid     REAL DEFAULT 0,
        FOREIGN KEY (po_number) REFERENCES purchase_order(po_number),
        FOREIGN KEY (vendor_id) REFERENCES vendor(vendor_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no  TEXT,
        item_code   TEXT,
        quantity    REAL,
        unit_price  REAL,
        FOREIGN KEY (invoice_no) REFERENCES invoice(invoice_no)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_status (
        po_id   TEXT PRIMARY KEY,
        status  TEXT,
        details TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no      TEXT,
        payment_date    DATE,
        amount_paid     REAL,
        status          TEXT DEFAULT 'Paid',
        FOREIGN KEY (invoice_no) REFERENCES invoice(invoice_no)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exceptions (
        exception_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number       TEXT,
        issue_type      TEXT,
        details         TEXT,
        status          TEXT DEFAULT 'Open',
        timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        message     TEXT,
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_schema()
    print("Database schema created successfully.")
