import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class AutoCleanup:
    def __init__(self):
        pass
        
    def run(self, force=False):
        """
        Runs automatically. Increments the run counter in SQLite.
        If the counter hits 10 (or if force=True), performs cleanup operations:
        - Deletes screenshot files older than 7 days.
        - Moves log files older than 30 days to logs/archive/.
        - Removes duplicate learned_fixes rows (same old + new locator combination).
        """
        # Increment execution counter
        counter_val = db_manager.increment_cleanup_counter()
        
        ran = False
        screenshots_deleted = 0
        logs_archived = 0
        duplicates_removed = 0
        
        if counter_val >= 10 or force:
            ran = True
            workspace_dir = Path(__file__).parent.parent.resolve()
            
            # 1. Clean up screenshots older than 7 days
            screenshots_dir = workspace_dir / "screenshots"
            if screenshots_dir.exists():
                now = time.time()
                seven_days_ago = now - (7 * 24 * 3600)
                
                for f_path in screenshots_dir.glob("*.png"):
                    if f_path.is_file():
                        # Use file modification time
                        file_mtime = f_path.stat().st_mtime
                        if file_mtime < seven_days_ago:
                            try:
                                f_path.unlink()
                                screenshots_deleted += 1
                            except Exception as e:
                                print(f"[AutoCleanup] Error deleting screenshot {f_path.name}: {str(e)}")
                                
            # 2. Archive logs older than 30 days
            logs_dir = workspace_dir / "logs"
            archive_dir = logs_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            if logs_dir.exists():
                now = time.time()
                thirty_days_ago = now - (30 * 24 * 3600)
                
                # Iterate through .log files, ignoring the archive directory itself
                for f_path in logs_dir.glob("*.log"):
                    if f_path.is_file():
                        file_mtime = f_path.stat().st_mtime
                        if file_mtime < thirty_days_ago:
                            try:
                                dest_path = archive_dir / f_path.name
                                shutil.move(str(f_path), str(dest_path))
                                logs_archived += 1
                            except Exception as e:
                                print(f"[AutoCleanup] Error archiving log {f_path.name}: {str(e)}")
                                
            # 3. Remove duplicate learned_fixes rows (same old+new locator)
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Count records before
            cursor.execute("SELECT COUNT(*) FROM learned_fixes")
            count_before = cursor.fetchone()[0]
            
            # Execute duplicate removal query, keeping the row with the largest ID
            cursor.execute("""
                DELETE FROM learned_fixes
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM learned_fixes
                    GROUP BY old_locator, new_locator
                )
            """)
            
            # Count records after
            cursor.execute("SELECT COUNT(*) FROM learned_fixes")
            count_after = cursor.fetchone()[0]
            
            duplicates_removed = count_before - count_after
            conn.commit()
            conn.close()
            
            # Reset cleanup counter in database
            db_manager.reset_cleanup_counter()
            
        return {
            "ran": ran,
            "screenshots_deleted": screenshots_deleted,
            "logs_archived": logs_archived,
            "duplicates_removed": duplicates_removed
        }
