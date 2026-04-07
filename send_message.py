import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests


def load_messages(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_message(token: str, channel_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={"chat_id": channel_id, "text": text}, timeout=10)
    response.raise_for_status()


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not token or not channel_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set.", file=sys.stderr)
        return 1

    try:
        messages = load_messages("messages.json")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not load messages.json: {e}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    window_minutes = int(os.environ.get("WINDOW_MINUTES", "5"))
    window = timedelta(minutes=window_minutes)
    sent_count = 0

    for entry in messages:
        try:
            scheduled = datetime.fromisoformat(entry["datetime"])
        except (KeyError, ValueError) as e:
            print(f"WARNING: Skipping invalid entry ({e}): {entry}", file=sys.stderr)
            continue

        # Normalize to UTC for comparison
        scheduled_utc = scheduled.astimezone(timezone.utc)

        if abs(now - scheduled_utc) <= window:
            preview = entry["message"][:40]
            try:
                send_message(token, channel_id, entry["message"])
                print(f"SENT [{scheduled}] {preview!r}")
                sent_count += 1
            except requests.RequestException as e:
                print(f"ERROR: Failed to send message scheduled at {scheduled}: {e}", file=sys.stderr)
                return 1

    if sent_count == 0:
        print(f"No messages scheduled within \u00b15 min of {now.strftime('%Y-%m-%dT%H:%M:%SZ')}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
