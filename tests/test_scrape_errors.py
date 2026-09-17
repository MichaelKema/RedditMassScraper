import unittest
from unittest.mock import patch

import prawcore
import requests

from RedditMassScraper import Api


class ScrapeErrorTests(unittest.TestCase):
    @patch("RedditMassScraper.log")
    @patch("RedditMassScraper.reddit")
    def test_listing_errors_return_safe_messages_and_preserve_results(self, reddit, log):
        response = requests.Response()
        response.status_code = 404
        response.headers["location"] = "/subreddits/search"
        cases = [
            (prawcore.NotFound(response), "Check the spelling"),
            (prawcore.Redirect(response), "Check the spelling"),
            (prawcore.Forbidden(response), "denied access"),
            (prawcore.TooManyRequests(response), "rate limit"),
            (prawcore.RequestException(ValueError("secret"), (), {}), "connection"),
            (RuntimeError("secret"), "Could not scrape"),
        ]
        api = Api()
        previous = {"scrape_id": "previous"}
        api.last_scrape = previous
        for exception, message in cases:
            with self.subTest(exception=type(exception).__name__):
                # PRAW fetches lazily: reproduce a failure while iterating.
                def listing():
                    raise exception
                    yield
                reddit.subreddit.return_value.top.return_value = listing()
                result = api.scrape_subreddit("typo", 25, "all")
                self.assertFalse(result["ok"])
                self.assertIn(message, result["error"])
                self.assertNotIn("secret", result["error"])
                self.assertIs(api.last_scrape, previous)

    @patch("RedditMassScraper.log")
    @patch("RedditMassScraper.reddit")
    def test_success_still_returns_results(self, reddit, log):
        reddit.subreddit.return_value.top.return_value = []
        api = Api()
        result = api.scrape_subreddit("python", 25, "all")
        self.assertTrue(result["ok"])
        self.assertIs(api.last_scrape, result)
        reddit.subreddit.assert_called_once_with("python")


if __name__ == "__main__":
    unittest.main()
