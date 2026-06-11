import os
from datetime import datetime
from pathlib import Path

class ScreenshotAgent:
    def __init__(self):
        pass
        
    def run(self, driver, test_name):
        """
        Captures a screenshot using the Selenium driver and saves it in the screenshots directory.
        Replaces illegal colon characters in the ISO timestamp to ensure Windows file compatibility.
        """
        # Create screenshots folder relative to workspace
        workspace_dir = Path(__file__).parent.parent.resolve()
        screenshots_dir = workspace_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize timestamp for Windows filenames (no colons)
        timestamp_str = datetime.now().isoformat().replace(":", "-")
        screenshot_filename = f"{test_name}_{timestamp_str}.png"
        screenshot_path = screenshots_dir / screenshot_filename
        
        # Save screenshot using WebDriver
        driver.save_screenshot(str(screenshot_path))
        
        # Return path as absolute string (or relative to workspace, let's return absolute string)
        return str(screenshot_path.resolve())
