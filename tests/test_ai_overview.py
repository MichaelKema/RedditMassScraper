import json
from io import StringIO
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import requests

import ai_overview as ai
from RedditMassScraper import Api


FAKE_KEY = "test-only-not-a-real-credential"


def scrape(count=1, comments=1):
    return {
        "scrape_id": "scrape-1", "kind": "user", "target": "private-user",
        "posts": [{"Title": f"Post {i}", "score": i, "num_comments": 2,
                   "Created": "2026-09-17 00:00 UTC", "URL": "https://example.com",
                   "secret_extra_field": FAKE_KEY} for i in range(count)],
        "comments": [{"Comment Body": "Useful comment", "Score": 3} for _ in range(comments)],
    }


def response_data(text="A useful overview."):
    return {"status": "completed", "output": [
        {"type": "reasoning", "summary": []},
        {"type": "message", "content": [{"type": "output_text", "text": text}]}]}


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"API_KEY": FAKE_KEY})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.session_patch = patch("ai_overview.requests.Session")
        self.session_class = self.session_patch.start()
        self.addCleanup(self.session_patch.stop)
        self.session = self.session_class.return_value.__enter__.return_value
        self.response = self.session.post.return_value.__enter__.return_value
        self.response.status_code = 200
        self.response.json.return_value = response_data()

    def test_secure_request_and_response(self):
        result = ai.generate_overview(scrape())
        args, kw = self.session.post.call_args
        self.assertEqual(args, ("https://api.openai.com/v1/responses",))
        self.assertFalse(self.session.trust_env)
        self.assertFalse(kw["allow_redirects"])
        self.assertEqual(kw["verify"], ai.certifi.where())
        self.assertEqual(kw["timeout"], (10, 90))
        self.assertEqual(kw["headers"], {"Authorization": f"Bearer {FAKE_KEY}"})
        self.assertEqual(kw["json"]["model"], "gpt-5-nano")
        self.assertFalse(kw["json"]["store"])
        self.assertEqual(kw["json"]["max_output_tokens"], 4000)
        self.assertNotIn(FAKE_KEY, json.dumps(kw["json"]))
        self.assertNotIn("private-user", kw["json"]["input"])
        self.assertNotIn("https://example.com", kw["json"]["input"])
        self.assertEqual(result["overview"], "A useful overview.")

    def test_missing_key_empty_results_and_bad_key_do_not_call_api(self):
        with patch.dict(os.environ, {"API_KEY": ""}):
            with self.assertRaisesRegex(ai.OverviewError, "Set API_KEY"):
                ai.generate_overview(scrape())
        with self.assertRaisesRegex(ai.OverviewError, "No posts or comments"):
            ai.generate_overview(scrape(0, 0))
        with patch.dict(os.environ, {"API_KEY": "bad\nheader"}):
            with self.assertRaisesRegex(ai.OverviewError, "invalid format"):
                ai.generate_overview(scrape())
        self.session.post.assert_not_called()

    def test_dotenv_explicit_path_no_interpolation_and_environment_precedence(self):
        parse_dotenv = ai.dotenv_values
        def read_fixture(path, interpolate):
            self.assertEqual(path, Path(ai.__file__).resolve().parent / ".env")
            return parse_dotenv(stream=StringIO("API_KEY=literal-${OTHER}\n"), interpolate=interpolate)
        with patch("ai_overview.dotenv_values", side_effect=read_fixture) as reader:
            self.assertEqual(ai.read_api_key(), FAKE_KEY)
            reader.assert_not_called()
            with patch.dict(os.environ, {"OTHER": "should-not-expand"}, clear=True):
                self.assertEqual(ai.read_api_key(), "literal-${OTHER}")
                self.assertNotIn("API_KEY", os.environ)
            reader.assert_called_once()

    def test_sampling_bounds_and_redaction(self):
        data = scrape(1000, 1000)
        for post in data["posts"]:
            post["Title"] = FAKE_KEY + "x" * 2000
        for comment in data["comments"]:
            comment["Comment Body"] = "x" * 10000
        encoded, coverage = ai.build_input(data, FAKE_KEY)
        self.assertLessEqual(len(encoded), ai.MAX_INPUT_CHARS)
        self.assertNotIn(FAKE_KEY, encoded)
        self.assertEqual(coverage["sampled_posts"], 100)
        self.assertEqual(coverage["sampled_comments"], 100)
        payload = json.loads(encoded)
        self.assertEqual(payload["statistics"]["total_posts"], 1000)
        self.assertEqual(payload["posts"][0]["score"], 0)
        self.assertEqual(payload["posts"][-1]["score"], 999)

    def test_error_bodies_and_exceptions_never_escape(self):
        self.response.text = FAKE_KEY
        for code in (302, 400, 401, 403, 429, 500):
            with self.subTest(code=code):
                self.response.status_code = code
                with self.assertRaises(ai.OverviewError) as caught:
                    ai.generate_overview(scrape())
                self.assertNotIn(FAKE_KEY, str(caught.exception))
        for error in (requests.Timeout(FAKE_KEY), requests.ConnectionError(FAKE_KEY), ValueError(FAKE_KEY)):
            self.session.post.side_effect = error
            with self.assertRaises(ai.OverviewError) as caught:
                ai.generate_overview(scrape())
            self.assertNotIn(FAKE_KEY, str(caught.exception))

    def test_oversized_metadata_fails_without_looping_or_calling_api(self):
        data = scrape()
        data["time_filter"] = "x" * ai.MAX_INPUT_CHARS
        with self.assertRaisesRegex(ai.OverviewError, "input limit"):
            ai.generate_overview(data)
        self.session.post.assert_not_called()

    def test_incomplete_refusal_and_malformed_outputs(self):
        for data in ({"status": "incomplete"}, {"status": "completed", "output": []},
                     {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
                     [], {"status": "completed", "output": None}):
            self.response.json.return_value = data
            with self.assertRaises(ai.OverviewError):
                ai.generate_overview(scrape())

    def test_output_redaction_and_comments_only_scrape(self):
        self.response.json.return_value = response_data("Secret: " + FAKE_KEY)
        result = ai.generate_overview(scrape(0, 3))
        self.assertNotIn(FAKE_KEY, result["overview"])
        self.assertEqual(result["coverage"]["sampled_comments"], 3)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.api = Api()
        self.api.last_scrape = scrape()

    @patch("RedditMassScraper.generate_overview")
    def test_cache_and_current_result_validation(self, generate):
        generate.return_value = {"ok": True, "scrape_id": "scrape-1", "overview": "Summary"}
        self.assertFalse(self.api.generate_overview("wrong-id")["ok"])
        first = self.api.generate_overview("scrape-1")
        second = self.api.generate_overview("scrape-1")
        self.assertEqual(first, second)
        generate.assert_called_once()

    @patch("RedditMassScraper.generate_overview")
    def test_parallel_requests_and_cooldown(self, generate):
        self.api._overview_lock.acquire()
        self.assertFalse(self.api.generate_overview("scrape-1")["ok"])
        self.api._overview_lock.release()
        generate.side_effect = ai.OverviewError("Safe failure")
        self.assertEqual(self.api.generate_overview("scrape-1")["error"], "Safe failure")
        self.assertIn("30 seconds", self.api.generate_overview("scrape-1")["error"])
        generate.assert_called_once()

    @patch("RedditMassScraper.generate_overview")
    def test_scrape_replaced_while_generating(self, generate):
        def replace(_):
            self.api.last_scrape = {**scrape(), "scrape_id": "scrape-2"}
            return {"ok": True, "scrape_id": "scrape-1"}
        generate.side_effect = replace
        self.assertIn("Results changed", self.api.generate_overview("scrape-1")["error"])
        self.assertIsNone(self.api._overview_cache)

    @patch("RedditMassScraper.generate_overview", side_effect=RuntimeError(FAKE_KEY))
    def test_unexpected_error_is_sanitized_and_lock_released(self, generate):
        self.assertNotIn(FAKE_KEY, str(self.api.generate_overview("scrape-1")))
        self.assertFalse(self.api._overview_lock.locked())


if __name__ == "__main__":
    unittest.main()
