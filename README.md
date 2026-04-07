# Telegram Channel Scheduler Bot

This repository automatically sends pre-written messages to a Telegram channel at scheduled times. You populate a `messages.json` file with your message text and the exact datetime you want each one sent, then GitHub Actions runs a check every 5 minutes and delivers any message whose scheduled time falls within that window. There is no web interface, no database, and nothing to install on your own computer.

---

## Prerequisites

- A GitHub account with this repository forked or cloned to your own account
- A Telegram account
- A Telegram channel where you are an administrator

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**.
2. Send the command `/newbot`.
3. Follow the prompts: choose a display name and a username (the username must end in `bot`, e.g. `my_scheduler_bot`).
4. BotFather will reply with a **token** that looks like `123456789:ABCDefGhIJKlmNoPQRstuVWXyz`. Copy it — you will need it in Step 3.

---

## Step 2 — Add the Bot to Your Channel and Get the Channel ID

1. Go to your Telegram channel settings and add your new bot as an **administrator** with permission to post messages.
2. To find the channel ID:
   - **Public channels**: The channel ID is its username prefixed with `@`, e.g. `@mychannel`. Alternatively, forward any message from the channel to [@username_to_id_bot](https://t.me/username_to_id_bot) to get the numeric ID. Public channel numeric IDs start with `-100`, e.g. `-1001234567890`.
   - **Private channels**: Forward a message from the channel to [@username_to_id_bot](https://t.me/username_to_id_bot). The numeric ID shown (starting with `-100`) is the one to use.
3. Use either `@channelusername` or the full numeric ID (e.g. `-1001234567890`) as your channel ID.

> **Note on the `-100` prefix:** Telegram supergroups and channels have IDs that begin with `-100` when represented numerically. If a tool shows you a shorter number without this prefix, prepend `-100` to form the full ID.

---

## Step 3 — Add Secrets to GitHub Actions

1. In your GitHub repository, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret** and add the following two secrets:

| Secret name            | Value                                      |
|------------------------|--------------------------------------------|
| `TELEGRAM_BOT_TOKEN`   | The token from BotFather (Step 1)          |
| `TELEGRAM_CHANNEL_ID`  | Your channel's username or numeric ID (Step 2) |

These values are encrypted and will never appear in logs.

---

## Step 4 — Populate `messages.json`

Edit `messages.json` in the root of the repository. Each entry needs two fields:

```json
[
  {
    "datetime": "2026-06-01T09:00:00+03:00",
    "message": "Your message text here."
  },
  {
    "datetime": "2026-06-05T18:00:00+00:00",
    "message": "Another message, scheduled in UTC this time."
  }
]
```

- **`datetime`** — ISO 8601 format with a timezone offset. See the section below for details.
- **`message`** — Plain text. No HTML, no Markdown.

Commit and push the file to the repository. The scheduler will start picking up entries automatically.

---

## Timezone Handling

Every `datetime` value **must** include a timezone offset such as `+03:00` or `-05:00` or `+00:00`. The bot converts all times to UTC internally before comparing them to the current time, so you can freely mix offsets across entries.

Examples:

| Local time you want     | How to write it                  |
|-------------------------|----------------------------------|
| 9 AM Moscow (UTC+3)     | `2026-06-01T09:00:00+03:00`      |
| 9 AM New York (UTC-4)   | `2026-06-01T09:00:00-04:00`      |
| 9 AM UTC                | `2026-06-01T09:00:00+00:00`      |

If you omit the offset, the entry will be skipped with a warning.

---

## Testing Manually with `workflow_dispatch`

You can trigger the workflow at any time without waiting for the cron schedule:

1. Go to the **Actions** tab in your repository.
2. Select **Send Scheduled Messages** from the left sidebar.
3. Click **Run workflow → Run workflow**.

This is useful for verifying that your secrets are configured correctly. To actually trigger a message send during a manual test, temporarily add an entry to `messages.json` with a datetime within ±5 minutes of now (in UTC), commit it, then run the workflow.

---

## The ±5 Minute Delivery Window

The workflow runs every 5 minutes. When it fires, it looks for messages whose scheduled datetime is within **5 minutes before or after** the current UTC time. This means:

- A message scheduled for `10:00` will be caught if the workflow runs at any time between `09:55` and `10:05`.
- **Avoid scheduling two messages within 5 minutes of each other.** If two entries fall in the same ±5 minute window, both will be sent. Space your messages at least 10 minutes apart to be safe.

---

## Limitations

- **No retry logic.** If the Telegram API is unreachable when the workflow runs, the message will not be sent. The next run will only resend it if its scheduled time is still within the ±5 minute window.
- **No duplicate prevention.** The bot does not record which messages have been sent. If the workflow fires twice in quick succession (which GitHub occasionally does), a message could be delivered twice. This is rare in practice.
- **GitHub Actions cron is not exact.** The `*/5 * * * *` schedule means GitHub will *attempt* to run every 5 minutes, but actual execution can be delayed by several minutes during periods of high load. Critical time-sensitive messages should not rely on this bot.
- **Plain text only.** The bot uses Telegram's default parse mode, so special characters are sent as-is and no formatting is applied.
