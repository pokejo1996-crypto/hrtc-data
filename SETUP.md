# Setup Guide — Path 2 (GitHub-powered hybrid)

You'll create a GitHub account, copy this repo to your own account, and from then on a daily scrape happens automatically at 18:30 IST. Total time: **~10 minutes**, only the first time.

After this setup:
- Every day at 6:30 PM IST, GitHub fetches the Rubber Board page and saves today's prices to `data/prices.json`.
- Whenever you open `index.html`, it pulls the latest from GitHub and merges into your local data.
- Even if you don't open the app for a week, when you finally do, you'll see all the missed days.

---

## Step 1 — Create a GitHub account (one time)

If you don't have one already:

1. Go to **https://github.com**
2. Click **Sign up**.
3. Use your business email. Choose a username (something like `hrtc` or `tojo-hrtc` is fine — it'll appear in your URL).
4. Verify the email.

Done.

---

## Step 2 — Create a new repository

1. Click the **+** icon top-right → **New repository**.
2. Name it: `hrtc-data` (anything works, but this name is short).
3. Description: `Hindustan Rubber Trading - daily price data`.
4. Set it to **Private**. You don't want random people seeing your prices/transactions.
5. **Don't** tick "Add a README" — we'll bring our own files.
6. Click **Create repository**.

You'll land on a page that says "Quick setup". Leave it open — you'll need it.

---

## Step 3 — Upload the files

Easiest way: click **uploading an existing file** on that Quick setup page (it's a link in the page text).

Then drag-and-drop these 3 things from the `path2` folder I gave you:

1. The whole **`.github`** folder (contains the Action that runs daily)
2. The whole **`data`** folder (contains the seed prices.json)
3. The **`scrape.py`** file
4. The **`index.html`** file (the modified app)

(You can drag them all at once. GitHub keeps the folder structure.)

Scroll down, **Commit changes** button.

---

## Step 4 — Run it once manually to verify

1. Click the **Actions** tab at the top of your repo.
2. You'll see "Daily Rubber Board scrape" listed.
3. Click on it, then click **Run workflow** (button on the right) → **Run workflow**.
4. Wait ~30 seconds. Refresh. The run should turn green.
5. Click into the run → click the `scrape` job → see the log. You should see lines like:
   ```
   Fetching https://rubberboard.org.in/public...
   Got 47291 bytes of HTML
   Found 4 prices: {'RSS4': 240, 'RSS5': 236, 'ISNR20': 205, 'Latex': 159.55}
   Saved to data/prices.json
   Committed and pushed.
   ```
6. Go back to the **Code** tab. Open `data/prices.json` — you'll see today's prices in there.

If the log says "no prices parsed", the Rubber Board page format may have changed. Tell me and I'll update the regex.

---

## Step 5 — Connect your local HTML app to the GitHub data

1. On GitHub, navigate to `data/prices.json` in your repo.
2. Click the **Raw** button (top-right of the file viewer). You'll get a URL like:
   ```
   https://raw.githubusercontent.com/yourusername/hrtc-data/main/data/prices.json
   ```
3. Copy that URL.
4. **Now open your local `hrtc_app_pro.html`** (or `index.html` from this folder — they're now the same).
5. Go to **Settings** page.
6. Find the **"GitHub data source"** field at the top.
7. Paste your raw URL there.
8. Click **Save**.

Done. From now on, every time you open the app, it pulls the latest prices from your GitHub repo.

---

## What runs when

| Time | What happens | Where |
|------|--------------|-------|
| 18:30 IST every day | GitHub Action scrapes Rubber Board, commits to your repo | GitHub's servers (free) |
| Whenever you open the HTML | App fetches your prices.json from GitHub, merges any new days | Your browser |
| Saturday morning | You open the app → click "Generate AI analysis" → click "Send by email" | Your laptop |

GitHub gives you 2,000 minutes/month of free Action time. Each daily scrape uses ~0.5 minutes. You'll use ~15 minutes/month. Plenty of headroom.

---

## What if I want to give my staff access too?

The HTML file is yours alone — your data is on your browser. If you want staff to see the same prices:

**Cheapest way**: Send them the HTML file. Each person enters the same GitHub raw URL in their Settings. They each get the auto-updating prices, but their transactions are independent.

**Real multi-user (different transactions, real auth)**: that's the full Node.js + Supabase version. Different problem, different setup.

---

## Backup: this setup makes accidental data loss almost impossible

Three layers of safety:

1. **Daily prices** are committed to git history. Every day's commit is a backup.
2. **Your transactions** sit in browser localStorage. Use Settings → Export to download a JSON, save it to your cloud drive weekly.
3. **The HTML file itself** — keep a copy in your cloud drive too. If your laptop dies, you re-download from GitHub + restore your transactions JSON.

---

## If something doesn't work

| Symptom | Fix |
|---------|-----|
| Action fails on day one | Open it on GitHub Actions tab, click the failed run, read the log, send it to me |
| `data/prices.json` shows blank for all grades | Rubber Board changed their page. Open an Issue on your repo and I'll send a regex update |
| HTML app says "GitHub fetch failed" | Wrong URL in Settings, or your repo is private (check the URL works in incognito) |
| Action runs but no commit happens | Means there were no NEW prices that day (already fetched). Normal. |

---

## When you're ready to upgrade to the full Node.js version

Path 2 covers ~80% of what the full backend does. The 20% you'd gain by upgrading:
- Auto-send the weekly email/WhatsApp Saturday morning even with laptop closed
- News aggregation + AI summaries on a schedule (not just on-demand)
- Proper multi-user with logins
- International market prices auto-fetched

The Node.js project is in your `outputs/backend` folder. The deployment guide is in `DEPLOYMENT_GUIDE.md`. Path 2 doesn't conflict with it — you can run both at once if you want.
