import smtplib
import os
from dotenv import load_dotenv
from config import carrier_emails

# load environment variables
load_dotenv()
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

def send_sms(number, carrier, message):
    try:
        # find user's carrier email based on their carrier
        carrier_gateway_template = carrier_emails[carrier]["sms_email"]
    except KeyError:
        print(f"Error: Carrier '{carrier}' not found in carrier_emails.")
        return

    carrier_gateway = carrier_gateway_template.replace("number", number)
    recipient_email = f"{number}@{carrier_gateway}"

    print(f"Sending message to {recipient_email}...")

    try:
        # set my email/pass
        sender = GMAIL_USER
        password = GMAIL_PASS

        # create server object
        server = smtplib.SMTP("smtp.gmail.com", 587)  # Example for Gmail
        server.starttls()
        server.login(sender, password)

        # send message
        server.sendmail(sender, recipient_email, message)
        server.quit()
        print("Message sent successfully.")
        
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")