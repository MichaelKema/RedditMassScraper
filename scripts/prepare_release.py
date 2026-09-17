"""Stamp the CI checkout with the release version; no commits or secrets needed."""

import os
from pathlib import Path
import re
import subprocess


VERSION_LINE = re.compile(r'^APP_VERSION = "([^"]+)"$', re.MULTILINE)
VERSION = re.compile(r"v?\d+\.\d+\.\d+(?:-[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)?")


def prepare_version(source, requested_tag, ref_type, ref_name, run_number):
    match = VERSION_LINE.search(source)
    if not match:
        raise ValueError("APP_VERSION is missing")
    tag = requested_tag or (ref_name if ref_type == "tag" else "")
    if tag:
        if not tag.startswith("v") or not VERSION.fullmatch(tag):
            raise ValueError("Release tags must be versions such as v0.1.3-alpha")
        version = tag[1:]
    else:
        base = match[1]
        if not VERSION.fullmatch(base) or not run_number.isdigit():
            raise ValueError("Invalid base version or workflow run number")
        separator = "." if "-" in base else "-"
        version = f"{base}{separator}build.{run_number}"
        tag = f"v{version}"
    return VERSION_LINE.sub(lambda _: f'APP_VERSION = "{version}"', source, count=1), tag


def main():
    app = Path("RedditMassScraper.py")
    updated, tag = prepare_version(
        app.read_text(encoding="utf-8"), os.environ.get("REQUESTED_TAG", ""),
        os.environ["GITHUB_REF_TYPE"], os.environ["GITHUB_REF_NAME"],
        os.environ["GITHUB_RUN_NUMBER"],
    )
    # Use the actual checked-out commit, including manually selected tags.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    app.write_text(updated, encoding="utf-8")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"tag={tag}\ncommit={commit}\n")
    print(f"Building {tag} from {commit}")


if __name__ == "__main__":
    main()
