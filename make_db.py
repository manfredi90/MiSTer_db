#!/usr/bin/env python3
"""Build db.json for the MiSTer Downloader from the cores each fork in cores.json publishes in
releases/ on its default branch: releases/ss-files.json gives the path on the SD card of each file.
The timestamp changes only when the set of files does, so the Downloader skips unchanged runs.
Needs GH_TOKEN (any token that can read public repositories) for the GitHub API.
"""
import hashlib, json, os, sys, time, urllib.error, urllib.request

API = "https://api.github.com"


def get(url, raw=False):
    """API call (JSON), or with raw=True a public download (no token: the redirect goes to another host)."""
    headers = {} if raw else {"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
        return r.read() if raw else json.load(r)


def main():
    cfg = json.load(open("cores.json"))
    try:
        old = json.load(open("db.json"))
    except FileNotFoundError:
        old = {"files": {}}
    known = {f["url"]: f for f in old["files"].values()}  # a URL names one commit: same file

    files, folders = {}, {}
    for core in cfg["cores"]:
        repo = core["repo"]
        branch = get(f"{API}/repos/{repo}")["default_branch"]
        commits = get(f"{API}/repos/{repo}/commits?sha={branch}&path=releases/ss-files.json&per_page=1")
        if not commits:  # nothing published yet
            print(f"{repo}: no release")
            continue
        sha = commits[0]["sha"]  # the files at that commit: they always match each other
        raw = f"https://raw.githubusercontent.com/{repo}/{sha}/"
        layout = json.loads(get(raw + "releases/ss-files.json", raw=True))  # SD path -> repo path
        if sum(p.endswith(".rbf") for p in layout) != 1:
            sys.exit(f"{repo} {sha[:7]}: expected one RBF in {sorted(layout)}")
        for path, src in layout.items():
            url = raw + src
            if url in known:
                entry = {k: known[url][k] for k in ("hash", "size", "url")}
            else:
                data = get(url, raw=True)
                entry = {"hash": hashlib.md5(data).hexdigest(), "size": len(data), "url": url}
            if path in files:
                sys.exit(f"{path} comes from two cores")
            files[path] = entry
            d = os.path.dirname(path)
            while d:  # every parent folder
                folders[d] = {}
                d = os.path.dirname(d)
        print(f"{repo}: {sha[:7]}, {len(layout)} files")

    if files == old["files"] and os.path.exists("db.json"):
        print("unchanged")
        return
    db = {"v": 1, "db_id": cfg["db_id"], "timestamp": int(time.time()), "files": files, "folders": folders}
    with open("db.json", "w") as f:
        json.dump(db, f, indent=2, sort_keys=True)
        f.write("\n")
    print("db.json updated")


if __name__ == "__main__":
    main()
