import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AutoResponder:
    def __init__(self, faq_path: Optional[str] = None, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the AutoResponder.
        Reads from LLM_API_KEY or OPENAI_API_KEY for drafting replies using OpenAI.
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL") or model
        self.faq_path = faq_path or "/home/team/shared/outreach/faq.json"
        
        # Load FAQ data
        self.faq = self._load_faq()
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("[AutoResponder] Warning: No LLM key set. Using template-based backup responder.")

    def _load_faq(self) -> Dict[str, str]:
        """Loads FAQ questions and answers from a JSON file with hardcoded fallbacks"""
        default_faq = {
            "pricing": "Our pricing is simple and transparent: a one-time setup and custom build fee of $1,000, followed by a recurring monthly subscription of $99/month. This covers secure cloud hosting, SSL certificates, ongoing technical maintenance, and unlimited basic edits/updates.",
            "domain": "We handle the entire domain registration and configuration process for you at no extra cost. If you already own a custom domain name (e.g., www.yourbusiness.com), we will work with you to securely point it to our hosting servers.",
            "edits": "The demo site we built is just a starting prototype! Once you sign up, we will customize everything to your liking: change colors, upload your specific logo, add custom photo galleries, modify sections, and build a working contact/appointment form.",
            "timeline": "We work extremely fast. After receiving your design feedback and setup payment, we will have your polished, 5-page website fully live on your custom domain in just 5 to 7 business days.",
            "who_we_are": "We are SiteForge, a digital design and technology agency specializing in helping local businesses establish a premium online presence. By using our proprietary generation platform, we build high-performing websites at a fraction of the cost of traditional agencies."
        }
        
        if os.path.exists(self.faq_path):
            try:
                with open(self.faq_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[AutoResponder] Error reading FAQ file ({e}). Using default fallback FAQs.")
        else:
            # Save default FAQ file
            try:
                os.makedirs(os.path.dirname(self.faq_path), exist_ok=True)
                with open(self.faq_path, "w") as f:
                    json.dump(default_faq, f, indent=2)
                print(f"[AutoResponder] Created default FAQ file at {self.faq_path}")
            except Exception as e:
                print(f"[AutoResponder] Failed to save default FAQ file ({e})")
                
        return default_faq

    def draft_response(self, sender_name: Optional[str], business_name: str, questions: List[str], reply_text: str) -> str:
        """
        Drafts a highly professional Q&A reply answering the sender's specific questions.
        Uses OpenAI LLM if available, otherwise stitches together answers from the FAQ file.
        """
        payment_link = os.getenv("STRIPE_PAYMENT_LINK") or "https://buy.stripe.com/mock-siteforge-build-fee"
        name_placeholder = sender_name if sender_name else "there"

        if self.client and questions:
            try:
                return self._draft_llm(name_placeholder, business_name, questions, reply_text, payment_link)
            except Exception as e:
                print(f"[AutoResponder] LLM drafting failed ({e}). Falling back to template response.")
                return self._draft_template(name_placeholder, business_name, questions, payment_link)
        else:
            return self._draft_template(name_placeholder, business_name, questions, payment_link)

    def _draft_llm(self, sender_name: str, business_name: str, questions: List[str], reply_text: str, payment_link: str) -> str:
        """Uses OpenAI to write a highly tailored personal email response based on FAQ context"""
        faq_context = "\n".join([f"- {k.upper()}: {v}" for k, v in self.faq.items()])
        
        system_prompt = f"""You are an elite, friendly, and helpful Account Executive for SiteForge.
Your goal is to reply to a prospect who has questions about our cold email offer.

Here is the FAQ context you MUST use to answer their questions:
{faq_context}

Guidelines:
1. Address the sender by name if provided (name is "{sender_name}").
2. Answer all of their questions clearly, accurately, and concisely using the FAQ context. Do NOT invent details that are not in the FAQ.
3. Be professional, warm, and confident.
4. Keep the email relatively short (under 250 words).
5. At the end, invite them to proceed by checking out via our Stripe link: {payment_link} or offer a brief call.
6. Return only the email body text. Do not include any Subject line or metadata."""

        user_content = f"""Prospect Name: {sender_name}
Business Name: {business_name}
Questions identified: {json.dumps(questions)}
Prospect's full message:
\"\"\"
{reply_text}
\"\"\""""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=500,
            timeout=20
        )
        
        return response.choices[0].message.content.strip()

    def _draft_template(self, sender_name: str, business_name: str, questions: List[str], payment_link: str) -> str:
        """Fallback template responder that matches keywords against the FAQ database"""
        # Collect answers based on keyword matching
        answers_to_include = []
        matched_keys = set()
        
        # Simple heuristic keyword matching
        query_text = " ".join(questions).lower()
        
        if any(w in query_text for w in ["price", "cost", "how much", "monthly", "setup", "$"]):
            matched_keys.add("pricing")
        if any(w in query_text for w in ["domain", "url", "domain name", "www"]):
            matched_keys.add("domain")
        if any(w in query_text for w in ["edit", "change", "custom", "logo", "color", "contact form"]):
            matched_keys.add("edits")
        if any(w in query_text for w in ["long", "time", "when", "days", "schedule", "timeline"]):
            matched_keys.add("timeline")
        if any(w in query_text for w in ["who are you", "who is", "siteforge", "agency"]):
            matched_keys.add("who_we_are")
            
        # Default to pricing and edits if no matches were clear
        if not matched_keys:
            matched_keys.add("pricing")
            matched_keys.add("edits")
            
        for key in matched_keys:
            answers_to_include.append(self.faq[key])
            
        answers_str = "\n\n".join([f"• {ans}" for ans in answers_to_include])

        return f"""Hi {sender_name},

Thank you for reaching out! I'd be happy to answer your questions about the website demo we built for {business_name}.

Here are the details you asked about:

{answers_str}

If you're ready to get your professional, fully-working website live on your own custom domain, you can secure your build and start the customization process right here:

{payment_link}

Once checkout is complete, our onboarding team will immediately contact you to gather your feedback, register your custom domain, and make any edits or changes you'd like.

If you have any other questions or would prefer to jump on a quick 5-minute call, please let me know!

Best regards,
The SiteForge Team
support@siteforge.com"""

if __name__ == "__main__":
    responder = AutoResponder()
    print("Testing auto responder with rule-based template fallback:")
    reply = responder.draft_response(
        sender_name="Alice",
        business_name="Alice's Spa & Salon",
        questions=["How much does it cost?", "Can we change the background colors?"],
        reply_text="How much does it cost? Can we change the background colors?"
    )
    print("\nDrafted Reply:\n" + "-"*40)
    print(reply)
