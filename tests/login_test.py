import argparse
import os
import webbrowser
import time
from pathlib import Path
import sys
# Add project root directory to sys.path to enable agent imports
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from database import db_manager
from agents.failure_detector import FailureDetector
from agents.screenshot_agent import ScreenshotAgent
from agents.log_agent import LogAgent
from agents.dom_analyzer import DOMAnalyzer
from agents.ai_agent import AIAgent
from agents.self_healer import SelfHealer
from agents.validator import Validator
from agents.learning_agent import LearningAgent
from agents.performance_monitor import PerformanceMonitor
from agents.retry_intelligence import RetryIntelligence
from agents.alert_notification import AlertNotification
from agents.auto_cleanup import AutoCleanup

def main():
    parser = argparse.ArgumentParser(description="AI TestFixer Login Self-Healing Test")
    parser.add_argument(
        "--locator",
        default="submitBtn",
        help="Locator ID for the submit button. Use 'submitButton' to simulate failure."
    )
    parser.add_argument(
        "--html",
        default="website/demo_form.html",
        help="Relative path to the HTML file to load in the browser."
    )

    args = parser.parse_args()
    
    # 1. Initialize SQLite Database
    db_manager.init_db()
    
    # Initialize Selenium imports
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import (
        NoSuchElementException,
        TimeoutException,
        StaleElementReferenceException,
        ElementNotInteractableException
    )
    
    # 2. Configure Chrome Driver options – base options (no headless yet)
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    
    # 3. Start Performance Monitor
    perf_monitor = PerformanceMonitor()
    perf_monitor.start()
    
    driver = None
    status = "FAIL"
    used_locator = args.locator
    heal_time = 0.0
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Load the specified HTML file using an absolute file URI
        html_path = (ROOT_DIR / args.html).resolve()
        if not html_path.exists():
            print(f"[ERROR] HTML file not found: {html_path}")
            return
        html_file_uri = html_path.as_uri()
        driver.get(html_file_uri)
        webbrowser.open(html_file_uri)
        
        # Fill standard credential fields
        username_field = driver.find_element(By.ID, "username")
        username_field.send_keys("admin")
        
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys("admin123")
        
        login_btn_locator = args.locator
        
        # Attempt to locate and interact with the button element
        try:
            # Check if there is an existing learned fix for this locator
            learned_fix = db_manager.get_learned_fix(login_btn_locator)
            if learned_fix:
                print(f"[*] Found pre-existing learned fix for locator '{login_btn_locator}': '{learned_fix}'")
                login_btn_locator = learned_fix
                used_locator = learned_fix
            
            # Attempt to click the login button
            by_strategy = By.XPATH if (login_btn_locator.startswith("//") or login_btn_locator.startswith("(/")) else By.ID
            button_element = driver.find_element(by_strategy, login_btn_locator)
            button_element.click()
            status = "PASS"
            used_locator = login_btn_locator
            
            # Track execution time of successful direct run
            exec_time = round(time.perf_counter() - perf_monitor.start_time, 4)
            
            # Log successful test execution to logs and DB
            log_agent = LogAgent()
            log_agent.run(
                test_name="login_test",
                locator=login_btn_locator,
                error_type=None,
                status="PASS",
                execution_time=exec_time,
                healed=0
            )
            
            perf_res = perf_monitor.stop("login_test", "PASS")
            print(f"PASS | Locator: {used_locator} | Exec Time: {perf_res['execution_time']}s")
            
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementNotInteractableException) as ex:
            # Self-healing workflow is triggered on target Selenium exception types
            print(f"[!] Test element resolution failed. Triggering Self-Healing sequence...")
            heal_start_time = time.perf_counter()
            
            # Step 1: Failure Detection
            detector = FailureDetector()
            detect_res = detector.run(ex, login_btn_locator)
            
            if detect_res["should_heal"]:
                # Step 2: Screenshot Capture
                screenshot_agent = ScreenshotAgent()
                screenshot_path = screenshot_agent.run(driver, "login_test")
                print(f"[*] Screenshot saved: {screenshot_path}")
                
                # Step 3: Initial Error Logging
                log_agent = LogAgent()
                log_agent.run(
                    test_name="login_test",
                    locator=login_btn_locator,
                    error_type=detect_res["error_type"],
                    status="FAIL",
                    execution_time=0.0,
                    healed=0
                )
                
                # Update failures database entry with the screenshot path
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM failures ORDER BY id DESC LIMIT 1")
                last_row = cursor.fetchone()
                if last_row:
                    cursor.execute(
                        "UPDATE failures SET screenshot_path = ? WHERE id = ?",
                        (screenshot_path, last_row["id"])
                    )
                conn.commit()
                conn.close()
                
                # Step 4: Analyze DOM structure
                dom_analyzer = DOMAnalyzer()
                candidates = dom_analyzer.run(driver, login_btn_locator)
                print(f"[*] DOM Analyzer discovered {len(candidates)} candidates matching locator criteria.")
                
                # Step 5: Run Retry and AI Healing Loop (RetryIntelligence handles AI suggestions, self healer, validator, learning agent)
                retry_intelligence = RetryIntelligence()
                
                def click_action(loc):
                    strategy = By.XPATH if (loc.startswith("//") or loc.startswith("(/")) else By.ID
                    btn = driver.find_element(strategy, loc)
                    btn.click()
                    return btn
                
                retry_res = retry_intelligence.run(
                    test_function=click_action,
                    test_name="login_test",
                    locator=login_btn_locator,
                    driver=driver,
                    candidates=candidates,
                    error_type=detect_res["error_type"],
                    page_title=driver.title,
                    max_retries=3
                )
                
                heal_time = round(time.perf_counter() - heal_start_time, 4)
                
                if retry_res["final_status"] == "PASS":
                    status = "PASS"
                    # Look up latest updated locator
                    latest_fix = db_manager.get_learned_fix(login_btn_locator)
                    if latest_fix:
                        used_locator = latest_fix
                        
                    # Update failure row with AI suggestion details
                    conn = db_manager.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM failures ORDER BY id DESC LIMIT 1")
                    last_row = cursor.fetchone()
                    if last_row:
                        cursor.execute(
                            "UPDATE failures SET ai_suggestion = ? WHERE id = ?",
                            (f"Replaced '{login_btn_locator}' with '{used_locator}' based on similarity", last_row["id"])
                        )
                    conn.commit()
                    conn.close()
                else:
                    status = "FAIL"
            
            # Step 6: Stop Performance Monitor
            perf_res = perf_monitor.stop("login_test", status)
            
            # Step 7: Alert Notification (Triggered on failure rate thresholds)
            alert_agent = AlertNotification()
            alert_agent.run("login_test")
            
            # Step 8: System File and DB Cleanup
            cleanup_agent = AutoCleanup()
            cleanup_agent.run()
            
            # Print final healed execution logs to stdout
            print(f"{status} | Locator used: {used_locator} | Heal time: {heal_time}s | Performance: {perf_res['execution_time']}s")
            
    except Exception as run_err:
        print(f"[ERROR] Test run failed: {str(run_err)}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
