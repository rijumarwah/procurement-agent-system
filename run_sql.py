# import sqlite3
#
# DB_PATH = "/Users/riju/Documents/Code/EYAutogen/db/procurement.db"
#
# def run_sql(query: str, params: tuple = (), fetch: bool = False):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     try:
#         cursor.execute(query, params)
#         result = cursor.fetchall() if fetch else None
#         conn.commit()
#     except Exception as e:
#         result = f"SQL Error: {str(e)}"
#     finally:
#         conn.close()
#     return result

import sqlite3
import os

# Make this the absolute path to your DB file
DB_PATH = os.path.abspath("/Users/riju/Documents/Code/EYAutogen/db/procurement.db")  # replace with your actual DB file name

def run_sql(query: str):
    print(f"[SQL DEBUG] Executing:\n{query}\n")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.commit()
        print(f"[SQL DEBUG] Rows: {rows}")
        return rows
    except Exception as e:
        print(f"[SQL ERROR] {e}")
        return None
    finally:
        conn.close()
