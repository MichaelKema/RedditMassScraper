# RedditScraper

A tiny desktop app to mass-download Reddit posts/comments to CSV (and optionally images/videos), powered by the official Reddit API.

> **Status:** alpha — expect rough edges and fast updates.

---

##  Features
- GUI (no terminal prompts) via **pywebview**
- Validate Reddit **Client ID/Secret** in-app
- **User** mode: posts + comments → CSV (+ media)
- **Subreddit** mode: top posts by `hour/day/week/month/year/all`
- Portable Windows **.exe** (no Python install needed)
- Live status log
- Optional “Check for updates” (GitHub Releases)

---

##  Download
Get the latest Windows `.exe` from **Releases**:  


> On some Windows 10 PCs you may need the **Microsoft Edge WebView2 Runtime** installed. Windows 11 usually has it already.

---

##  Reddit API credentials
You need a **Client ID** and **Client Secret** from Reddit (free).  
Guide: https://www.geeksforgeeks.org/how-to-get-client_id-and-client_secret-for-python-reddit-api-registration/#

You’ll enter these in the app’s first screen.

---

## How to use (quick)
1. Open the app.
2. Enter **Client ID**, **Client Secret**, **Reddit username** → **Check Credentials**.
3. Pick **User** or **Subreddit** mode.
4. Fill fields (username/subreddit, limit, time filter) → start.
5. Watch the **Status Log**.  
6. Output files are created next to the app:
   - `username.csv` and `username_comments.csv`
   - `<subreddit>_posts.csv`
   - Media in `username_images/` or `<subreddit>/`

---

## Run from source (dev)

Requirements: Python 3.10+ (Windows/macOS/Linux)

```bash
# 1) create & activate venv
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 2) install deps
pip install praw requests pywebview certifi

# 3) run
python RedditMassScraper.py
