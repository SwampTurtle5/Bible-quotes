# Daily Bible Verse Discord Bot

Posts a random popular/inspirational Bible verse to a Discord channel
every day at 8 AM, via GitHub Actions — no server required. Verses don't
repeat until the entire ~200-verse list has been used once (then it
reshuffles and starts a fresh cycle).

## How it works

- `verses.py` — curated list of ~200 popular/inspirational verse references.
- `bot.py` — picks an unused reference, fetches the verse text from
  [bible-api.com](https://bible-api.com) (free, no API key), and posts
  it to your Discord webhook as an embed.
- `history.json` — tracks which references have already been posted.
  The GitHub Action commits this file back to the repo after every run,
  so the "no redos" state persists across runs.
- `.github/workflows/daily-verse.yml` — the cron schedule that runs
  `bot.py` automatically every day.

## Setup (5 minutes)

### 1. Create a Discord webhook
In Discord: **Server Settings → Integrations → Webhooks → New Webhook**.
Pick the channel you want verses posted in, then copy the Webhook URL.

### 2. Create the GitHub repo
Push these files to a new GitHub repo (public or private both work).

### 3. Add the webhook URL as a secret
In your repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `DISCORD_WEBHOOK_URL`
- Value: (paste the webhook URL from step 1)

That's it — the workflow already references `secrets.DISCORD_WEBHOOK_URL`,
so nothing else needs editing unless you want to change the time or verse list.

### 4. Test it manually
Go to the **Actions** tab → **Daily Bible Verse** → **Run workflow**.
This triggers it immediately so you can confirm it posts correctly,
without waiting for 8 AM.

## ⚠️ Timezone — read this

GitHub Actions cron schedules run in **UTC only**, and GitHub does not
adjust for daylight saving time. The workflow ships with:

```yaml
cron: "0 12 * * *"   # 12:00 UTC
```

| Your timezone | UTC offset | Cron for 8:00 AM local |
|---|---|---|
| US Eastern (EDT, summer)  | UTC-4 | `0 12 * * *` |
| US Eastern (EST, winter)  | UTC-5 | `0 13 * * *` |
| US Central (CDT, summer)  | UTC-5 | `0 13 * * *` |
| US Central (CST, winter)  | UTC-6 | `0 14 * * *` |

Florida (Eastern time) means you'll need to **manually flip between
`0 12 * * *` and `0 13 * * *` twice a year** when daylight saving
changes, since GitHub's free scheduler doesn't do this for you. Just
edit the `cron` line in `.github/workflows/daily-verse.yml` and push.

Also note: GitHub Actions cron is "best effort" — on the free tier,
runs can occasionally be delayed a few minutes during high load on
GitHub's infrastructure. It's very reliable in practice, just not
millisecond-precise.

## Customizing

- **Change translation**: edit `BIBLE_TRANSLATION: kjv` in the workflow
  file. Options include `kjv`, `web` (World English Bible), `bbe` (Bible
  in Basic English), `oeb-us`, and others bible-api.com supports.
- **Add/remove verses**: edit the `VERSES` list in `verses.py`. Use the
  format `"Book Chapter:Verse"` (e.g. `"Romans 8:28"`) or a range like
  `"Psalm 23:1-3"`.
- **Reset the "no redo" cycle early**: delete the contents of
  `history.json` (replace with `[]`) and commit/push.

## Running locally (optional, for testing)

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="your webhook url here"
python bot.py
```

## Files

```
bible-verse-bot/
├── bot.py                          # main script
├── verses.py                       # curated verse reference list
├── history.json                    # tracks used verses (auto-updated)
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        └── daily-verse.yml         # cron schedule
```
