import os
import json
import re
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ReplyClassifier:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the ReplyClassifier with an optional OpenAI API key.
        If not provided, checks:
        1. LLM_API_KEY environment variable (specified in instructions)
        2. OPENAI_API_KEY environment variable
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL") or model
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("[ReplyClassifier] Warning: Neither LLM_API_KEY nor OPENAI_API_KEY is set. Using rule-based fallback.")

    def classify_reply(self, reply_text: str) -> Dict[str, Any]:
        """
        Classifies the reply text using OpenAI LLM if available, otherwise falls back to a rule-based classifier.
        Returns a dictionary with:
        {
            "intent": "interested" | "not_interested" | "has_questions" | "unclear",
            "reason": str,
            "questions": list of str,
            "suggested_action": str
        }
        """
        if not reply_text or not reply_text.strip():
            return {
                "intent": "unclear",
                "reason": "Empty reply text.",
                "questions": [],
                "suggested_action": "manual_review"
            }

        if self.client:
            try:
                return self._classify_llm(reply_text)
            except Exception as e:
                print(f"[ReplyClassifier] LLM classification failed ({e}). Falling back to rule-based.")
                return self._classify_rules(reply_text)
        else:
            return self._classify_rules(reply_text)

    def _classify_llm(self, reply_text: str) -> Dict[str, Any]:
        """Uses OpenAI to classify reply text with JSON mode enabled"""
        system_prompt = """You are an expert sales assistant for SiteForge, a website development agency.
Analyze the inbound cold email reply and classify the sender's intent.

Classify into exactly one of the following four categories:
1. "interested" — The sender expresses interest in a website, getting a build, buying, scheduling a call, or proceeding with the demo site.
2. "not_interested" — The sender rejects the offer, says "No thanks", "Stop emailing", "Unsubscribe", or indicates they already have a website or don't need one.
3. "has_questions" — The sender is asking specific questions about pricing, features, who we are, security, timeline, custom domains, or edits to the site.
4. "unclear" — The reply is too short, ambiguous, vague, or is an auto-response (e.g., Out of Office).

You must return a valid JSON object with the following fields:
- "intent": (string) one of ["interested", "not_interested", "has_questions", "unclear"]
- "reason": (string) a concise 1-sentence explanation of why you classified it this way.
- "questions": (array of strings) list any specific questions the sender asked (empty array if none).
- "suggested_action": (string) one of ["send_payment_link", "unsubscribe", "reply_to_questions", "manual_review", "ignore"]

Your output must be strictly valid JSON and nothing else."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Reply to analyze:\n\"\"\"\n{reply_text}\n\"\"\""}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
            timeout=15
        )

        result_content = response.choices[0].message.content
        return json.loads(result_content)

    def _classify_rules(self, reply_text: str) -> Dict[str, Any]:
        """Simple rule-based regex backup classifier if LLM is unavailable"""
        text = reply_text.lower().strip()
        
        # 1. Unsubscribe / Not interested rules
        unsub_patterns = [
            r"\bunsubscribe\b", r"\bstop\b", r"\bremove\b", r"\bno thanks\b", 
            r"\bnot interested\b", r"\bdont email\b", r"\bdelete me\b", r"\bno\b",
            r"\balready have\b", r"\balready built\b", r"\bspam\b", r"\bbother\b"
        ]
        for pattern in unsub_patterns:
            if re.search(pattern, text):
                return {
                    "intent": "not_interested",
                    "reason": f"Matched rule-based opt-out pattern: '{pattern}'",
                    "questions": [],
                    "suggested_action": "unsubscribe"
                }

        # 2. Q&A / Has questions rules
        question_indicators = ["?", "how much", "cost", "price", "who is", "what is", "where are", "can we", "can you", "details"]
        found_questions = []
        for ind in question_indicators:
            if ind in text:
                if ind == "?":
                    # Try to extract sentence with question mark
                    sentences = re.split(r"[.!?]", reply_text)
                    for s in sentences:
                        if "?" in s:
                            found_questions.append(s.strip() + "?")
                else:
                    found_questions.append(f"Inquired about: '{ind}'")
        
        if found_questions:
            return {
                "intent": "has_questions",
                "reason": "Contains question marks or inquiry keywords.",
                "questions": list(set(found_questions))[:3],
                "suggested_action": "reply_to_questions"
            }

        # 3. Interested rules
        interested_patterns = [
            r"\byes\b", r"\bsounds good\b", r"\binterested\b", r"\blets do it\b",
            r"\bcall\b", r"\btalk\b", r"\bphone\b", r"\bmeet\b", r"\bschedule\b",
            r"\bhow to pay\b", r"\blink\b", r"\bproceed\b", r"\bdemo\b"
        ]
        for pattern in interested_patterns:
            if re.search(pattern, text):
                return {
                    "intent": "interested",
                    "reason": f"Matched rule-based interest pattern: '{pattern}'",
                    "questions": [],
                    "suggested_action": "send_payment_link"
                }

        # 4. Default: Unclear
        return {
            "intent": "unclear",
            "reason": "Vague or short reply. No rules matched.",
            "questions": [],
            "suggested_action": "manual_review"
        }

# Simple self-test
if __name__ == "__main__":
    classifier = ReplyClassifier()
    
    test_replies = [
        "Unsubscribe me immediately, I am not interested.",
        "This actually looks really cool. How much would it be to add a custom contact form?",
        "Yes, I am interested in proceeding with the $1000 build. How do we get started?",
        "Please call me at 555-0199 tomorrow afternoon.",
        "I am currently out of the office returning on Tuesday."
    ]
    
    print("Running reply classification tests:")
    for reply in test_replies:
        print("\n" + "="*50)
        print(f"Reply: \"{reply}\"")
        classification = classifier.classify_reply(reply)
        print("Classification Result:")
        print(json.dumps(classification, indent=2))
