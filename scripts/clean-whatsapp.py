#!/usr/bin/env python3
"""
WhatsApp Chat Cleaner — Extract your messages into clean, SAFE text files.

TWO-PASS SAFETY:
  Pass 1: Keyword filter (fast, catches obvious stuff)
  Pass 2: Local AI classifier via Ollama (catches Hinglish, Punjabi, innuendo)

Every message goes through both passes. If EITHER flags it, it's dropped.
All processing happens locally via Ollama — nothing leaves your machine.

Input:  data/raw/whatsapp/*.txt
Output: data/cleaned/whatsapp/<chat_name>.txt (sanitized, safe for knowledge base)
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# --- Config ---
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw" / "whatsapp"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned" / "whatsapp"
QUARANTINE_DIR = PROJECT_DIR / "data" / "quarantined" / "whatsapp"

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CLASSIFIER_MODEL = os.environ.get("CLASSIFIER_MODEL", "qwen3:8b")

# Batch size for AI classification (trade-off: speed vs accuracy)
# Higher = faster (fewer API calls) but slightly less accurate per-message
AI_BATCH_SIZE = 50

# Max chars sent to AI per message (full msg not needed for tone detection)
AI_TRUNCATE_LEN = 120

# Messages this short with no NSFW signals are obviously safe — skip AI
OBVIOUS_SAFE_MAX_LEN = 40
OBVIOUS_SAFE_RE = re.compile(
    r"^("
    r"ok[ay]*|yes|no|yeah|yep|nope|nah|haan|nahi|ha|hmm+|haha+|lol|lmao"
    r"|done|coming|ok done|accha|theek hai|sahi hai|chal|chalo|acha"
    r"|good morning|good night|gm|gn|thanks|thank you|ty|thx|shukriya"
    r"|hello|hi|hey|bye|see you|ttyl|brb|k|kk|ohh*|ah+|nice|cool|great"
    r"|what|when|where|why|how|who|kya|kab|kaha|kaise|kaun"
    r"|send|sent|check|done|noted|sure|definitely|absolutely|got it"
    r"|on my way|omw|reaching|reached|left|leaving|coming in \d+"
    r"|one sec|wait|hold on|ruk|ek min|2 min|5 min|\d+ min"
    r")$",
    re.IGNORECASE,
)

# Your name(s) as they appear in WhatsApp exports
YOUR_NAMES = {
    "Shubham",
    "Shubham Attri",
    "You",
}

# =============================================================================
# PASS 1: KEYWORD FILTER (fast, catches obvious)
# =============================================================================

NSFW_KEYWORDS = [
    # English
    r"\bsex\b", r"\bsexy\b", r"\bnude[s]?\b", r"\bnaked\b",
    r"\bhorny\b", r"\bcum\b", r"\bcumm", r"\bdick\b", r"\bcock\b",
    r"\bpussy\b", r"\bboob[s]?\b", r"\btits?\b",
    r"\bfuck", r"\bblowjob", r"\bhandjob", r"\borgasm",
    r"\bmasturbat", r"\bporn", r"\bxxx\b", r"\berotic",
    r"\bkink", r"\bfetish", r"\bthreesome", r"\blingerie\b",
    r"\bcondom[s]?\b", r"\bmoaning\b", r"\bsext",
    r"\bnaughty\b", r"\bdirty.?talk", r"\bturn.?me.?on",
    r"\bcome.?to.?bed\b", r"\bwhat.?are.?you.?wearing\b",
    r"\bsend.?pic", r"\bsend.?nud",
    # Hindi / Hinglish
    r"\bchut\b", r"\blund\b", r"\bgand\b", r"\brandi\b",
    r"\bchod\b", r"\bchud\b", r"\bbhosd", r"\bmadarchod",
    r"\bbehenchod", r"\bjhaant\b", r"\bchuchi\b",
    r"\bsuhaagraat\b", r"\bsuhagraat\b",
    # Punjabi
    r"\bkudi\b.*\b(?:hot|sexy)", r"\bpenchod\b", r"\bkutt[ie]\b",
    # Romantic/intimate context
    r"\bi.?love.?you\b", r"\blove.?you.?(?:baby|jaan|jaanu|shona|babu)\b",
    r"\bmiss.?you.?(?:so.?much|baby|jaan|jaanu)\b",
    r"\bbaby\b", r"\bbabu\b", r"\bjaan[u]?\b", r"\bshona\b",
    r"\bdarling\b", r"\bhoney\b", r"\bsweetie\b",
    r"\bkiss\b", r"\bhug\b", r"\bcuddle\b",
    r"\bgood.?night.?(?:baby|jaan|love|babu)\b",
    r"\bgood.?morning.?(?:baby|jaan|love|babu)\b",
]

NSFW_RE = re.compile("|".join(NSFW_KEYWORDS), re.IGNORECASE)

# =============================================================================
# PII SANITIZATION
# =============================================================================

PII_PATTERNS = [
    (r"\+?\d{1,3}[-.\s]?\d{4,5}[-.\s]?\d{4,5}", "[PHONE]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[AADHAAR]"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN]"),
    (r"\b\d{9,18}\b", "[ACCOUNT]"),
    (r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "[IFSC]"),
    (r"https?://\S+", "[LINK]"),
    (r"\b\d{1,5}\s+(?:sector|block|plot|flat|house|floor|gali|lane|road|street|colony|nagar|vihar|enclave|apartment|society)\b[^.]*", "[ADDRESS]"),
]

PII_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in PII_PATTERNS]

# =============================================================================
# SYSTEM MESSAGE FILTER
# =============================================================================

SYSTEM_PATTERNS = [
    r"Messages and calls are end-to-end encrypted",
    r"created group", r"added you", r"changed the subject",
    r"changed this group", r"changed the group",
    r"left$", r"removed ", r"joined using",
    r"security code changed", r"Your security code with .* changed",
    r"Missed (?:voice|video) call",
    r"This message was deleted", r"You deleted this message",
    r"<Media omitted>", r"image omitted", r"video omitted",
    r"audio omitted", r"sticker omitted", r"document omitted",
    r"GIF omitted", r"Contact card omitted",
    r"Location: https://", r"Live location shared",
    r"\u200e",
]

SYSTEM_RE = re.compile("|".join(SYSTEM_PATTERNS), re.IGNORECASE)

MSG_RE = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]?\s*[-\u2013]?\s*"
    r"([^:]+?):\s(.+)"
)


# =============================================================================
# PASS 2: LOCAL AI CLASSIFIER
# =============================================================================

CLASSIFIER_SYSTEM_PROMPT = """You are an AGGRESSIVE content safety filter. Your job: classify messages for a PROFESSIONAL knowledge base.

Mark UNSAFE if the message has ANY of: romantic language, pet names (baby/jaan/jaanu/babu/shona/darling/honey), sexual content, flirting, innuendo, intimate requests, missing someone romantically, couple fights, emotional manipulation. Works across English, Hindi, Hinglish, Punjabi.

Mark SAFE only if the message is clearly: work talk, tech, opinions, food/travel logistics, news, general greetings to friends/family (bhai/yaar/dude).

WHEN IN DOUBT → UNSAFE. Reply ONLY one word per line: SAFE or UNSAFE. No explanations."""


def classify_with_ollama(messages: list[str]) -> list[bool]:
    """Classify messages as safe/unsafe using local Ollama chat API.

    Uses chat endpoint with think:false (required for Qwen3 thinking models).
    Returns list of bools: True = safe, False = unsafe.
    """
    if not messages:
        return []

    # Build numbered message list (truncated — full text not needed for tone detection)
    numbered = "\n".join(
        f"{i+1}. {msg[:AI_TRUNCATE_LEN]}" for i, msg in enumerate(messages)
    )

    payload = json.dumps({
        "model": CLASSIFIER_MODEL,
        "messages": [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": numbered},
        ],
        "stream": False,
        "think": False,  # Disable thinking mode (critical for Qwen3)
        "options": {
            "temperature": 0.0,
            "num_predict": len(messages) * 10,
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            # Chat API returns message.content, generate API returns response
            msg = result.get("message", {})
            response_text = msg.get("content", "") or result.get("response", "")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"    WARNING: Ollama classification failed ({e}). Marking batch as UNSAFE for safety.")
        return [False] * len(messages)

    # Parse response — one SAFE/UNSAFE per line
    lines = [l.strip().upper() for l in response_text.strip().split("\n") if l.strip()]

    results = []
    for i in range(len(messages)):
        if i < len(lines):
            # Look for SAFE/UNSAFE in the line (model might add numbers or punctuation)
            line = lines[i]
            if "SAFE" in line and "UNSAFE" not in line:
                results.append(True)
            else:
                # Default to UNSAFE if unclear
                results.append(False)
        else:
            # Model returned fewer lines than messages — mark remaining as unsafe
            results.append(False)

    return results


def check_ollama_available() -> bool:
    """Check if Ollama is running and the classifier model is available."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            # Check for model name (with or without :latest suffix)
            return any(CLASSIFIER_MODEL in m for m in models)
    except Exception:
        return False


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def is_your_message(sender: str) -> bool:
    sender_clean = sender.strip()
    return any(
        sender_clean.lower() == name.lower() or sender_clean.lower().startswith(name.lower())
        for name in YOUR_NAMES
    )


def is_system_message(text: str) -> bool:
    return bool(SYSTEM_RE.search(text))


def is_nsfw_keyword(text: str) -> bool:
    return bool(NSFW_RE.search(text))


def sanitize_pii(text: str) -> str:
    for pattern, replacement in PII_COMPILED:
        text = pattern.sub(replacement, text)
    return text


def clean_message(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = sanitize_pii(text)
    return text


def parse_chat(filepath: Path) -> list[str]:
    """Parse WhatsApp export, return your raw messages (before safety filtering)."""
    messages = []
    current_msg = None
    current_sender = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            match = MSG_RE.match(line)

            if match:
                if current_msg is not None and is_your_message(current_sender):
                    if not is_system_message(current_msg):
                        messages.append(current_msg)

                current_sender = match.group(3)
                current_msg = match.group(4)
            elif current_msg is not None:
                current_msg += " " + line.strip()

    if current_msg is not None and is_your_message(current_sender):
        if not is_system_message(current_msg):
            messages.append(current_msg)

    return messages


def group_consecutive(messages: list[str], max_group: int = 5) -> list[str]:
    grouped = []
    buffer = []

    for msg in messages:
        buffer.append(msg)
        if len(buffer) >= max_group or len(msg) > 200:
            grouped.append(" ".join(buffer))
            buffer = []

    if buffer:
        grouped.append(" ".join(buffer))

    return grouped


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = list(RAW_DIR.glob("*.txt"))
    if not raw_files:
        print(f"No .txt files found in {RAW_DIR}")
        print("Export your WhatsApp chats and place the .txt files there.")
        sys.exit(1)

    # Check Ollama
    ai_available = check_ollama_available()
    if ai_available:
        print(f"=== WhatsApp Cleaner (AI Safety Mode) ===")
        print(f"Pass 1: Keyword filter ({len(NSFW_KEYWORDS)} patterns)")
        print(f"Pass 2: AI classifier via {CLASSIFIER_MODEL} (local)")
        print(f"Ollama: {OLLAMA_URL}")
    else:
        print(f"=== WhatsApp Cleaner (Keyword-Only Mode) ===")
        print(f"WARNING: Ollama not available at {OLLAMA_URL}")
        print(f"WARNING: AI safety pass DISABLED. Only keyword filtering active.")
        print(f"WARNING: This is NOT safe for Hinglish/Punjabi content.")
        response = input("Continue with keyword-only mode? (y/N) ")
        if response.lower() != "y":
            print("Aborted. Start Ollama first: ollama serve")
            sys.exit(1)

    print()

    total_kept = 0
    total_keyword_killed = 0
    total_ai_killed = 0
    total_files = 0

    for filepath in sorted(raw_files):
        chat_name = filepath.stem
        clean_name = chat_name.replace("WhatsApp Chat with ", "").replace(" ", "_")

        print(f"Processing: {filepath.name}")

        # Extract your messages
        raw_messages = parse_chat(filepath)
        if not raw_messages:
            print(f"  Skipped (no messages from you)")
            continue

        # --- Pass 1: Keyword filter ---
        pass1_safe = []
        pass1_killed = 0
        for msg in raw_messages:
            if is_nsfw_keyword(msg):
                pass1_killed += 1
            else:
                pass1_safe.append(msg)

        print(f"  Pass 1 (keywords): {pass1_killed} removed, {len(pass1_safe)} remain")

        # --- Pass 2: AI classifier (if available) ---
        if ai_available and pass1_safe:
            pass2_safe = []
            pass2_killed = 0
            quarantined = []

            # Pre-filter: skip AI for obviously safe short messages
            needs_ai = []
            obvious_safe_count = 0
            for msg in pass1_safe:
                stripped = msg.strip()
                if len(stripped) <= OBVIOUS_SAFE_MAX_LEN and OBVIOUS_SAFE_RE.match(stripped):
                    pass2_safe.append(msg)
                    obvious_safe_count += 1
                else:
                    needs_ai.append(msg)

            print(f"  Pre-filter:    {obvious_safe_count} obvious safe, {len(needs_ai)} need AI")

            # Process remaining in batches
            for i in range(0, len(needs_ai), AI_BATCH_SIZE):
                batch = needs_ai[i:i + AI_BATCH_SIZE]
                results = classify_with_ollama(batch)

                for msg, is_safe in zip(batch, results):
                    if is_safe:
                        pass2_safe.append(msg)
                    else:
                        pass2_killed += 1
                        quarantined.append(msg)

                # Progress indicator
                processed = min(i + AI_BATCH_SIZE, len(needs_ai))
                print(f"    AI classified: {processed}/{len(needs_ai)}", end="\r")

            print(f"  Pass 2 (AI):       {pass2_killed} removed, {len(pass2_safe)} remain")

            # Save quarantined messages for manual review (you can check what AI flagged)
            if quarantined:
                q_path = QUARANTINE_DIR / f"{clean_name}_quarantined.txt"
                with open(q_path, "w", encoding="utf-8") as f:
                    f.write(f"# Quarantined messages from: {clean_name}\n")
                    f.write(f"# These were flagged by AI as potentially unsafe.\n")
                    f.write(f"# Review manually. If any are safe, add them back.\n\n")
                    for msg in quarantined:
                        f.write(msg + "\n---\n")

            final_messages = pass2_safe
            total_ai_killed += pass2_killed
        else:
            final_messages = pass1_safe

        total_keyword_killed += pass1_killed

        # --- Clean and write output ---
        cleaned = [clean_message(msg) for msg in final_messages if clean_message(msg)]
        grouped = group_consecutive(cleaned)

        if not grouped:
            print(f"  Skipped (no messages survived filtering)")
            continue

        out_path = CLEAN_DIR / f"{clean_name}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# Conversation: {clean_name}\n")
            f.write(f"# Messages from: Shubham (double-sanitized)\n")
            f.write(f"# Kept: {len(cleaned)} | Keyword-killed: {pass1_killed} | AI-killed: {total_ai_killed}\n\n")
            for chunk in grouped:
                f.write(chunk + "\n\n")

        total_kept += len(cleaned)
        total_files += 1
        print(f"  Final: {len(cleaned)} messages saved")

    print(f"\n=== Summary ===")
    print(f"Files:         {total_files} cleaned from {len(raw_files)} chats")
    print(f"Messages kept: {total_kept}")
    print(f"Keyword-killed:{total_keyword_killed}")
    print(f"AI-killed:     {total_ai_killed}")
    print(f"Output:        {CLEAN_DIR}")
    if total_ai_killed > 0:
        print(f"Quarantined:   {QUARANTINE_DIR} (review these manually)")
    print()
    print("NEXT: Review cleaned files before uploading to Open WebUI.")
    print("      Check quarantined files for false positives you want to keep.")


if __name__ == "__main__":
    main()
