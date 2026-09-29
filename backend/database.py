import sqlite3
import os
from datetime import datetime, timedelta

# Define database file path inside the backend folder
DB_PATH = os.path.join(os.path.dirname(__file__), "payments.db")

class DatabaseUnavailableError(Exception):
    """Raised when payments.db is locked or database connection fails."""
    pass

def get_connection():
    """
    Helper function to establish a connection to the SQLite database.
    Configures row_factory so that query results can be accessed as dictionary-like objects.
    Raises DatabaseUnavailableError if database is locked or unreadable.
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Database unavailable or locked: {str(e)}") from e

def init_db():
    """
    Initializes the SQLite database.
    Creates the 'transactions' table if it does not already exist.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
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
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to initialize database: {str(e)}") from e

def insert_transaction(merchant_id, method, bank, amount, device, hour, status, error_code=None):
    """
    Inserts a new transaction record into the database.
    Returns integer ID of newly inserted row.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        current_timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO transactions (merchant_id, method, bank, amount, device, hour, status, error_code, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (merchant_id, method, bank, amount, device, hour, status, error_code, current_timestamp))
        
        inserted_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return inserted_id
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to insert transaction: {str(e)}") from e

def get_recent_transactions(merchant_id=None, method=None, bank=None, hours_lookback=2, amount_min=None, amount_max=None):
    """
    Fetches transactions recorded within last hours_lookback hours.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours_lookback)).isoformat()
        
        query = "SELECT * FROM transactions WHERE timestamp >= ?"
        params = [cutoff_time]
        
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
            
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        conn.close()
        return results
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to query recent transactions: {str(e)}") from e

def get_windowed_stats_sql(merchant_id=None, method=None, bank=None, hours_lookback=2):
    """
    UPGRADE 1: Database-level windowed aggregation query.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours_lookback)).isoformat()

        query = """
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) as success_count
            FROM transactions
            WHERE timestamp >= ?
        """
        params = [cutoff_time]

        if merchant_id is not None:
            query += " AND merchant_id = ?"
            params.append(merchant_id)

        if method is not None:
            query += " AND method = ?"
            params.append(method)

        if bank is not None:
            query += " AND bank = ?"
            params.append(bank)
        elif method in ["Credit Card", "Debit Card", "Net Banking"]:
            query += " AND bank IS NULL"

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        total_count = row["total_count"] if row else 0
        success_count = row["success_count"] if row else 0
        success_rate = round((success_count / total_count * 100.0), 1) if total_count > 0 else None

        return {
            "total_count": total_count,
            "success_count": success_count,
            "success_rate": success_rate
        }
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to calculate windowed stats: {str(e)}") from e

def get_windowed_transactions_decay(merchant_id=None, method=None, bank=None, hours_lookback=2):
    """
    UPGRADE 2: Fetches transaction statuses and timestamps for exponential decay.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours_lookback)).isoformat()

        query = """
            SELECT status, timestamp
            FROM transactions
            WHERE timestamp >= ?
        """
        params = [cutoff_time]

        if merchant_id is not None:
            query += " AND merchant_id = ?"
            params.append(merchant_id)

        if method is not None:
            query += " AND method = ?"
            params.append(method)

        if bank is not None:
            query += " AND bank = ?"
            params.append(bank)
        elif method in ["Credit Card", "Debit Card", "Net Banking"]:
            query += " AND bank IS NULL"

        query += " ORDER BY timestamp DESC"

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to fetch decay transactions: {str(e)}") from e

def get_all_transactions_count():
    """
    Returns total count of transaction rows.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to count transactions: {str(e)}") from e

def inject_failure_spike(merchant_id: str, method: str, bank: str = None, failure_count: int = 10, error_code: str = "simulated_downtime"):
    """
    Injects artificial failed transaction records.
    """
    try:
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
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to inject failure spike: {str(e)}") from e

def get_merchant_analytics(merchant_id: str = None):
    """
    Calculates key metrics and fetches last 20 transaction records.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

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

        failure_counts = {}
        for r in failed_rows:
            key = f"{r['method']} - {r['bank']}" if r.get("bank") else r["method"]
            failure_counts[key] = failure_counts.get(key, 0) + 1
        
        top_failing_method = max(failure_counts, key=failure_counts.get) if failure_counts else "None"
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
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        raise DatabaseUnavailableError(f"Failed to compute merchant analytics: {str(e)}") from e

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
