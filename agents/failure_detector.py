import sys
from datetime import datetime
from pathlib import Path
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementNotInteractableException
)

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class FailureDetector:
    def __init__(self):
        pass
        
    def run(self, exception, locator):
        """
        Analyzes a Selenium exception, determines if it is self-healable,
        and logs the failure event into the database.
        """
        error_type = type(exception).__name__
        timestamp = datetime.now().isoformat()
        
        # Check if the exception belongs to the 4 self-healable types
        healable_exceptions = {
            "NoSuchElementException",
            "TimeoutException",
            "StaleElementReferenceException",
            "ElementNotInteractableException"
        }
        
        should_heal = error_type in healable_exceptions
        
        # Log to SQLite failures table
        db_manager.insert_failure(
            locator=locator,
            error=error_type,
            screenshot_path=None,
            ai_suggestion=None
        )
        
        return {
            "error_type": error_type,
            "locator": locator,
            "timestamp": timestamp,
            "should_heal": should_heal
        }
