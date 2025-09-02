import praw
import csv
import os
import sys
import requests
import webview
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
from pathlib import Path
import certifi, os
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()


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


class Api:
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
            return False

        redditor = reddit.redditor(username)
        posts = []
        image_directory = os.path.join(os.getcwd(), f"{username}_images")
        os.makedirs(image_directory, exist_ok=True)

        for i, submission in enumerate(redditor.submissions.new(limit=limit), start=1):
            log(f"Scraping u/{username}: {i}/{limit}")
            posts.append({
                "Title": submission.title,
                "URL": submission.url,
                "created_utc": submission.created_utc,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "id": submission.id
            })
            if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4')):
                download_media(submission.url, image_directory)

        if posts:
            csv_file = f"{username}.csv"
            with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=posts[0].keys())
                writer.writeheader()
                writer.writerows(posts)
            log(f"✅ Finished scraping u/{username} ({len(posts)} posts). Saved to {csv_file}")
        else:
            log(f"⚠️ No posts found for u/{username}")

        # Scrape comments
        output_file = f"{username}_comments.csv"
        with open(output_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Comment ID", "Comment URL", "Comment Body", "Subreddit", "Score"])
            for comment in redditor.comments.new(limit=limit):
                writer.writerow([
                    comment.id,
                    f"https://www.reddit.com{comment.permalink}",
                    comment.body.replace("\n", " "),
                    comment.subreddit.display_name,
                    comment.score
                ])
        log(f"✅ Comments saved to {output_file}")
        return True

    # --- Scrape a subreddit ---
    def scrape_subreddit(self, subreddit_name, limit, time_filter):
        if reddit is None:
            log("❌ Please check credentials first.")
            return False

        subreddit = reddit.subreddit(subreddit_name)
        directory = os.path.join(os.getcwd(), subreddit_name)
        os.makedirs(directory, exist_ok=True)
        posts = []

        for i, submission in enumerate(subreddit.top(limit=limit, time_filter=time_filter), start=1):
            log(f"Scraping r/{subreddit_name}: {i}/{limit}")
            posts.append({
                "Title": submission.title,
                "URL": submission.url,
                "created_utc": submission.created_utc,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "id": submission.id
            })
            if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4')):
                download_media(submission.url, directory)

        if posts:
            csv_file = f"{subreddit_name}_posts.csv"
            with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=posts[0].keys())
                writer.writeheader()
                writer.writerows(posts)
            log(f"✅ Finished scraping r/{subreddit_name} ({len(posts)} posts). Saved to {csv_file}")
        else:
            log(f"⚠️ No posts found in r/{subreddit_name}")
        return True



if __name__ == "__main__":
    api = Api()
    index_url = Path(resource_path("index.html")).resolve().as_uri()  # file:///...
    webview.create_window("RedditMassScraper", index_url, js_api=api)
    webview.start(gui='edgechromium')  # just once; remove the other start() 
