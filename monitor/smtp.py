import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

# Load configuration from JSON file
def load_config(file_path):
    with open(file_path, 'r') as config_file:
        config = json.load(config_file)
    return config

# Load configuration
config = load_config('config_smtp.json')
smtp_server = config.get('smtp_server')
smtp_port = config.get('smtp_port')
username = config.get('username')
password = config.get('password')
sender_email = config.get('sender_email', "pcs@oceanpark.com.hk")
recipient_emails = config.get('recipient_emails', ["pcs_recipient@oceanpark.com.hk"])  # List of recipients

# Create the email content
subject = "PeopleCountSystem Alert"

def send_email(aContent):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_emails)  # Join multiple recipients with commas
        msg['Subject'] = subject
        
        msg.attach(MIMEText(aContent, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # server.login(username, password)  # Uncomment if authentication is required
            server.sendmail(sender_email, recipient_emails, msg.as_string())
        print(f"Email sent to {recipient_emails}: {aContent}")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == '__main__':
    send_email(f"python smtp test {datetime.datetime.now()}")