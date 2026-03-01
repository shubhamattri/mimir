#!/usr/bin/env python3
"""
WhatsApp Chat Cleaner — Extract your messages into clean text files.

Input:  data/raw/whatsapp/*.txt (WhatsApp "Export Chat" .txt files)
Output: data/cleaned/whatsapp/<chat_name>.txt (your messages only, cleaned)

WhatsApp export format (varies by locale):
  [DD/MM/YY, HH:MM:SS] Sender Name: Message text
  DD/MM/YY, HH:MM:SS - Sender Name: Message text
  [MM/DD/YY, HH:MM:SS] Sender Name: Message text
"""

import os
import re
import sys
from pathlib import Path

# --- Config ---
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw" / "whatsapp"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned" / "whatsapp"

# Your name(s) as they appear in WhatsApp exports.
# Add all variants (different contacts may store your name differently).
YOUR_NAMES = {
    "Shubham",
    "Shubham Attri",
    "You",  # WhatsApp uses "You" when exporting your own messages
}

# Lines matching these patterns are system messages, not real messages
SYSTEM_PATTERNS = [
    r"Messages and calls are end-to-end encrypted",
    r"created group",
    r"added you",
    r"changed the subject",
    r"changed this group",
    r"changed the group",
    r"left$",
    r"removed ",
    r"joined using",
    r"security code changed",
    r"Your security code with .* changed",
    r"Missed (?:voice|video) call",
    r"This message was deleted",
    r"You deleted this message",
    r"<Media omitted>",
    r"image omitted",
    r"video omitted",
    r"audio omitted",
    r"sticker omitted",
    r"document omitted",
    r"GIF omitted",
    r"Contact card omitted",
    r"Location: https://",
    r"Live location shared",
    r"\u200e",  # Left-to-right mark (WhatsApp system marker)
]

SYSTEM_RE = re.compile("|".join(SYSTEM_PATTERNS), re.IGNORECASE)

# Regex to match the start of a WhatsApp message line
# Handles: [DD/MM/YY, HH:MM:SS] or DD/MM/YY, HH:MM:SS - or [MM/DD/YY, ...]
MSG_RE = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]?\s*[-–]?\s*"
    r"([^:]+?):\s(.+)"
)


def is_your_message(sender: str) -> bool:
    """Check if the sender matches any of your known names."""
    sender_clean = sender.strip()
    return any(
        sender_clean.lower() == name.lower() or sender_clean.lower().startswith(name.lower())
        for name in YOUR_NAMES
    )


def is_system_message(text: str) -> bool:
    """Check if text is a WhatsApp system message."""
    return bool(SYSTEM_RE.search(text))


def clean_message(text: str) -> str:
    """Clean a single message text."""
    # Remove URLs (optional — keep if you want link context)
    # text = re.sub(r'https?://\S+', '[link]', text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_chat(filepath: Path) -> list[str]:
    """Parse a WhatsApp export file and return your cleaned messages."""
    messages = []
    current_msg = None
    current_sender = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            match = MSG_RE.match(line)

            if match:
                # Save previous message if it was yours
                if current_msg is not None and is_your_message(current_sender):
                    cleaned = clean_message(current_msg)
                    if cleaned and not is_system_message(cleaned):
                        messages.append(cleaned)

                # Start new message
                current_sender = match.group(3)
                current_msg = match.group(4)
            elif current_msg is not None:
                # Continuation of previous message (multi-line)
                current_msg += " " + line.strip()

    # Don't forget the last message
    if current_msg is not None and is_your_message(current_sender):
        cleaned = clean_message(current_msg)
        if cleaned and not is_system_message(cleaned):
            messages.append(cleaned)

    return messages


def group_consecutive(messages: list[str], max_group: int = 5) -> list[str]:
    """Group consecutive short messages into paragraphs.

    WhatsApp conversations often have rapid-fire short messages that are
    really one thought. Grouping them makes better training data.
    """
    grouped = []
    buffer = []

    for msg in messages:
        buffer.append(msg)
        # Flush if buffer is full or message is long enough to stand alone
        if len(buffer) >= max_group or len(msg) > 200:
            grouped.append(" ".join(buffer))
            buffer = []

    if buffer:
        grouped.append(" ".join(buffer))

    return grouped


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = list(RAW_DIR.glob("*.txt"))
    if not raw_files:
        print(f"No .txt files found in {RAW_DIR}")
        print("Export your WhatsApp chats and place the .txt files there.")
        sys.exit(1)

    total_messages = 0
    total_files = 0

    for filepath in sorted(raw_files):
        chat_name = filepath.stem  # e.g., "WhatsApp Chat with John"
        # Clean up the filename
        clean_name = chat_name.replace("WhatsApp Chat with ", "").replace(" ", "_")

        print(f"Processing: {filepath.name}")
        messages = parse_chat(filepath)
        grouped = group_consecutive(messages)

        if not grouped:
            print(f"  Skipped (no messages from you)")
            continue

        # Write cleaned output
        out_path = CLEAN_DIR / f"{clean_name}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# Conversation: {chat_name}\n")
            f.write(f"# Messages from: Shubham\n")
            f.write(f"# Total messages: {len(messages)} (grouped into {len(grouped)} chunks)\n\n")
            for chunk in grouped:
                f.write(chunk + "\n\n")

        total_messages += len(messages)
        total_files += 1
        print(f"  {len(messages)} messages → {out_path.name}")

    print(f"\nDone: {total_messages} messages from {len(raw_files)} chats → {total_files} cleaned files")
    print(f"Output: {CLEAN_DIR}")


if __name__ == "__main__":
    main()
