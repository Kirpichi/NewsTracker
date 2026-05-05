import os
import json
import hashlib
import re
import feedparser
import httpx
from datetime import datetime, timezone
from pathlib import Path
from deep_translator import GoogleTranslator

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = Path("seen.json")

FEEDS = [
    # OpenAI
    ("OpenAI", "https://openai.com/blog/rss.xml"),
    # Anthropic
    ("Anthropic", "https://www.anthropic.com/rss.xml"),
    # Hugging Face
    ("HuggingFace", "https://huggingface.co/blog/feed.xml"),
    # Google DeepMind
    ("DeepMind", "https://deepmind.google/blog/rss.xml"),
    # Simon Willison (AI trends, vibe coding, MCP, tools)
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    # Hacker News — AI stories
    ("HackerNews AI", "https://hnrss.org/newest?q=AI+LLM+Claude+GPT&points=50"),
    # Reddit r/LocalLLaMA
    ("r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/.rss"),
    # Reddit r/ClaudeAI
    ("r/ClaudeAI", "https://www.reddit.com/r/ClaudeAI/.rss"),
    # The Batch (DeepLearning.AI newsletter)
    ("The Batch", "https://www.deeplearning.ai/the-batch/feed/"),
]


def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set) -> None:
    SEEN_FILE.write_text(json.dumps(list(seen), indent=2))


def entry_id(entry) -> str:
    key = getattr(entry, "id", None) or getattr(entry, "link", "") or entry.get("title", "")
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def translate(text: str) -> str:
    if not text:
        return text
    try:
        return GoogleTranslator(source="auto", target="ru").translate(text[:4500])
    except Exception:
        return text


def format_message(source: str, entry) -> str:
    title = getattr(entry, "title", "No title").strip()
    link = getattr(entry, "link", "")
    summary = getattr(entry, "summary", "")

    summary = re.sub(r"<[^>]+>", "", summary or "").strip()
    if len(summary) > 280:
        summary = summary[:277] + "..."

    title = translate(title)
    summary = translate(summary)

    lines = [f"📰 *{source}*", f"[{title}]({link})"]
    if summary:
        lines.append(f"\n_{summary}_")
    return "\n".join(lines)


def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    httpx.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }, timeout=10)


def fetch_feed(source: str, url: str) -> list[tuple[str, object]]:
    try:
        feed = feedparser.parse(url)
        return [(source, e) for e in feed.entries]
    except Exception as e:
        print(f"[{source}] fetch error: {e}")
        return []


def main():
    seen = load_seen()
    new_seen = set()
    to_send = []

    for source, url in FEEDS:
        entries = fetch_feed(source, url)
        for src, entry in entries:
            eid = entry_id(entry)
            if eid not in seen:
                to_send.append((src, entry, eid))
            new_seen.add(eid)

    # Keep seen set bounded (last 2000 ids)
    combined = (seen | new_seen)
    if len(combined) > 2000:
        combined = set(list(combined)[-2000:])

    print(f"Found {len(to_send)} new items")

    sent = 0
    for source, entry, eid in to_send:
        try:
            msg = format_message(source, entry)
            send_message(msg)
            seen.add(eid)
            sent += 1
        except Exception as e:
            print(f"[{source}] send error: {e}")

    save_seen(seen | new_seen)
    print(f"Sent {sent} messages, {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
