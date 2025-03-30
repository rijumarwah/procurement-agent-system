import sqlite3

DB_PATH = '/path/to/your/database.db'

def connect_db():
    return sqlite3.connect(DB_PATH)

def create_schema():
    conn = connect_db()
    cursor = conn.cursor()

    # Create invoice table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice (
        invoice_no TEXT PRIMARY KEY,
        po_number TEXT,
        vendor_id TEXT,
        invoice_date DATE,
        total_amount REAL,
        status TEXT DEFAULT 'Pending',
        date_received DATE,
        amount_paid REAL DEFAULT 0
    );
    """)

    # Create match_status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_status (
        po_id TEXT PRIMARY KEY,
        status TEXT,
        details TEXT
    );
    """)

    # Create exceptions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exceptions (
        exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number TEXT,
        issue_type TEXT,
        details TEXT,
        status TEXT DEFAULT 'Open',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create payments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        payment_date DATE,
        amount_paid REAL,
        status TEXT DEFAULT 'Paid',
        FOREIGN KEY (invoice_no) REFERENCES invoice(invoice_no)
    );
    """)

    # Create logs table (optional)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_schema()
    print("Database schema created successfully.")
