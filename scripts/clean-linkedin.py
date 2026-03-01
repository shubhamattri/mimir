#!/usr/bin/env python3
"""
LinkedIn Data Cleaner — Extract your posts, comments, and articles.

Input:  data/raw/linkedin/ (unzipped LinkedIn data export)
Output: data/cleaned/linkedin/posts.txt, comments.txt, articles.txt

LinkedIn data export structure (after unzip):
  - Shares.csv          → Your posts
  - Comments.csv        → Your comments on others' posts
  - Articles.csv        → Long-form articles (if any)
  - Messages.csv        → DMs (optional, high-signal for voice)
  - Profile.csv         → Bio/headline (useful for system prompt)
"""

import csv
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw" / "linkedin"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned" / "linkedin"


def clean_text(text: str) -> str:
    """Clean a single piece of text."""
    if not text:
        return ""
    # Remove excessive whitespace but preserve paragraph breaks
    lines = text.strip().split("\n")
    cleaned = "\n".join(line.strip() for line in lines if line.strip())
    return cleaned


def process_shares(filepath: Path) -> list[str]:
    """Extract posts from Shares.csv."""
    posts = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # LinkedIn Shares.csv has: Date, ShareLink, ShareCommentary, SharedUrl, MediaUrl
            text = row.get("ShareCommentary", "").strip()
            if text and len(text) > 20:  # Skip empty/trivial shares
                posts.append(clean_text(text))
    return posts


def process_comments(filepath: Path) -> list[str]:
    """Extract comments from Comments.csv."""
    comments = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Comments.csv has: Date, Link, Message
            text = row.get("Message", "").strip()
            if text and len(text) > 10:
                comments.append(clean_text(text))
    return comments


def process_articles(filepath: Path) -> list[str]:
    """Extract articles from Articles.csv."""
    articles = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Title", "").strip()
            content = row.get("Content", "").strip()
            if content:
                article = f"# {title}\n\n{clean_text(content)}" if title else clean_text(content)
                articles.append(article)
    return articles


def process_messages(filepath: Path) -> list[str]:
    """Extract your DM messages from Messages.csv (optional, high-signal)."""
    messages = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Messages.csv has: CONVERSATION ID, CONVERSATION TITLE, FROM, SENDER PROFILE URL,
            #                    DATE, SUBJECT, CONTENT
            sender = row.get("FROM", "").strip()
            content = row.get("CONTENT", "").strip()

            # Only keep YOUR messages (name matching)
            if content and len(content) > 20:
                sender_lower = sender.lower()
                if "shubham" in sender_lower:
                    messages.append(clean_text(content))
    return messages


def write_output(items: list[str], filepath: Path, header: str):
    """Write cleaned items to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {header}\n")
        f.write(f"# Total items: {len(items)}\n\n")
        for item in items:
            f.write(item + "\n\n---\n\n")


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # Check what files exist in raw dir
    if not RAW_DIR.exists():
        print(f"Directory not found: {RAW_DIR}")
        print("Download your LinkedIn data and unzip it there.")
        sys.exit(1)

    # Find CSV files (LinkedIn exports may be in subdirectories)
    csv_files = {}
    for pattern in ["Shares.csv", "Comments.csv", "Articles.csv", "Messages.csv", "Profile.csv"]:
        matches = list(RAW_DIR.rglob(pattern))
        if matches:
            csv_files[pattern] = matches[0]

    if not csv_files:
        print(f"No LinkedIn CSV files found in {RAW_DIR}")
        print("Expected files: Shares.csv, Comments.csv, Articles.csv")
        print("Download from: LinkedIn → Settings → Get a copy of your data")
        sys.exit(1)

    total = 0

    # Process each file type
    if "Shares.csv" in csv_files:
        posts = process_shares(csv_files["Shares.csv"])
        if posts:
            write_output(posts, CLEAN_DIR / "posts.txt", "LinkedIn Posts by Shubham")
            total += len(posts)
            print(f"Posts: {len(posts)} extracted")

    if "Comments.csv" in csv_files:
        comments = process_comments(csv_files["Comments.csv"])
        if comments:
            write_output(comments, CLEAN_DIR / "comments.txt", "LinkedIn Comments by Shubham")
            total += len(comments)
            print(f"Comments: {len(comments)} extracted")

    if "Articles.csv" in csv_files:
        articles = process_articles(csv_files["Articles.csv"])
        if articles:
            write_output(articles, CLEAN_DIR / "articles.txt", "LinkedIn Articles by Shubham")
            total += len(articles)
            print(f"Articles: {len(articles)} extracted")

    if "Messages.csv" in csv_files:
        messages = process_messages(csv_files["Messages.csv"])
        if messages:
            write_output(messages, CLEAN_DIR / "messages.txt", "LinkedIn DMs from Shubham")
            total += len(messages)
            print(f"DMs: {len(messages)} extracted")

    print(f"\nDone: {total} total items extracted")
    print(f"Output: {CLEAN_DIR}")


if __name__ == "__main__":
    main()
