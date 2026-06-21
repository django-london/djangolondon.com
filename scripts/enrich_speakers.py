#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomli-w"]
# ///
# Script to enrich speaker data with GitHub, Mastodon, and Bluesky information,
# by searching GitHub for the given name, checking for signals from their bio
# (mention of Django or Python) and pinned repositories (mention of Django or
# Python), and then retrieving their Mastodon and Bluesky accounts.

import json
import subprocess
import time
import tomllib
from pathlib import Path

import tomli_w

BASE_DIR = Path(__file__).resolve().parent.parent
SPEAKERS_DIR = BASE_DIR / "data" / "speakers"

EXCLUDE = {
    "andy-jones",
    "girish-kumar",
}


def gh(path):
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def gh_graphql(query):
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def has_confidence(username):
    user = gh(f"users/{username}")
    if user is None:
        return False

    bio = (user.get("bio") or "").lower()
    if "django" in bio or "python" in bio:
        return True

    gql = gh_graphql(
        f'{{ user(login: "{username}") {{'
        f"  pinnedItems(first: 6, types: REPOSITORY) {{"
        f"    nodes {{ ... on Repository {{"
        f"      name description primaryLanguage {{ name }}"
        f"    }} }}"
        f"  }}"
        f"}} }}"
    )
    if gql:
        nodes = (
            gql.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
        )
        for repo in nodes:
            repo_name = (repo.get("name") or "").lower()
            desc = (repo.get("description") or "").lower()
            lang = (repo.get("primaryLanguage") or {}).get("name", "").lower()
            if any("django" in s or "python" in s for s in [repo_name, desc, lang]):
                return True

    commits = gh(f"repos/django/django/commits?author={username}&per_page=1")
    return bool(commits and isinstance(commits, list) and len(commits) > 0)


def find_github_user(name):
    q = "+".join(name.split())
    results = gh(f"search/users?q={q}&per_page=5")
    if not results:
        return None
    for item in results.get("items", []):
        login = item["login"]
        if has_confidence(login):
            return login
    return None


def get_social(username):
    accounts = gh(f"users/{username}/social_accounts")
    mastodon = ""
    bluesky = ""
    if accounts:
        for acc in accounts:
            provider = acc.get("provider", "").lower()
            url = acc.get("url", "")
            if provider == "mastodon":
                mastodon = url
            elif provider == "bluesky":
                bluesky = url.removeprefix("https://bsky.app/profile/").rstrip("/")
    return mastodon, bluesky


def process_speaker(toml_file):
    with toml_file.open("rb") as f:
        data = tomllib.load(f)

    name = data["name"]
    orig_github = data.get("github_username", "")
    orig_mastodon = data.get("mastodon_url", "")
    orig_bluesky = data.get("bluesky_handle", "")

    if orig_github and orig_mastodon and orig_bluesky:
        return

    if toml_file.stem in EXCLUDE:
        return

    github = orig_github
    mastodon = orig_mastodon
    bluesky = orig_bluesky

    if not github:
        github = find_github_user(name) or ""

    if github and (not mastodon or not bluesky):
        new_mastodon, new_bluesky = get_social(github)
        if new_mastodon and not mastodon:
            mastodon = new_mastodon
        if new_bluesky and not bluesky:
            bluesky = new_bluesky

    if github == orig_github and mastodon == orig_mastodon and bluesky == orig_bluesky:
        return

    new_data: dict = {"name": name}
    if github:
        new_data["github_username"] = github
    if mastodon:
        new_data["mastodon_url"] = mastodon
    if bluesky:
        new_data["bluesky_handle"] = bluesky

    with toml_file.open("wb") as f:
        tomli_w.dump(new_data, f)

    parts = [name]
    if github != orig_github:
        parts.append(f"github={github}")
    if mastodon != orig_mastodon:
        parts.append(f"mastodon={mastodon}")
    if bluesky != orig_bluesky:
        parts.append(f"bluesky={bluesky}")
    print("  ".join(parts))


def main():
    for toml_file in sorted(SPEAKERS_DIR.glob("*.toml")):
        process_speaker(toml_file)
        time.sleep(2)


if __name__ == "__main__":
    main()
