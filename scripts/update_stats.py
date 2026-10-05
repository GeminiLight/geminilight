"""Refresh the profile's compact counters from public GitHub data."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

START = "<!-- github-stats:start -->"
END = "<!-- github-stats:end -->"


def fetch(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-stats",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request("https://api.github.com" + path, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(username):
    user_path = "/users/" + quote(username, safe="")
    account = fetch(user_path)
    repos = []
    page = 1
    while True:
        batch = fetch(user_path + "/repos?type=owner&per_page=100&page=" + str(page))
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    stars = sum(
        repo["stargazers_count"] for repo in repos
        if not repo["fork"] and not repo["private"]
        and repo["owner"]["login"].lower() == username.lower()
    )
    return {
        "stars": stars,
        "public_repos": account["public_repos"],
        "followers": account["followers"],
    }


def render(stats):
    return (
        START + '\n<p align="center">\n'
        f'  <strong>{stats["stars"]:,}</strong> stars &nbsp; &nbsp; &nbsp;\n'
        f'  <strong>{stats["public_repos"]:,}</strong> public repos &nbsp; &nbsp; &nbsp;\n'
        f'  <strong>{stats["followers"]:,}</strong> followers\n'
        '</p>\n' + END
    )


def replace_stats(text, stats):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one GitHub stats block")
    pattern = re.escape(START) + r".*?" + re.escape(END)
    updated, count = re.subn(pattern, lambda match: render(stats), text, flags=re.S)
    if count != 1:
        raise ValueError("GitHub stats markers are out of order")
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    args = parser.parse_args()
    stats = collect(args.username)
    original = args.readme.read_text(encoding="utf-8")
    updated = replace_stats(original, stats)
    if updated != original:
        args.readme.write_text(updated, encoding="utf-8")
    print(json.dumps({**stats, "updated": updated != original}))


if __name__ == "__main__":
    main()

