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
- Optional GPT-5 nano overview of scraped results
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

## Automatic releases

Commit and push your changes to `main`. The **Build and release Windows app**
workflow runs the backend and UI tests, builds `RedditMassScraper.exe`, and
publishes a new release marked **Latest** with generated release notes. If tests
or the build fail, it does not publish a release; check the repository's
**Actions** tab for the failure.

Automatic versions combine `APP_VERSION` with the workflow run number, for
example `v0.1.3-alpha.build.12`. The executable is stamped with that same version
in the CI checkout, without making a commit back to your repository. Each new
push gets its own release; previous releases remain available. These are public
alpha builds, marked as regular GitHub releases so they appear as **Latest**.

You can also select **Actions → Build and release Windows app → Run workflow**
on `main`. Leave the tag blank for an automatic version. For a manually numbered
release, push a new version tag such as `v0.2.0`, or supply an existing version
tag when running the workflow. Normally, just pushing to `main` is enough;
also pushing a tag will trigger a second release build.

The workflow uses GitHub's built-in token with `contents: write`; no personal
access token, Reddit credentials, or OpenAI API key is needed. `.env` is not
included in the executable. Users provide their own keys locally.

Releases are created using the
[GitHub release action](https://github.com/softprops/action-gh-release).

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
pip install -r requirements.txt

# 3) run
python RedditMassScraper.py
```

## AI overview

After a scrape, click **Generate summary** in Analytics. The app uses
[`gpt-5-nano`](https://developers.openai.com/api/docs/models/gpt-5-nano) to describe
themes, engagement, notable findings, and limitations. This is optional and uses
your OpenAI API billing. Scraping and downloading work without an OpenAI key.

The Python backend reads your existing **API_KEY** environment variable. If that
variable is absent, it reads `API_KEY` from `.env` beside `RedditMassScraper.py`
(or beside the packaged executable). Restart the app after changing an inherited
environment variable. `.env.example` contains an empty template; enter the key
locally, never in JavaScript, source code, screenshots, or issue reports.

- The key stays in Python and is sent only in the HTTPS Authorization header to
  the fixed OpenAI API endpoint. It is not passed to the UI, prompts, CSV files,
  or app logs. Raw API errors are replaced with safe messages.
- TLS verification is required; redirects, implicit environment proxies, and
  `.netrc` authentication are disabled for OpenAI requests.
- `.env` and `.env.*` are ignored by Git (except the empty example). Build scripts
  do not bundle them. Keep the local file private and never distribute it with
  an executable. If a key was previously committed or shared, rotate it;
  ignoring a file does not remove it from Git history.
- Only clicking **Generate summary** sends scrape data to OpenAI: full-result
  counts and score statistics, plus at most 100 evenly spaced post titles and
  100 user comments. Text is shortened to fit a 60,000-character input cap.
  Usernames, URLs, and IDs are omitted as fields, but scraped text itself can
  still contain personal information. Post bodies and subreddit comment bodies
  are not collected or summarized.
- Responses use `store: false`. This disables response storage for later API
  retrieval; it does not guarantee zero retention under all OpenAI data policies.
  See [OpenAI data controls](https://platform.openai.com/docs/guides/your-data).
- Output is capped at 4,000 tokens including reasoning, with a connection/read
  timeout and no automatic retries. One request can run at a time, attempts are
  spaced by 30 seconds, and a successful overview is cached for the current
  scrape in memory. No overview files are written automatically.
- Scraped text is treated as untrusted input. The model has no tools or access
  to credentials. Its output is displayed as plain text and may contain mistakes.

Run offline checks with `python -m unittest discover -s tests` and
`node tests/test_overview_ui.js`.
