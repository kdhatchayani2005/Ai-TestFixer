import sys
from pathlib import Path

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class LearningAgent:
    def __init__(self):
        pass
        
    def run(self, old_locator, new_locator, confidence):
        """
        Registers or updates a healed locator mapping in the learned_fixes table.
        Increments usage count if it exists, otherwise inserts a new record.
        """
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check if this exact mapping already exists
        cursor.execute(
            "SELECT id, usage_count FROM learned_fixes WHERE old_locator = ? AND new_locator = ?",
            (old_locator, new_locator)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing fix
            record_id = row["id"]
            new_usage_count = row["usage_count"] + 1
            cursor.execute(
                "UPDATE learned_fixes SET usage_count = ? WHERE id = ?",
                (new_usage_count, record_id)
            )
            action = "updated"
            usage_count = new_usage_count
        else:
            # Check if old_locator already exists but with a different new_locator
            # In that case, we can either insert a new row or update.
            # The prompt says: "If exists: increments usage_count. If new: inserts the fix."
            # So we will insert the fix as a new mapping.
            cursor.execute(
                "INSERT INTO learned_fixes (old_locator, new_locator, confidence, usage_count) VALUES (?, ?, ?, 1)",
                (old_locator, new_locator, confidence)
            )
            action = "inserted"
            usage_count = 1
            
        conn.commit()
        conn.close()
        
        return {
            "action": action,
            "old_locator": old_locator,
            "new_locator": new_locator,
            "confidence": float(confidence),
            "usage_count": usage_count
        }
