import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# Resolve database path relative to db_manager.py
DB_DIR = Path(__file__).parent.resolve()
DB_PATH = DB_DIR / "testfixer.db"

def get_connection():
    """Returns a connection to the SQLite database, ensuring directory exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes all database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. failures table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        locator TEXT NOT NULL,
        error TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        screenshot_path TEXT,
        ai_suggestion TEXT
    );
    """)
    
    # 2. learned_fixes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learned_fixes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        old_locator TEXT NOT NULL,
        new_locator TEXT NOT NULL,
        confidence REAL NOT NULL,
        usage_count INTEGER DEFAULT 1
    );
    """)
    
    # 3. test_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT NOT NULL,
        status TEXT NOT NULL,
        execution_time REAL NOT NULL,
        healed INTEGER DEFAULT 0
    );
    """)
    
    # 4. performance table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT NOT NULL,
        execution_time REAL NOT NULL,
        avg_time REAL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)
    
    # 5. alerts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        sent_status INTEGER DEFAULT 0
    );
    """)
    
    # 6. retry_log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS retry_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT NOT NULL,
        retry_count INTEGER NOT NULL,
        final_status TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    # 7. cleanup_counter table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cleanup_counter (
        counter_val INTEGER DEFAULT 0
    );
    """)
    
    # Initialize cleanup counter if empty
    cursor.execute("SELECT COUNT(*) FROM cleanup_counter")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO cleanup_counter (counter_val) VALUES (0)")
        
    conn.commit()
    conn.close()

def insert_failure(locator, error, screenshot_path, ai_suggestion):
    """Inserts a failed locator event into the failures table."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO failures (locator, error, timestamp, screenshot_path, ai_suggestion)
        VALUES (?, ?, ?, ?, ?)
    """, (locator, error, timestamp, screenshot_path, ai_suggestion))
    conn.commit()
    conn.close()

def insert_learned_fix(old_locator, new_locator, confidence):
    """Inserts a newly resolved locator mapping."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO learned_fixes (old_locator, new_locator, confidence, usage_count)
        VALUES (?, ?, ?, 1)
    """, (old_locator, new_locator, confidence))
    conn.commit()
    conn.close()

def get_learned_fix(old_locator):
    """Retrieves the healed locator for an old locator, if one exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT new_locator FROM learned_fixes 
        WHERE old_locator = ? 
        ORDER BY confidence DESC, id DESC LIMIT 1
    """, (old_locator,))
    row = cursor.fetchone()
    conn.close()
    return row["new_locator"] if row else None

def increment_fix_usage(old_locator):
    """Increments the usage count of a learned locator fix."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE learned_fixes 
        SET usage_count = usage_count + 1 
        WHERE old_locator = ?
    """, (old_locator,))
    conn.commit()
    conn.close()

def insert_test_history(test_name, status, execution_time, healed):
    """Inserts a test execution outcome record."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO test_history (test_name, status, execution_time, healed)
        VALUES (?, ?, ?, ?)
    """, (test_name, status, execution_time, healed))
    conn.commit()
    conn.close()

def insert_performance(test_name, execution_time, avg_time, status):
    """Logs test performance telemetry."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO performance (test_name, execution_time, avg_time, status, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (test_name, execution_time, avg_time, status, timestamp))
    conn.commit()
    conn.close()

def insert_alert(alert_type, message, sent_status):
    """Logs an alert trigger, recording if email sending succeeded."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO alerts (alert_type, message, timestamp, sent_status)
        VALUES (?, ?, ?, ?)
    """, (alert_type, message, timestamp, sent_status))
    conn.commit()
    conn.close()

def insert_retry_log(test_name, retry_count, final_status):
    """Logs execution retry activity."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO retry_log (test_name, retry_count, final_status, timestamp)
        VALUES (?, ?, ?, ?)
    """, (test_name, retry_count, final_status, timestamp))
    conn.commit()
    conn.close()

def increment_cleanup_counter():
    """Increments the internal counter tracking run executions for cleanup, returns new count."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cleanup_counter SET counter_val = counter_val + 1")
    cursor.execute("SELECT counter_val FROM cleanup_counter LIMIT 1")
    val = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return val

def reset_cleanup_counter():
    """Resets the execution counter tracking cleanups to zero."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cleanup_counter SET counter_val = 0")
    conn.commit()
    conn.close()

# DataFrame queries using parameter-safe operations
def get_all_failures():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM failures ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_learned_fixes():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM learned_fixes ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_test_history():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM test_history ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_performance():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM performance ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_alerts():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM alerts ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_retry_logs():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM retry_log ORDER BY id DESC", conn)
    conn.close()
    return df

def get_kpi_stats():
    """Computes high-level KPI dashboard metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total tests run
    cursor.execute("SELECT COUNT(*) FROM test_history")
    total = cursor.fetchone()[0]
    
    # Passed tests (excluding healed tests from failures, status = 'PASS')
    cursor.execute("SELECT COUNT(*) FROM test_history WHERE status = 'PASS'")
    passed = cursor.fetchone()[0]
    
    # Failed tests
    cursor.execute("SELECT COUNT(*) FROM test_history WHERE status = 'FAIL'")
    failed = cursor.fetchone()[0]
    
    # Healed tests
    cursor.execute("SELECT COUNT(*) FROM test_history WHERE healed = 1")
    healed = cursor.fetchone()[0]
    
    # Average healing time (for healed tests)
    cursor.execute("SELECT AVG(execution_time) FROM test_history WHERE healed = 1")
    avg_heal_time = cursor.fetchone()[0]
    avg_heal_time = round(avg_heal_time, 2) if avg_heal_time else 0.0
    
    conn.close()
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "healed": healed,
        "avg_heal_time": avg_heal_time
    }
