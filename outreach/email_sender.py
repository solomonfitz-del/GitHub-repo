import os
import json
import requests
from typing import Optional, Dict, Any
from jinja2 import Template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailSender:
    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, from_email: Optional[str] = None):
        """
        Initialize the EmailSender with a provider, api_key, and from_email.
        If not provided, reads from environment variables:
        - EMAIL_PROVIDER (defaults to 'resend' or 'sendgrid' depending on key)
        - EMAIL_API_KEY
        - FROM_EMAIL (defaults to 'SiteForge <outreach@siteforge.com>' or similar)
        """
        self.api_key = api_key or os.getenv("EMAIL_API_KEY")
        self.provider = provider or os.getenv("EMAIL_PROVIDER") or self._detect_provider()
        self.from_email = from_email or os.getenv("FROM_EMAIL") or "SiteForge <outreach@siteforge.com>"
        
        # Unsubscribe tracking file to prevent emailing opted-out leads
        self.optout_file = os.getenv("OPTOUT_FILE_PATH") or "/home/team/shared/outreach/optouts.json"
        self._ensure_optout_file()

    def _detect_provider(self) -> str:
        """Helper to auto-detect provider based on API key prefix if not specified"""
        if not self.api_key:
            return "mock"
        if self.api_key.startswith("re_"):
            return "resend"
        if self.api_key.startswith("SG."):
            return "sendgrid"
        return "resend"  # default to resend

    def _ensure_optout_file(self):
        """Create optouts file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.optout_file), exist_ok=True)
        if not os.path.exists(self.optout_file):
            with open(self.optout_file, "w") as f:
                json.dump([], f)

    def is_unsubscribed(self, email: str) -> bool:
        """Check if an email is in the unsubscribe/opt-out list"""
        try:
            with open(self.optout_file, "r") as f:
                optouts = json.load(f)
                return email.strip().lower() in [e.strip().lower() for e in optouts]
        except Exception as e:
            print(f"[EmailSender] Error reading optouts: {e}")
            return False

    def unsubscribe(self, email: str) -> bool:
        """Opt-out an email from future outreach"""
        try:
            with open(self.optout_file, "r") as f:
                optouts = json.load(f)
            
            clean_email = email.strip().lower()
            if clean_email not in optouts:
                optouts.append(clean_email)
                with open(self.optout_file, "w") as f:
                    json.dump(optouts, f, indent=2)
                print(f"[EmailSender] Successfully unsubscribed: {clean_email}")
                return True
        except Exception as e:
            print(f"[EmailSender] Error unsubscribing: {e}")
        return False

    def get_default_template(self) -> str:
        """Returns the default cold outreach email template"""
        return """Subject: {% if business_name %}{{ business_name }} — {% endif %}your free website demo is ready!

Hi{% if contact_name %} {{ contact_name }}{% else %}{% endif %},

I was looking at local businesses in the area on Google Maps and noticed that {{ business_name }} doesn't have an online website yet. In today's digital world, having a web presence is key to getting discovered by new customers.

To help you get started, we built a fully-working free website demo specifically for {{ business_name }}. You can check it out live right here:

{{ demo_url }}

If you like what you see, we can move this to your own custom domain (e.g. www.{{ business_name | replace(" ", "") | lower }}.com) and make any edits you'd like for a one-time build fee of $1,000, followed by $99/month for hosting, maintenance, and updates.

Would you be open to a quick call or reply to discuss making this your official website?

Best regards,
The SiteForge Team
support@siteforge.com

---
If you do not wish to receive any more emails from us, please reply with "Unsubscribe" or opt out here: http://siteforge.com/unsubscribe?email={{ email | urlencode }}
"""

    def send_cold_email(self, to_email: str, business_name: str, demo_url: str, contact_name: Optional[str] = None, template_str: Optional[str] = None) -> bool:
        """
        Renders the cold outreach template and sends it to the recipient.
        """
        if self.is_unsubscribed(to_email):
            print(f"[EmailSender] Aborted send. Recipient {to_email} is unsubscribed.")
            return False

        # Prepare template variables
        variables = {
            "business_name": business_name,
            "demo_url": demo_url,
            "contact_name": contact_name,
            "email": to_email
        }

        # Render template
        template_text = template_str or self.get_default_template()
        rendered = Template(template_text).render(**variables)

        # Split subject and body from the rendered output
        subject = f"{business_name} — your free website demo is ready!"
        body = rendered
        
        lines = rendered.split("\n")
        if lines[0].startswith("Subject:"):
            subject = lines[0].replace("Subject:", "").strip()
            body = "\n".join(lines[1:]).strip()

        print(f"[EmailSender] Sending email to {to_email} via {self.provider}...")
        
        if self.provider == "mock" or not self.api_key:
            return self._send_mock(to_email, subject, body)
        elif self.provider == "resend":
            return self._send_resend(to_email, subject, body)
        elif self.provider == "sendgrid":
            return self._send_sendgrid(to_email, subject, body)
        else:
            print(f"[EmailSender] Unknown provider {self.provider}. Falling back to mock.")
            return self._send_mock(to_email, subject, body)

    def _send_mock(self, to: str, subject: str, body: str) -> bool:
        """Saves email locally to file for verification and debugging"""
        log_file = "/home/team/shared/outreach/sent_emails.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        import time
        sent_record = {
            "to": to,
            "from": self.from_email,
            "subject": subject,
            "body": body,
            "timestamp": time.time()
        }
        
        try:
            records = []
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    records = json.load(f)
            records.append(sent_record)
            with open(log_file, "w") as f:
                json.dump(records, f, indent=2)
            print(f"[EmailSender][MOCK] Simulated email sent successfully to {to}.")
            return True
        except Exception as e:
            print(f"[EmailSender][MOCK] Failed to save mock email: {e}")
            return False

    def _send_resend(self, to: str, subject: str, body: str) -> bool:
        """Send via Resend API"""
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": self.from_email,
            "to": [to],
            "subject": subject,
            "text": body
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code in (200, 201):
                print(f"[EmailSender][Resend] Email sent to {to} successfully.")
                return True
            else:
                print(f"[EmailSender][Resend] Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[EmailSender][Resend] Connection error: {e}")
            return False

    def _send_sendgrid(self, to: str, subject: str, body: str) -> bool:
        """Send via SendGrid API"""
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self.from_email.split("<")[-1].replace(">", "").strip(), "name": "SiteForge"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code in (200, 202):
                print(f"[EmailSender][SendGrid] Email sent to {to} successfully.")
                return True
            else:
                print(f"[EmailSender][SendGrid] Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[EmailSender][SendGrid] Connection error: {e}")
            return False

# Simple self-test
if __name__ == "__main__":
    sender = EmailSender()
    print("Testing mock email send...")
    sender.send_cold_email(
        to_email="test@example.com",
        business_name="Joe's Pizza",
        demo_url="https://joes-pizza-demo.siteforge.com",
        contact_name="Joe"
    )
    print("Opting out test@example.com...")
    sender.unsubscribe("test@example.com")
    print(f"Is test@example.com unsubscribed? {sender.is_unsubscribed('test@example.com')}")
    print("Attempting to email unsubscribed recipient:")
    sender.send_cold_email(
        to_email="test@example.com",
        business_name="Joe's Pizza",
        demo_url="https://joes-pizza-demo.siteforge.com"
    )
