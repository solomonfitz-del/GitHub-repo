import os
import re
import requests
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailFinder:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the EmailFinder with an optional Hunter.io API key.
        If not provided, it will check the HUNTER_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")

    def find_emails_by_domain(self, domain: str) -> List[str]:
        """
        Query Hunter.io Domain Search API to find emails associated with a domain.
        """
        if not self.api_key:
            print("[EmailFinder] Warning: HUNTER_API_KEY is not set. Skipping Hunter.io search.")
            return []

        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "domain": domain,
            "api_key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                emails_data = data.get("data", {}).get("emails", [])
                return [item.get("value") for item in emails_data if item.get("value")]
            else:
                print(f"[EmailFinder] Hunter.io API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[EmailFinder] Error calling Hunter.io Domain Search: {e}")
        
        return []

    def find_email_by_name(self, business_name: str, domain: str, contact_name: Optional[str] = None) -> Optional[str]:
        """
        Find a specific contact email. If contact_name is provided, it uses the
        Hunter.io Email Finder API. Otherwise, it retrieves the domain emails and returns the first one.
        """
        if not self.api_key:
            return self.scrape_emails_from_web(domain) if domain else None

        if contact_name:
            parts = contact_name.strip().split(maxsplit=1)
            first_name = parts[0] if len(parts) > 0 else ""
            last_name = parts[1] if len(parts) > 1 else ""

            url = "https://api.hunter.io/v2/email-finder"
            params = {
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "company": business_name,
                "api_key": self.api_key
            }
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    email = data.get("data", {}).get("email")
                    if email:
                        return email
            except Exception as e:
                print(f"[EmailFinder] Error calling Hunter.io Email Finder: {e}")

        # Fallback: get first available domain email
        emails = self.find_emails_by_domain(domain)
        if emails:
            return emails[0]

        # Final fallback: web scrape the domain
        return self.scrape_emails_from_web(domain) if domain else None

    def scrape_emails_from_web(self, domain: str) -> Optional[str]:
        """
        Fallback scraper: Fetches the main page of the domain and searches for email regex.
        """
        if not domain:
            return None
            
        # Normalize domain URL
        url = domain if domain.startswith(("http://", "https://")) else f"https://{domain}"
        
        try:
            print(f"[EmailFinder] Attempting fallback scrape of website: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=8, verify=False)
            if response.status_code == 200:
                html = response.text
                # Find common email pattern
                email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
                emails = re.findall(email_pattern, html)
                
                # Filter out image/asset extensions that might match
                filtered_emails = []
                invalid_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
                for email in emails:
                    if not email.lower().endswith(invalid_extensions):
                        filtered_emails.append(email)
                        
                if filtered_emails:
                    found = list(set(filtered_emails))[0]
                    print(f"[EmailFinder] Scrape success! Found email: {found}")
                    return found
        except Exception as e:
            print(f"[EmailFinder] Fallback scrape failed for {domain}: {e}")
            
        return None

# Simple self-test
if __name__ == "__main__":
    import sys
    finder = EmailFinder()
    test_domain = "example.com"
    if len(sys.argv) > 1:
        test_domain = sys.argv[1]
    print(f"Testing Domain Search for: {test_domain}")
    emails = finder.find_emails_by_domain(test_domain)
    print(f"Emails found via Hunter.io: {emails}")
    if not emails:
        print("Trying fallback scraping...")
        scraped = finder.scrape_emails_from_web(test_domain)
        print(f"Emails found via Scraping: {scraped}")
