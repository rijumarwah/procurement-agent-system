"""Populate the database with a small sample dataset for local testing.

Run this once after `python schema.py` to get a working demo:

    python schema.py
    python seed_data.py
"""

from run_sql import run_sql


def seed():
    # Vendors
    run_sql("INSERT OR IGNORE INTO vendor (vendor_id, name, email) VALUES ('V001', 'Acme Supplies', 'accounts@acme.com')")
    run_sql("INSERT OR IGNORE INTO vendor (vendor_id, name, email) VALUES ('V002', 'Global Parts Ltd', 'billing@globalparts.com')")

    # Purchase orders
    run_sql("INSERT OR IGNORE INTO purchase_order (po_number, vendor_id, order_date) VALUES ('PO1001', 'V001', '2024-01-10')")
    run_sql("INSERT OR IGNORE INTO purchase_order (po_number, vendor_id, order_date) VALUES ('PO1002', 'V002', '2024-01-15')")

    # PO line items
    run_sql("INSERT OR IGNORE INTO purchase_order_items (po_number, item_code, quantity, unit_price) VALUES ('PO1001', 'ITEM-A', 100, 10.00)")
    run_sql("INSERT OR IGNORE INTO purchase_order_items (po_number, item_code, quantity, unit_price) VALUES ('PO1001', 'ITEM-B', 50, 20.00)")
    run_sql("INSERT OR IGNORE INTO purchase_order_items (po_number, item_code, quantity, unit_price) VALUES ('PO1002', 'ITEM-C', 200, 5.00)")

    # Goods receipts
    run_sql("INSERT OR IGNORE INTO goods_receipt (gr_number, po_number, receipt_date) VALUES ('GR2001', 'PO1001', '2024-01-20')")
    run_sql("INSERT OR IGNORE INTO goods_receipt (gr_number, po_number, receipt_date) VALUES ('GR2002', 'PO1002', '2024-01-22')")

    # GR line items — PO1001 fully received, PO1002 short-received (mismatch)
    run_sql("INSERT OR IGNORE INTO goods_receipt_items (gr_number, item_code, quantity_received) VALUES ('GR2001', 'ITEM-A', 100)")
    run_sql("INSERT OR IGNORE INTO goods_receipt_items (gr_number, item_code, quantity_received) VALUES ('GR2001', 'ITEM-B', 50)")
    run_sql("INSERT OR IGNORE INTO goods_receipt_items (gr_number, item_code, quantity_received) VALUES ('GR2002', 'ITEM-C', 180)")  # short by 20

    # Invoices
    run_sql(
        "INSERT OR IGNORE INTO invoice (invoice_no, po_number, vendor_id, invoice_date, total_amount, status, date_received) "
        "VALUES ('INV3001', 'PO1001', 'V001', '2024-01-21', 2000.00, 'Pending', '2024-01-21')"
    )
    run_sql(
        "INSERT OR IGNORE INTO invoice (invoice_no, po_number, vendor_id, invoice_date, total_amount, status, date_received) "
        "VALUES ('INV3002', 'PO1002', 'V002', '2024-01-23', 1000.00, 'Pending', '2024-01-23')"
    )

    # Invoice line items
    run_sql("INSERT OR IGNORE INTO invoice_items (invoice_no, item_code, quantity, unit_price) VALUES ('INV3001', 'ITEM-A', 100, 10.00)")
    run_sql("INSERT OR IGNORE INTO invoice_items (invoice_no, item_code, quantity, unit_price) VALUES ('INV3001', 'ITEM-B', 50, 20.00)")
    run_sql("INSERT OR IGNORE INTO invoice_items (invoice_no, item_code, quantity, unit_price) VALUES ('INV3002', 'ITEM-C', 200, 5.00)")  # invoiced more than received

    print("Sample data inserted successfully.")


if __name__ == "__main__":
    seed()
