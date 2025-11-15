import os
import json
from dotenv import load_dotenv
from google import genai

# 1) Load .env and configure client
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"  # or gemini-2.0-flash / gemini-2.5-flash if enabled


PROMPT_TEMPLATE = """
You are a cybersecurity and online safety analyst.

You will receive metadata about a single social media post and you must ONLY evaluate
the TITLE of the post from a digital-safety perspective.

Digital-safety / cybersecurity risks include:
- Scams, phishing, fraud, or attempts to steal money or credentials
- Malware, suspicious downloads, links that try to hack or infect users
- Encouraging hacking, DDoS, or other cyberattacks
- Sexual exploitation or grooming
- Encouraging self-harm or suicide
- Severe harassment, hate, or threats
- Doxxing, leaking personal data (addresses, phone numbers, etc.)

Your job:
1. Read the TITLE.
2. Decide if the title is generally GOOD (safe/harmless) or BAD (suspicious, risky, or harmful).
3. Give a numeric threat_score between 0 and 100, where:
   - 0–20  = clearly safe / normal content
   - 21–40 = slightly concerning but probably okay
   - 41–70 = medium risk, should be warned or checked
   - 71–100= high risk, strongly unsafe

OUTPUT FORMAT (VERY IMPORTANT):
Return ONLY valid JSON and NOTHING else.

The JSON MUST have these exact keys:
{{
  "record_id": <integer>,
  "title": "<original title>",
  "verdict": "<good | bad>",
  "threat_score": <integer 0-100>,
  "reason": "<short explanation in one or two sentences>"
}}

Here is the post data:

record_id: {record_id}
source   : {source}
author   : {author}
title    : {title}
link     : {link}
"""


def analyze_title(record: dict) -> dict:
    """
    Analyze a single post record (like the TikTok objects you showed)
    and return a JSON-serializable dict with verdict and threat_score.
    """
    # Extract needed fields with sensible defaults
    record_id = record.get("record_id", 0)
    source = record.get("source", "")
    author = record.get("author", "")
    title = record.get("title", "")
    link = record.get("link", "")

    prompt = PROMPT_TEMPLATE.format(
        record_id=record_id,
        source=source,
        author=author,
        title=title,
        link=link,
    )

    # Call Gemini
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    raw_text = response.text.strip()

    # Parse JSON safely
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to salvage a JSON block if model added something extra
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1:
            try:
                result = json.loads(raw_text[start:end+1])
            except Exception:
                result = _fallback_result(record_id, title, raw_text)
        else:
            result = _fallback_result(record_id, title, raw_text)

    # Ensure keys exist and are in correct types
    result.setdefault("record_id", record_id)
    result.setdefault("title", title)
    result.setdefault("verdict", "good")  # default to good if uncertain
    result.setdefault("threat_score", 0)
    result.setdefault("reason", "No reason provided.")

    # Coerce threat_score into [0, 100]
    try:
        ts = int(result["threat_score"])
        ts = max(0, min(100, ts))
        result["threat_score"] = ts
    except Exception:
        result["threat_score"] = 0

    return result


def _fallback_result(record_id: int, title: str, raw_text: str) -> dict:
    return {
        "record_id": record_id,
        "title": title,
        "verdict": "good",
        "threat_score": 0,
        "reason": "Failed to parse model output. Treating as safe. Raw: " + raw_text[:200],
    }


if __name__ == "__main__":
    # Quick test with one of your examples
    sample_record = {
        "record_id": 5,
        "source": "TikTok",
        "title": "Faker: The Cold Motherfucker of League of Legends | TikTok",
        "link": "https://www.tiktok.com/@thescoreesports/video/7368595180448009477",
        "thumbnail": "https://serpapi.com/searches/691886d2e6590e05f8e6a2ba/images/d0fd73998e227f1c8b34127fe977e324896df2ef334a9c4bb795a96b0c2bd891.jpeg",
        "author": "thescoreesports",
        "link_to_author": "https://www.tiktok.com/@thescoreesports",
        "post_id": 7569741263415659831
    }

    print(analyze_title(sample_record))
