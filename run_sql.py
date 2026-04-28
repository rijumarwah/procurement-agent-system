import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "procurement.db")


def run_sql(query: str, params: tuple = ()):
    """Execute a single SQL statement and return all rows.

    Returns a list of rows on success, or None if an error occurs.
    Uses parameterised queries when `params` is provided.
    """
    logging.debug("[SQL] %s | params=%s", query.strip(), params)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.commit()
        logging.debug("[SQL] returned %d row(s)", len(rows))
        return rows
    except Exception as exc:
        logging.error("[SQL ERROR] %s", exc)
        return None
    finally:
        conn.close()
