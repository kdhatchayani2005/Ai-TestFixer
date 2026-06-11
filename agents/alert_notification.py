import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

# Add parent directory to path to import db_manager
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from database import db_manager

class AlertNotification:
    def __init__(self, threshold=3):
        self.threshold = threshold
        
    def run(self, test_name="login_test"):
        """
        Reads the failure count from the last 1 hour from the failures table.
        If it meets or exceeds the threshold, triggers an email alert using SMTP + SSL.
        Logs the alert details to the alerts table.
        """
        # Calculate time 1 hour ago
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        # Query database for failures in the last 1 hour
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM failures WHERE timestamp >= ?", (one_hour_ago,))
        failure_count = cursor.fetchone()[0]
        
        # Get the latest failure details for the email body
        cursor.execute("SELECT locator, error, timestamp FROM failures ORDER BY id DESC LIMIT 1")
        latest_failure = cursor.fetchone()
        conn.close()
        
        alert_sent = False
        message_body = ""
        
        if failure_count >= self.threshold:
            # Construct email alert body using actual DB data
            timestamp_str = datetime.now().isoformat()
            latest_locator = latest_failure["locator"] if latest_failure else "Unknown"
            latest_error = latest_failure["error"] if latest_failure else "Unknown"
            
            message_body = (
                f"WARNING: High failure rate detected for test '{test_name}'!\n"
                f"Failure count in the last hour: {failure_count} (Threshold: {self.threshold})\n"
                f"Timestamp: {timestamp_str}\n"
                f"Latest failed locator: {latest_locator}\n"
                f"Latest error detected: {latest_error}\n\n"
                f"Suggested Action: Open the Streamlit dashboard or check logs to analyze and heal the locator."
            )
            
            # SMTP config from environment variables
            smtp_host = os.environ.get("SMTP_HOST")
            smtp_port = os.environ.get("SMTP_PORT")
            smtp_user = os.environ.get("SMTP_USER")
            smtp_pass = os.environ.get("SMTP_PASS")
            alert_to = os.environ.get("ALERT_TO")
            
            if smtp_host and smtp_port and smtp_user and smtp_pass and alert_to:
                try:
                    # Construct message
                    msg = MIMEText(message_body)
                    msg["Subject"] = f"AI TestFixer Alert: High failure rate for {test_name}"
                    msg["From"] = smtp_user
                    msg["To"] = alert_to
                    
                    # Send email via SSL
                    port = int(smtp_port)
                    # Check if port is standard SSL (465) or standard STARTTLS (587)
                    if port == 465:
                        with smtplib.SMTP_SSL(smtp_host, port, timeout=10) as server:
                            server.login(smtp_user, smtp_pass)
                            server.sendmail(smtp_user, [alert_to], msg.as_string())
                    else:
                        with smtplib.SMTP(smtp_host, port, timeout=10) as server:
                            server.starttls()
                            server.login(smtp_user, smtp_pass)
                            server.sendmail(smtp_user, [alert_to], msg.as_string())
                    alert_sent = True
                    sent_status = 1
                except Exception as e:
                    print(f"[AlertNotification] Failed to send email alert: {str(e)}")
                    sent_status = 0
            else:
                print("[AlertNotification] SMTP environment variables are missing. Skipping email dispatch.")
                sent_status = 0
                
            # Log to alerts table
            db_manager.insert_alert(
                alert_type="HighFailureRate",
                message=message_body,
                sent_status=sent_status
            )
        else:
            sent_status = 0
            
        return {
            "alert_sent": alert_sent,
            "failure_count": failure_count,
            "threshold": self.threshold
        }
