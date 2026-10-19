"""Updates profile/README.md with the latest and top-ranked public repos.

Runs inside GitHub Actions (daily + manual). Uses only the standard library.
"""
import json
import os
import re
import urllib.request
from datetime import datetime

ORG = os.environ.get("ORG", "SMMpro-pk")
README = os.environ.get("README_PATH", "profile/README.md")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
LIMIT = 5
SKIP = {".github"}  # the profile repo itself is not listed


def fetch_repos():
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos?type=public&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "smmpro-profile-updater"})
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
        if not batch:
            break
        repos += batch
        page += 1
    return [r for r in repos if r["name"] not in SKIP and not r.get("archived") and not r.get("fork")]


def clean(text, n=90):
    text = (text or "No description yet.").replace("|", "/").replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def table(repos):
    if not repos:
        return "_No public repositories yet. Check back soon._"
    rows = ["| Repository | Description | ⭐ Stars | Updated |", "|---|---|:---:|:---:|"]
    for r in repos:
        updated = datetime.strptime(r["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %Y")
        lang = f" `{r['language']}`" if r.get("language") else ""
        rows.append(f"| [**{r['name']}**]({r['html_url']}){lang} | {clean(r['description'])} | {r['stargazers_count']} | {updated} |")
    return "\n".join(rows)


def replace_block(text, marker, content):
    pattern = re.compile(rf"(<!-- {marker}:START -->)(.*?)(<!-- {marker}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def main():
    repos = fetch_repos()
    latest = sorted(repos, key=lambda r: r["pushed_at"], reverse=True)[:LIMIT]
    top = sorted(repos, key=lambda r: (r["stargazers_count"], r["forks_count"], r["pushed_at"]), reverse=True)[:LIMIT]

    with open(README, encoding="utf-8") as f:
        text = f.read()
    new = replace_block(text, "LATEST_REPOS", table(latest))
    new = replace_block(new, "TOP_REPOS", table(top))
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
