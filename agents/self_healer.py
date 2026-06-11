import sys
from pathlib import Path
from selenium.webdriver.common.by import By

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class SelfHealer:
    def __init__(self):
        # Map string strategies to Selenium By locators
        self.by_map = {
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "class_name": By.CLASS_NAME,
            "xpath": By.XPATH,
            "css": By.CSS_SELECTOR,
            "css_selector": By.CSS_SELECTOR
        }
        
    def run(self, driver, old_locator, new_locator, by_strategy):
        """
        Attempts to find the element using the new locator and strategy.
        If successful, updates the learned_fixes table in the database.
        """
        strategy_lower = str(by_strategy).lower().strip()
        by_locator = self.by_map.get(strategy_lower)
        
        if not by_locator:
            # Fallback to ID if not matching, or XPATH if it looks like one
            if new_locator.startswith("//") or new_locator.startswith("(/"):
                by_locator = By.XPATH
                strategy_lower = "xpath"
            else:
                by_locator = By.ID
                strategy_lower = "id"
                
        success = False
        element_found = None
        
        try:
            # Attempt to find the element
            element = driver.find_element(by_locator, new_locator)
            success = True
            element_found = str(element)
            
            # Update database learned_fixes table on success
            existing_fix = db_manager.get_learned_fix(old_locator)
            if existing_fix:
                db_manager.increment_fix_usage(old_locator)
            else:
                # Default confidence to 80% if not provided
                db_manager.insert_learned_fix(old_locator, new_locator, 80.0)
                
        except Exception as e:
            success = False
            element_found = None
            
        return {
            "success": success,
            "new_locator": new_locator,
            "by_strategy": strategy_lower,
            "element_found": element_found
        }
