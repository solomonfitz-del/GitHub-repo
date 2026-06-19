# SiteForge Outreach Pipeline

This directory contains the automated cold outreach pipeline for SiteForge. The pipeline finds emails for scraped local business leads, sends them personalized cold emails featuring their unique static website demo, analyzes their replies, and automatically responds to common Q&A queries.

## Components

The pipeline consists of the following modular Python scripts:

1. **`email_finder.py`** (`EmailFinder`):
   - Integrates with Hunter.io's Domain Search and Email Finder APIs.
   - Fallback scraper: If no API key is set or no professional emails are found, it scrapes the business domain home page for contact email addresses using robust pattern extraction.

2. **`email_sender.py`** (`EmailSender`):
   - Sends templated cold emails via **Resend** or **SendGrid** API.
   - Personalizes email templates with `{{ business_name }}`, `{{ demo_url }}`, and `{{ contact_name }}` using Jinja2 templating.
   - Includes opt-out / unsubscribe safety mechanisms: saves unsubscribed emails to `optouts.json` and prevents any future sends to them.
   - Fallback mock mode: If no email API key is configured, it simulates sending by saving emails to `sent_emails.json` for validation and debugging.

3. **`reply_classifier.py`** (`ReplyClassifier`):
   - Categorizes inbound prospect responses using **OpenAI's `gpt-4o-mini`** (via the modern `openai` client) with structured JSON outputs.
   - Categorizes reply intent into exactly one of:
     - `interested`: Prospect wants to proceed, buy, schedule a call, or test the demo.
     - `not_interested`: Prospect wants to unsubscribe, rejects the offer, or already has a site.
     - `has_questions`: Prospect has specific questions (pricing, domains, edits, timeline).
     - `unclear`: Short, vague, or Out-of-Office responses.
   - Fallback rule-based mode: Contains robust keyword/regex parsing if OpenAI API is unavailable.

4. **`auto_responder.py`** (`AutoResponder`):
   - Generates high-quality responses to Q&A replies.
   - Uses OpenAI's LLM to dynamically draft a cohesive, friendly email that specifically addresses the prospect's questions based on an FAQ knowledge context.
   - Fallback template responder: Matches questions against `faq.json` topics and stiches answers together.
   - Appends a call-to-action inviting them to secure their build with a Stripe checkout link.

---

## Required API Keys & Configuration

The modules read configuration from environment variables. You can store these in a `.env` file in the root or export them in your shell:

| Environment Variable | Description | Example / Format |
|----------------------|-------------|------------------|
| `HUNTER_API_KEY` | Hunter.io API key for finding professional email addresses. | `3a9f...` |
| `EMAIL_API_KEY` | API key for the email sending service (Resend or SendGrid). | `re_abc123...` (Resend) or `SG.xyz...` (SendGrid) |
| `EMAIL_PROVIDER` | Email provider to use. Auto-detected from key prefix if omitted. | `resend` or `sendgrid` |
| `FROM_EMAIL` | Sender address shown to prospects. | `SiteForge <outreach@siteforge.com>` |
| `LLM_API_KEY` | OpenAI API key for reply intent classification and Q&A drafting. | `sk-proj-...` |
| `LLM_MODEL` | OpenAI model to use. Defaults to `gpt-4o-mini`. | `gpt-4o-mini` |
| `STRIPE_PAYMENT_LINK`| Stripe Payment Link for the $1,000 build fee + $99/mo subscription. | `https://buy.stripe.com/...` |
| `OPTOUT_FILE_PATH` | Path to store unsubscribed emails. Defaults to `./optouts.json`. | `/home/team/shared/outreach/optouts.json` |

---

## Installation & Setup

1. A virtual environment has been configured in this directory:
   ```bash
   # Activate virtual environment
   source /home/team/shared/outreach/venv/bin/activate
   ```

2. Required packages (`requests`, `openai`, `python-dotenv`, `jinja2`) are already installed. If you need to re-install:
   ```bash
   pip install -r requirements.txt
   ```

## Usage Example

### Running Self-Tests
Each module is self-testable by running it directly:

```bash
# Test Email Finding (with fallback scrape)
python3 email_finder.py example.com

# Test Email Sending (Mock mode)
python3 email_sender.py

# Test Reply Classification
python3 reply_classifier.py

# Test Auto-Responder Q&A Drafting
python3 auto_responder.py
```

### Integrated End-to-End Flow (Example Script)
To run the full outreach loop, you can import and compose these modules as follows:

```python
from email_finder import EmailFinder
from email_sender import EmailSender
from reply_classifier import ReplyClassifier
from auto_responder import AutoResponder

# 1. Initialize pipeline
finder = EmailFinder()
sender = EmailSender()
classifier = ReplyClassifier()
responder = AutoResponder()

# 2. Process a new lead
lead = {
    "business_name": "Sparkle Nails & Spa",
    "domain": "sparklenailslocal.com",
    "contact_name": "Sarah Jenkins"
}

# Find email
email = finder.find_email_by_name(lead["business_name"], lead["domain"], lead["contact_name"])
if email:
    # Send cold outreach
    sender.send_cold_email(
        to_email=email,
        business_name=lead["business_name"],
        demo_url="https://sparkle-nails-demo.siteforge.com",
        contact_name=lead["contact_name"]
    )

# 3. Classify an incoming response
incoming_email = "This is Sarah from Sparkle Nails. The demo site looks beautiful! How long does it take to go live once we pay? Also can we change the background to soft pink?"

analysis = classifier.classify_reply(incoming_email)
print(f"Classification: {analysis['intent']}")

if analysis["intent"] == "has_questions":
    # Draft automatic Q&A response
    draft = responder.draft_response(
        sender_name="Sarah",
        business_name=lead["business_name"],
        questions=analysis["questions"],
        reply_text=incoming_email
    )
    print(f"Auto-Response Draft:\n{draft}")
```
