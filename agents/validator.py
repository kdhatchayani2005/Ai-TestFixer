import sys
import time
from pathlib import Path
from selenium.webdriver.common.by import By

# Add parent directory to path to import log_agent
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from agents.log_agent import LogAgent

class Validator:
    def __init__(self):
        self.by_map = {
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "class_name": By.CLASS_NAME,
            "xpath": By.XPATH,
            "css": By.CSS_SELECTOR,
            "css_selector": By.CSS_SELECTOR
        }
        
    def run(self, driver, healed_locator, by_strategy, expected_action):
        """
        Attempts the expected action on the healed element and validates if it succeeds.
        Actions: "click", "type", "visible"
        """
        start_time = time.perf_counter()
        
        strategy_lower = str(by_strategy).lower().strip()
        by_locator = self.by_map.get(strategy_lower)
        if not by_locator:
            if healed_locator.startswith("//") or healed_locator.startswith("(/"):
                by_locator = By.XPATH
            else:
                by_locator = By.ID
                
        validation_status = "FAIL"
        message = ""
        
        try:
            # Locate element
            element = driver.find_element(by_locator, healed_locator)
            
            if expected_action == "click":
                element.click()
                validation_status = "PASS"
                message = "Successfully clicked element."
            elif expected_action == "type":
                # Determine what input value to send
                val_to_type = "test_input"
                name_attr = element.get_attribute("name") or ""
                id_attr = element.get_attribute("id") or ""
                
                if "pass" in name_attr.lower() or "pass" in id_attr.lower():
                    val_to_type = "admin123"
                elif "user" in name_attr.lower() or "user" in id_attr.lower():
                    val_to_type = "admin_user"
                    
                element.clear()
                element.send_keys(val_to_type)
                validation_status = "PASS"
                message = f"Successfully typed '{val_to_type}' into element."
            elif expected_action == "visible":
                if element.is_displayed():
                    validation_status = "PASS"
                    message = "Element is visible on the page."
                else:
                    validation_status = "FAIL"
                    message = "Element was found but not visible."
            else:
                validation_status = "FAIL"
                message = f"Unknown validation action '{expected_action}'"
                
        except Exception as e:
            validation_status = "FAIL"
            message = f"Validation failed with exception: {type(e).__name__} - {str(e)}"
            
        execution_time = round(time.perf_counter() - start_time, 4)
        
        # Log outcome via LogAgent
        # Since this represents the validation step of a healing operation,
        # we log this to the test log file. We set healed=1 on PASS.
        log_agent = LogAgent()
        healed_flag = 1 if validation_status == "PASS" else 0
        log_agent.run(
            test_name="login_test",
            locator=healed_locator,
            error_type=None if validation_status == "PASS" else "ValidationError",
            status=validation_status,
            execution_time=execution_time,
            healed=healed_flag
        )
        
        return {
            "validation_status": validation_status,
            "message": message,
            "execution_time": execution_time
        }
