import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class LogAgent:
    def __init__(self):
        pass
        
    def run(self, test_name, locator, error_type, status, execution_time, healed=0):
        """
        Writes a structured log entry to logs/{test_name}.log,
        and inserts the execution record into the test_history table.
        """
        workspace_dir = Path(__file__).parent.parent.resolve()
        logs_dir = workspace_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file_path = logs_dir / f"{test_name}.log"
        timestamp = datetime.now().isoformat()
        
        # Format: [TIMESTAMP] TEST={test_name} LOCATOR={locator} ERROR={error_type} STATUS={status} TIME={execution_time}s
        log_line = f"[{timestamp}] TEST={test_name} LOCATOR={locator} ERROR={error_type} STATUS={status} TIME={execution_time}s\n"
        
        # Append to log file
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_line)
            
        # Insert into test_history database table
        db_manager.insert_test_history(
            test_name=test_name,
            status=status,
            execution_time=execution_time,
            healed=healed
        )
        
        return str(log_file_path.resolve())
