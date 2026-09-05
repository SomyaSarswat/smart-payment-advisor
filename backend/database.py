import sqlite3
import os
from datetime import datetime, timedelta

# Define database file path inside the backend folder
DB_PATH = os.path.join(os.path.dirname(__file__), "payments.db")

def get_connection():
    """
    Helper function to establish a connection to the SQLite database.
    Configures row_factory so that query results can be accessed as dictionary-like objects.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the SQLite database.
    Creates the 'transactions' table if it does not already exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create the transactions table with required fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id TEXT NOT NULL,
            method TEXT NOT NULL,
            bank TEXT,
            amount REAL NOT NULL,
            device TEXT,
            hour INTEGER,
            status TEXT NOT NULL,
            error_code TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def insert_transaction(merchant_id, method, bank, amount, device, hour, status, error_code=None):
    """
    Inserts a new transaction record into the database.
    Automatically sets the timestamp to the current ISO format datetime string.
    Returns the integer ID of the newly inserted row.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current time formatted as ISO standard string (e.g. '2026-09-04T19:20:00.123456')
    current_timestamp = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO transactions (merchant_id, method, bank, amount, device, hour, status, error_code, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (merchant_id, method, bank, amount, device, hour, status, error_code, current_timestamp))
    
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return inserted_id

def get_recent_transactions(merchant_id=None, method=None, bank=None, hours_lookback=2, amount_min=None, amount_max=None):
    """
    Fetches transactions recorded within the last `hours_lookback` hours.
    Applies optional filters if merchant_id, method, bank, amount_min, or amount_max are provided.
    Returns a list of dictionaries with keys matching the column names.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate cutoff time based on hours_lookback
    cutoff_time = (datetime.now() - timedelta(hours=hours_lookback)).isoformat()
    
    # Base query: select transactions newer than cutoff time
    query = "SELECT * FROM transactions WHERE timestamp >= ?"
    params = [cutoff_time]
    
    # Dynamically append optional filters
    if merchant_id is not None:
        query += " AND merchant_id = ?"
        params.append(merchant_id)
        
    if method is not None:
        query += " AND method = ?"
        params.append(method)
        
    if bank is not None:
        query += " AND bank = ?"
        params.append(bank)
        
    if amount_min is not None:
        query += " AND amount >= ?"
        params.append(amount_min)
        
    if amount_max is not None:
        query += " AND amount <= ?"
        params.append(amount_max)
        
    # Order by timestamp (newest first)
    query += " ORDER BY timestamp DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Convert sqlite3.Row objects to standard python dictionaries
    results = [dict(row) for row in rows]
    
    conn.close()
    return results

def get_all_transactions_count():
    """
    Returns the total count of transaction rows stored in the table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count

def inject_failure_spike(merchant_id: str, method: str, bank: str = None, failure_count: int = 10, error_code: str = "simulated_downtime"):
    """
    Injects artificial failed transaction records to simulate a real-time bank or network outage.
    Returns the number of injected rows and updated success rate for the target method.
    """
    conn = get_connection()
    cursor = conn.cursor()
    current_timestamp = datetime.now().isoformat()
    current_hour = datetime.now().hour

    for _ in range(failure_count):
        cursor.execute("""
            INSERT INTO transactions (merchant_id, method, bank, amount, device, hour, status, error_code, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (merchant_id, method, bank, 100.0, "Android", current_hour, "failed", error_code, current_timestamp))

    conn.commit()

    # Calculate updated success rate for this method
    if bank:
        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM transactions 
            WHERE merchant_id = ? AND method = ? AND bank = ?
            GROUP BY status
        """, (merchant_id, method, bank))
    else:
        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM transactions 
            WHERE merchant_id = ? AND method = ? AND bank IS NULL
            GROUP BY status
        """, (merchant_id, method))
    
    rows = cursor.fetchall()
    conn.close()

    counts = {r["status"]: r["cnt"] for r in rows}
    successes = counts.get("success", 0)
    fails = counts.get("failed", 0)
    total = successes + fails
    updated_rate = round((successes / total * 100), 1) if total > 0 else 0.0

    return {
        "injected_count": failure_count,
        "method": method,
        "bank": bank,
        "merchant_id": merchant_id,
        "updated_success_rate": updated_rate
    }

def get_merchant_analytics(merchant_id: str = None):
    """
    Calculates key metrics (total transactions, global success rate, top failing method, estimated fee savings)
    and fetches the last 20 transaction records for the dashboard.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Filter query based on merchant_id
    if merchant_id and merchant_id.lower() != "all":
        cursor.execute("SELECT * FROM transactions WHERE merchant_id = ? ORDER BY id DESC", (merchant_id,))
    else:
        cursor.execute("SELECT * FROM transactions ORDER BY id DESC")
    
    all_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_count = len(all_rows)
    success_rows = [r for r in all_rows if r["status"] == "success"]
    failed_rows = [r for r in all_rows if r["status"] == "failed"]

    global_success_rate = round((len(success_rows) / total_count * 100), 1) if total_count > 0 else 100.0

    # Determine top failing method
    failure_counts = {}
    for r in failed_rows:
        key = f"{r['method']} - {r['bank']}" if r.get("bank") else r["method"]
        failure_counts[key] = failure_counts.get(key, 0) + 1
    
    top_failing_method = max(failure_counts, key=failure_counts.get) if failure_counts else "None"

    # Total fee savings estimate: ₹15.0 avg savings per auto-rerouted successful transaction
    total_fee_savings = round(len(success_rows) * 15.0, 2)

    recent_transactions = all_rows[:20]

    return {
        "merchant_id": merchant_id or "all",
        "total_transactions": total_count,
        "global_success_rate": global_success_rate,
        "top_failing_method": top_failing_method,
        "total_merchant_fee_savings": total_fee_savings,
        "recent_transactions": recent_transactions
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

