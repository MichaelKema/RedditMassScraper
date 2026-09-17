import praw
import prawcore
import csv
import math
import os
import sys
import requests
import webview
from datetime import datetime, timezone
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
from pathlib import Path
from statistics import median
from threading import Lock
from time import monotonic
from uuid import uuid4
from ai_overview import generate_overview, OverviewError
import certifi, os
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()


APP_VERSION = "0.1.3-alpha"
RELEASE_API = "https://api.github.com/repos/MichaelKema/RedditMassScraper/releases"

def check_updates():
    try:
        r = requests.get(RELEASE_API, headers={"User-Agent": "RedditMassScraper"}, timeout=10)
        r.raise_for_status()
        data = r.json()[0]  # most recent release
        latest_version = data["tag_name"]
        latest_normalized = latest_version.removeprefix("v")
        current_normalized = APP_VERSION.removeprefix("v")
        exe_url = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                exe_url = asset["browser_download_url"]
                break

        if latest_normalized != current_normalized:
            log(f"⬆️ Update available: {latest_version} (you have {APP_VERSION})")
            log(f"Download here: {exe_url or data['html_url']}")
            return {"update": True, "latest": latest_version, "url": exe_url or data["html_url"]}
        else:
            log(f"✅ Up to date (v{APP_VERSION})")
            return {"update": False, "latest": latest_version}
    except Exception as e:
        log(f"❌ Update check failed: {e}")
        return {"update": False, "error": str(e)}


reddit = None


try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except Exception:
    pass

def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

def log(msg):
    try:
        webview.windows[0].evaluate_js(f"addLog({repr(msg)})")
    except:
        print(msg)  # fallback if no window is ready


def download_media(url, directory):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            filename = os.path.basename(urlparse(url).path)
            filepath = os.path.join(directory, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            log(f"Downloaded: {filename}")
        else:
            log(f"⚠️ Failed to download: {url}")
    except Exception as e:
        log(f"❌ Error: {e}")


def is_media_url(url):
    return url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4'))


def safe_filename(value):
    return "".join(char for char in value if char.isalnum() or char in ("-", "_", ".")).strip() or "scrape"


def normalize_limit(limit, default=25, maximum=1000):
    try:
        if isinstance(limit, float) and math.isnan(limit):
            return default
        parsed = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def build_post_record(submission):
    created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
    return {
        "Title": submission.title,
        "URL": submission.url,
        "Permalink": f"https://www.reddit.com{submission.permalink}",
        "Created": created.strftime("%Y-%m-%d %H:%M UTC"),
        "created_utc": submission.created_utc,
        "score": submission.score,
        "num_comments": submission.num_comments,
        "id": submission.id
    }


def build_comment_record(comment):
    return {
        "Comment ID": comment.id,
        "Comment URL": f"https://www.reddit.com{comment.permalink}",
        "Comment Body": comment.body.replace("\n", " "),
        "Subreddit": comment.subreddit.display_name,
        "Score": comment.score
    }


def increment_frequency(frequencies, created_utc):
    dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    iso_year, iso_week, _ = dt.isocalendar()
    keys = {
        "day": dt.strftime("%Y-%m-%d"),
        "week": f"{iso_year}-W{iso_week:02d}",
        "month": dt.strftime("%Y-%m")
    }

    for group, key in keys.items():
        frequencies[group][key] = frequencies[group].get(key, 0) + 1


def frequency_items(values):
    return [{"label": key, "count": values[key]} for key in sorted(values)]


def build_analytics(posts, scraped_comment_count=None):
    scores = [post["score"] for post in posts]
    comment_counts = [post["num_comments"] for post in posts]
    frequencies = {"day": {}, "week": {}, "month": {}}

    for post in posts:
        increment_frequency(frequencies, post["created_utc"])

    highest_post = max(posts, key=lambda post: post["score"], default=None)
    top_posts = sorted(posts, key=lambda post: post["score"], reverse=True)[:10]

    analytics = {
        "total_posts": len(posts),
        "total_comments": sum(comment_counts),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "median_score": median(scores) if scores else 0,
        "average_comments_per_post": round(sum(comment_counts) / len(comment_counts), 2) if comment_counts else 0,
        "highest_scoring_post": highest_post,
        "frequency": {
            "day": frequency_items(frequencies["day"]),
            "week": frequency_items(frequencies["week"]),
            "month": frequency_items(frequencies["month"])
        },
        "top_posts": top_posts
    }

    if scraped_comment_count is not None:
        analytics["scraped_user_comments"] = scraped_comment_count

    return analytics


def write_csv(path, rows):
    if not rows:
        return None

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


class Api:
    def __init__(self):
        self.last_scrape = None
        self._overview_lock = Lock()
        self._overview_cache = None
        self._overview_next_attempt = 0

    def generate_overview(self, scrape_id):
        # pywebview can dispatch simultaneous bridge calls on separate threads.
        if not self._overview_lock.acquire(blocking=False):
            return {"ok": False, "error": "An overview is already being generated. Please wait."}
        try:
            result = self.last_scrape
            if not result or result["scrape_id"] != scrape_id:
                return {"ok": False, "error": "Run a scrape and generate an overview for the current results."}
            if self._overview_cache and self._overview_cache["scrape_id"] == scrape_id:
                return dict(self._overview_cache)
            if monotonic() < self._overview_next_attempt:
                return {"ok": False, "error": "Please wait 30 seconds between overview requests."}
            self._overview_next_attempt = monotonic() + 30
            overview = generate_overview(result)
            if self.last_scrape is not result:
                return {"ok": False, "error": "Results changed. Generate an overview for the new scrape."}
            self._overview_cache = overview
            return dict(overview)
        except OverviewError as error:
            return {"ok": False, "error": str(error)}
        except Exception:
            return {"ok": False, "error": "The overview could not be generated. Try again later."}
        finally:
            self._overview_lock.release()

    def check_credentials(self, client_id, client_secret, agent_input):
        global reddit
        try:
            # sanitize: only accept real strings
            if not isinstance(client_id, str) or not client_id.strip():
                return {"ok": False, "error": "Missing client_id"}
            if not isinstance(client_secret, str) or not client_secret.strip():
                return {"ok": False, "error": "Missing client_secret"}
            if not isinstance(agent_input, str) or not agent_input.strip():
                return {"ok": False, "error": "Missing Reddit username"}

            user_agent = f"Extraction by: {agent_input.strip()}"
            auth = HTTPBasicAuth(client_id.strip(), client_secret.strip())
            headers = {"User-Agent": user_agent}
            data = {"grant_type": "client_credentials"}

            log("Checking credentials…")
            resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth, headers=headers, data=data, timeout=20
            )

            if resp.status_code == 200:
                reddit = praw.Reddit(
                    client_id=client_id.strip(),
                    client_secret=client_secret.strip(),
                    user_agent=user_agent,
                    check_for_updates=False,
                    comment_kind="t1",
                    message_kind="t4",
                    redditor_kind="t2",
                    submission_kind="t3",
                    subreddit_kind="t5",
                    trophy_kind="t6",
                    oauth_url="https://oauth.reddit.com",
                    reddit_url="https://www.reddit.com",
                    short_url="https://redd.it",
                    refresh_token=None,
                    validate_on_submit=True
                )
                log("✅ Credentials valid")
                return {"ok": True}
            else:
                msg = f"API returned {resp.status_code}: {getattr(resp, 'text', '')[:200]}"
                log("❌ " + msg)
                return {"ok": False, "error": msg}

        except Exception as e:
            log(f"❌ Exception during auth: {e}")
            return {"ok": False, "error": str(e)}


    # --- Scrape a user ---
    def scrape_user(self, username, limit):
        if reddit is None:
            log("❌ Please check credentials first.")
            return {"ok": False, "error": "Please check credentials first."}

        limit = normalize_limit(limit)
        username = (username or "").strip()
        if not username:
            log("❌ Missing username.")
            return {"ok": False, "error": "Missing username"}

        redditor = reddit.redditor(username)
        posts = []

        for i, submission in enumerate(redditor.submissions.new(limit=limit), start=1):
            log(f"Scraping u/{username}: {i}/{limit}")
            posts.append(build_post_record(submission))

        if posts:
            log(f"✅ Finished scraping u/{username} ({len(posts)} posts).")
        else:
            log(f"⚠️ No posts found for u/{username}")

        # Scrape comments
        comments = []
        for comment in redditor.comments.new(limit=limit):
            comments.append(build_comment_record(comment))
        log(f"✅ Collected {len(comments)} comments.")

        result = {
            "ok": True,
            "kind": "user",
            "scrape_id": uuid4().hex,
            "target": username,
            "posts": posts,
            "comments": comments,
            "analytics": build_analytics(posts, len(comments))
        }
        self.last_scrape = result
        return result

    # --- Scrape a subreddit ---
    def scrape_subreddit(self, subreddit_name, limit, time_filter):
        try:
            return self._scrape_subreddit(subreddit_name, limit, time_filter)
        except prawcore.NotFound:
            message = "Subreddit not found. Check the spelling and try again."
        except prawcore.Redirect:
            message = "Reddit could not open this subreddit. Check the spelling and that it is accessible."
        except prawcore.Forbidden:
            message = "Reddit denied access to this subreddit. It may be private or restricted."
        except prawcore.TooManyRequests:
            message = "Reddit's rate limit was reached. Please try again later."
        except (prawcore.RequestException, requests.RequestException):
            message = "Could not connect to Reddit. Check your connection and try again."
        except Exception:
            # Never send raw API exceptions or request details across the bridge.
            message = "Could not scrape this subreddit. Check your Reddit credentials and try again."
        return {"ok": False, "error": message}

    def _scrape_subreddit(self, subreddit_name, limit, time_filter):
        if reddit is None:
            log("❌ Please check credentials first.")
            return {"ok": False, "error": "Please check credentials first."}

        limit = normalize_limit(limit)
        subreddit_name = (subreddit_name or "").strip()
        if not subreddit_name:
            log("❌ Missing subreddit.")
            return {"ok": False, "error": "Missing subreddit"}

        subreddit = reddit.subreddit(subreddit_name)
        posts = []

        for i, submission in enumerate(subreddit.top(limit=limit, time_filter=time_filter), start=1):
            log(f"Scraping r/{subreddit_name}: {i}/{limit}")
            posts.append(build_post_record(submission))

        if posts:
            log(f"✅ Finished scraping r/{subreddit_name} ({len(posts)} posts).")
        else:
            log(f"⚠️ No posts found in r/{subreddit_name}")

        result = {
            "ok": True,
            "kind": "subreddit",
            "scrape_id": uuid4().hex,
            "time_filter": time_filter,
            "target": subreddit_name,
            "posts": posts,
            "comments": [],
            "analytics": build_analytics(posts)
        }
        self.last_scrape = result
        return result

    def download_last_scrape(self):
        if not self.last_scrape:
            log("❌ Nothing to download yet. Run a scrape first.")
            return {"ok": False, "error": "Nothing to download yet. Run a scrape first."}

        kind = self.last_scrape["kind"]
        target = safe_filename(self.last_scrape["target"])
        posts = self.last_scrape.get("posts", [])
        comments = self.last_scrape.get("comments", [])
        outputs = []

        if kind == "user":
            post_csv = write_csv(f"{target}.csv", posts)
            comment_csv = write_csv(f"{target}_comments.csv", comments)
            media_directory = os.path.join(os.getcwd(), f"{target}_images")
            if post_csv:
                outputs.append(post_csv)
            if comment_csv:
                outputs.append(comment_csv)
        else:
            post_csv = write_csv(f"{target}_posts.csv", posts)
            media_directory = os.path.join(os.getcwd(), target)
            if post_csv:
                outputs.append(post_csv)

        media_count = 0
        media_posts = [post for post in posts if is_media_url(post["URL"])]
        if media_posts:
            os.makedirs(media_directory, exist_ok=True)
            for post in media_posts:
                download_media(post["URL"], media_directory)
                media_count += 1
            outputs.append(media_directory)

        log(f"✅ Download complete. Created: {', '.join(outputs) if outputs else 'no files'}")
        return {"ok": True, "outputs": outputs, "media_count": media_count}



if __name__ == "__main__":
    api = Api()
    index_url = Path(resource_path("index.html")).resolve().as_uri()  # file:///...
    webview.create_window("RedditMassScraper", index_url, js_api=api)
    webview.start(gui='edgechromium')  # just once; remove the other start() 
