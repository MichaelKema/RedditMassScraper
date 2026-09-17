import unittest

from scripts.prepare_release import prepare_version


class ReleaseVersionTests(unittest.TestCase):
    def test_main_builds_have_unique_versions_matching_executable(self):
        source = 'APP_VERSION = "0.1.3-alpha"\nOTHER = "unchanged"\n'
        for number in ("12", "13"):
            updated, tag = prepare_version(source, "", "branch", "main", number)
            self.assertEqual(tag, f"v0.1.3-alpha.build.{number}")
            self.assertIn(f'APP_VERSION = "{tag[1:]}"', updated)
            self.assertIn('OTHER = "unchanged"', updated)

    def test_tag_push_and_manual_tag_are_preserved(self):
        source = 'APP_VERSION = "0.1.3-alpha"\n'
        for requested, kind, ref in [("", "tag", "v0.2.0"), ("v0.2.0", "branch", "main")]:
            updated, tag = prepare_version(source, requested, kind, ref, "12")
            self.assertEqual(tag, "v0.2.0")
            self.assertEqual(updated, 'APP_VERSION = "0.2.0"\n')

    def test_release_metadata_rejects_invalid_input(self):
        source = 'APP_VERSION = "0.1.3-alpha"\n'
        for tag in ("main", "vbad", 'v0.1.3\ncommit=wrong', 'v0.1.3"'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                prepare_version(source, tag, "branch", "main", "12")
        with self.assertRaises(ValueError):
            prepare_version(source, "", "branch", "main", "invalid")
        with self.assertRaises(ValueError):
            prepare_version("", "", "branch", "main", "12")


if __name__ == "__main__":
    unittest.main()
