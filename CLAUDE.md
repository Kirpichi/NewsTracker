# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Telegram channel bot that aggregates AI news from RSS feeds and posts them in Russian. Runs on GitHub Actions — no paid hosting.

## Running locally

```bash
pip install -r requirements.txt
TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... python bot.py
```

## Key files

- `bot.py` — fetches RSS feeds, filters by age, translates to Russian, posts to Telegram
- `seen.json` — deduplication store (committed to repo by the workflow after each run)
- `.github/workflows/news.yml` — cron schedule (07:00, 13:00, 19:00 UTC)

## Architecture

`feedparser` reads 9 RSS feeds → entries older than `MAX_AGE_HOURS` (25h) are dropped → new entry IDs (sha256[:16] of `entry.id` or `entry.link`) are checked against `seen.json` → remaining entries are translated via `deep-translator` (Google Translate, no API key needed) → posted to Telegram via Bot API → `seen.json` updated and committed by the workflow.

## Deployment

Secrets required in GitHub repo settings:
- `TELEGRAM_TOKEN` — from @BotFather
- `TELEGRAM_CHAT_ID` — channel username (`@channel`) or numeric ID

The workflow commits `seen.json` back after each run using `github-actions[bot]`.

## Adding/removing sources

Edit the `FEEDS` list in `bot.py` — each entry is `("Label", "rss_url")`.
