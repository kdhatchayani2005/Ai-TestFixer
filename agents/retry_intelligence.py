import sys
import time
from pathlib import Path

# Add parent directory to path to import db_manager and other agents
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager
from agents.ai_agent import AIAgent
from agents.self_healer import SelfHealer
from agents.validator import Validator
from agents.learning_agent import LearningAgent

class RetryIntelligence:
    def __init__(self):
        pass
        
    def run(self, test_function, test_name, locator, max_retries=3, driver=None, candidates=None, error_type=None, page_title=None):
        """
        Orchestrates the retry and healing loop.
        - Before each retry: checks learned_fixes table for existing fix.
        - If known fix exists: applies it immediately, skips AI call.
        - Uses exponential backoff: wait = 2^attempt seconds.
        - Logs every retry attempt to the retry_log table.
        """
        attempts_used = 0
        fix_source = "none"
        final_status = "FAILED"
        
        # Instantiate needed agents
        ai_agent = AIAgent()
        healer = SelfHealer()
        validator = Validator()
        learning_agent = LearningAgent()
        
        for attempt in range(1, max_retries + 1):
            attempts_used = attempt
            
            # 1. Check if a learned fix exists for this locator in learned_fixes
            learned_locator = db_manager.get_learned_fix(locator)
            
            if learned_locator:
                fix_source = "learned"
                # Apply the learned fix
                # We assume ID strategy as default or guess it based on value
                by_strategy = "xpath" if (learned_locator.startswith("//") or learned_locator.startswith("(/")) else "id"
                
                # Try healing using the learned locator
                heal_res = healer.run(driver, locator, learned_locator, by_strategy)
                if heal_res["success"]:
                    # Validate the healing action
                    val_res = validator.run(driver, learned_locator, by_strategy, "click")
                    if val_res["validation_status"] == "PASS":
                        # Increment learned fix usage
                        learning_agent.run(locator, learned_locator, 100.0) # confidence high for verified learned fix
                        final_status = "PASS"
                        db_manager.insert_retry_log(test_name, attempt, "HEALED")
                        break
            else:
                # 2. If no learned fix exists, call the AI agent for suggestion
                fix_source = "ai"
                if candidates and error_type:
                    try:
                        ai_res = ai_agent.run(
                            failed_locator=locator,
                            candidates=candidates,
                            error_type=error_type,
                            page_title=page_title or "Login"
                        )
                        replacement = ai_res.get("replacement")
                        confidence = ai_res.get("confidence", 80.0)
                        reason = ai_res.get("reason", "AI/DOM similarity fallback suggestion.")
                        
                        if replacement:
                            by_strategy = "xpath" if (replacement.startswith("//") or replacement.startswith("(/")) else "id"
                            
                            # Try healing with the suggestion
                            heal_res = healer.run(driver, locator, replacement, by_strategy)
                            if heal_res["success"]:
                                # Validate the healing action
                                val_res = validator.run(driver, replacement, by_strategy, "click")
                                if val_res["validation_status"] == "PASS":
                                    # Learn this new fix
                                    learning_agent.run(locator, replacement, confidence)
                                    final_status = "PASS"
                                    db_manager.insert_retry_log(test_name, attempt, "HEALED")
                                    
                                    # Update failures table with detailed suggestion including confidence
                                    try:
                                        conn = db_manager.get_connection()
                                        cursor = conn.cursor()
                                        cursor.execute("SELECT id FROM failures WHERE locator = ? ORDER BY id DESC LIMIT 1", (locator,))
                                        last_row = cursor.fetchone()
                                        if last_row:
                                            cursor.execute(
                                                "UPDATE failures SET ai_suggestion = ? WHERE id = ?",
                                                (f"Replaced '{locator}' with '{replacement}' (Confidence: {int(confidence)}%) - {reason}", last_row["id"])
                                            )
                                        conn.commit()
                                        conn.close()
                                    except Exception as db_err:
                                        print(f"[RetryIntelligence] Failures update error: {str(db_err)}")
                                        
                                    break
                    except Exception as e:
                        # Log error, but continue retrying
                        print(f"[RetryIntelligence] AI Suggestion failed: {str(e)}")
            
            # Log failure of this retry attempt
            db_manager.insert_retry_log(test_name, attempt, "FAILED")
            
            # Exponential backoff (except on the last run)
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"[RetryIntelligence] Attempt {attempt} failed. Waiting {wait_time}s before next retry...")
                time.sleep(wait_time)
                
        # If it never succeeded, mark final retry status
        if final_status != "PASS":
            db_manager.insert_retry_log(test_name, attempts_used, "PERMANENTLY_FAILED")
            
        return {
            "final_status": "PASS" if final_status == "PASS" else "FAIL",
            "attempts_used": attempts_used,
            "fix_source": fix_source
        }
