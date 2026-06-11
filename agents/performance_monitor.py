import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class PerformanceMonitor:
    def __init__(self):
        self.start_time = None
        
    def start(self):
        """Starts the timer for tracking execution performance."""
        self.start_time = time.perf_counter()
        
    def stop(self, test_name, status):
        """
        Stops the timer, calculates the execution time, fetches the rolling average
        over the last 10 runs from SQLite, flags if the test is slow (>2x average),
        logs the data to the performance table, and returns the metrics.
        """
        if self.start_time is None:
            # Fallback if start was not called
            self.start_time = time.perf_counter()
            
        execution_time = round(time.perf_counter() - self.start_time, 4)
        timestamp = datetime.now().isoformat()
        
        # Calculate rolling average of the last 10 runs from SQLite
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT execution_time FROM performance WHERE test_name = ? ORDER BY id DESC LIMIT 10",
            (test_name,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        times = [row["execution_time"] for row in rows]
        
        if times:
            avg_time = sum(times) / len(times)
        else:
            # First run
            avg_time = execution_time
            
        avg_time = round(avg_time, 4)
        
        # Flag as slow if execution_time > 2 * avg_time
        # (Only flag if we have at least one prior execution to compare to)
        is_slow = False
        if len(times) > 0 and execution_time > 2 * avg_time:
            is_slow = True
            
        # Write to performance table
        db_manager.insert_performance(
            test_name=test_name,
            execution_time=execution_time,
            avg_time=avg_time,
            status=status
        )
        
        return {
            "test_name": test_name,
            "execution_time": execution_time,
            "avg_time": avg_time,
            "is_slow": is_slow,
            "status": status,
            "timestamp": timestamp
        }
