# Telegram Channel Scheduler Bot

This repository automatically sends pre-written messages to a Telegram channel at scheduled times. You populate a `messages.json` file with your message text and the exact datetime you want each one sent, then GitHub Actions runs a check on your chosen interval and delivers any message whose scheduled time falls within that window.

The main branch intentionally has no cron schedule and will not send anything. All active scheduling lives on dedicated implementation branches, each backed by its own GitHub environment with isolated secrets.

---

## Overview

Each deployment follows this structure:

- A branch named `implementation/[name]` holds your messages and workflow config
- A GitHub environment named to match sits at the repository level and stores the credentials
- The workflow on that branch references the environment and runs on your chosen cron schedule

This keeps multiple independent schedules (different bots, channels, or campaigns) cleanly separated without any shared state.

---

## Prerequisites

- A GitHub account with this repository forked to your own account
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

## Step 3 — Create an Implementation Branch

Create a new branch from main using the naming convention `implementation/[name]`, where `[name]` describes this particular deployment (e.g. `implementation/product-launch` or `implementation/weekly-digest`):

```bash
git checkout -b implementation/my-campaign
git push -u origin implementation/my-campaign
```

All further changes in this guide are made on this branch.

---

## Step 4 — Create a Matching GitHub Environment

1. In your GitHub repository, go to **Settings → Environments**.
2. Click **New environment** and give it the same name you used for the branch suffix, e.g. `my-campaign`.
3. Inside the environment, click **Add secret** and add the following two secrets:

| Secret name            | Value                                      |
|------------------------|--------------------------------------------|
| `TELEGRAM_BOT_TOKEN`   | The token from BotFather (Step 1)          |
| `TELEGRAM_CHANNEL_ID`  | Your channel's username or numeric ID (Step 2) |

These values are scoped to this environment only and will never appear in logs.

---

## Step 5 — Update the Workflow Config

On your implementation branch, open `.github/workflows/scheduler.yml` and make two changes:

**1. Set the environment name** to match what you created in Step 4:

```yaml
jobs:
  send:
    runs-on: ubuntu-latest
    environment: my-campaign   # ← your environment name here
```

**2. Add a cron schedule** with the interval you want. The example below checks every 5 minutes:

```yaml
on:
  schedule:
    - cron: "*/5 * * * *"   # ← your desired interval here
  workflow_dispatch:
    inputs:
      window_minutes:
        description: "Delivery window in minutes (default: 5)"
        required: false
        default: "5"
```

**3. (Optional) Set the delivery window** by adding a `WINDOW_MINUTES` variable to your GitHub environment (Settings → Environments → your environment → Variables). If omitted, the window defaults to ±5 minutes. You can also override it per manual run via the `window_minutes` input in the Actions UI.

The full file should look like this after your edits:

```yaml
name: Send Scheduled Messages

on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:
    inputs:
      window_minutes:
        description: "Delivery window in minutes (default: 5)"
        required: false
        default: "5"

jobs:
  send:
    runs-on: ubuntu-latest
    environment: my-campaign
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests

      - name: Send scheduled messages
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHANNEL_ID: ${{ secrets.TELEGRAM_CHANNEL_ID }}
          WINDOW_MINUTES: ${{ inputs.window_minutes || vars.WINDOW_MINUTES || '5' }}
        run: python send_message.py
```

Commit and push this change to your implementation branch.

---

## Step 6 — Populate `messages.json`

Edit `messages.json` on your implementation branch. Each entry needs two fields:

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

Commit and push the file to your implementation branch. The scheduler will start picking up entries automatically once the workflow runs.

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
3. Use the branch selector to pick your implementation branch.
4. Click **Run workflow → Run workflow**.

This is useful for verifying that your environment secrets are configured correctly. To actually trigger a message send during a manual test, temporarily add an entry to `messages.json` with a datetime within the delivery window of now (in UTC), commit it, then run the workflow. You can also set the `window_minutes` input when triggering manually to widen the window for testing.

---

## The Delivery Window

When the workflow fires, it looks for messages whose scheduled datetime falls within a window of **±N minutes** around the current UTC time. The window defaults to **5 minutes** and can be configured in three ways, in priority order:

1. **`workflow_dispatch` input** — set `window_minutes` when triggering manually from the Actions UI
2. **GitHub Actions variable** — add a `WINDOW_MINUTES` variable to your environment (Settings → Environments → your environment → Variables) for scheduled runs
3. **Default** — falls back to `5` if neither is set

Example with the default window:

- A message scheduled for `10:00` will be caught if the workflow runs at any time between `09:55` and `10:05`.

**Avoid scheduling two messages within `N` minutes of each other** (where `N` is your window size). If two entries fall in the same window, both will be sent. Space your messages at least `2×N` minutes apart to be safe.

If you set a longer cron interval (e.g. every 15 minutes), consider increasing `WINDOW_MINUTES` to match, or ensure messages are spaced far enough apart to avoid gaps in coverage.

---

## Limitations

- **No retry logic.** If the Telegram API is unreachable when the workflow runs, the message will not be sent. The next run will only resend it if its scheduled time is still within the ±5 minute window.
- **No duplicate prevention.** The bot does not record which messages have been sent. If the workflow fires twice in quick succession (which GitHub occasionally does), a message could be delivered twice. This is rare in practice.
- **GitHub Actions cron is not exact.** Scheduled workflows can be delayed by several minutes during periods of high load on GitHub's infrastructure. Critical time-sensitive messages should not rely on this bot.
- **Plain text only.** The bot uses Telegram's default parse mode, so special characters are sent as-is and no formatting is applied.
