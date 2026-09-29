import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'payments.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cutoff = (datetime.now() - timedelta(hours=2)).isoformat()

cursor.execute("""
    SELECT COUNT(*) as total, SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes
    FROM transactions
    WHERE timestamp >= ?
""", (cutoff,))
row = cursor.fetchone()
print("ISO Cutoff query:", row)

cursor.execute("""
    SELECT COUNT(*) as total, SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes
    FROM transactions
    WHERE replace(timestamp, 'T', ' ') >= datetime('now', '-2 hours')
""")
row2 = cursor.fetchone()
print("datetime('now', '-2 hours') query:", row2)

cursor.execute("""
    SELECT timestamp, status FROM transactions
    WHERE timestamp >= ? AND method = 'Net Banking'
    ORDER BY timestamp DESC LIMIT 5
""", (cutoff,))
print("Recent rows:", cursor.fetchall())
