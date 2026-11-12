#!/usr/bin/env python3
"""Build db.json for the MiSTer Downloader from the latest full release of each core in cores.json.

Pre-releases are left out: a build reaches the MiSTer only once it is promoted to a full release.
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
    known = {f["url"]: f for f in old["files"].values()}  # an asset URL names one tag: same file

    files, folders = {}, {}
    for core in cfg["cores"]:
        repo, folder = core["repo"], core.get("folder", "_Console")
        try:
            rel = get(f"{API}/repos/{repo}/releases/latest")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # no full release yet
                print(f"{repo}: no release")
                continue
            raise
        assets = {a["name"]: a for a in rel["assets"]}
        if "sd-files.json" in assets:  # asset name -> path on the SD card
            layout = json.loads(get(assets.pop("sd-files.json")["browser_download_url"], raw=True))
        else:  # just the core
            layout = {n: f"{folder}/{n}" for n in assets if n.endswith(".rbf")}
        if set(layout) != set(assets) or sum(p.endswith(".rbf") for p in layout.values()) != 1:
            sys.exit(f"{repo} {rel['tag_name']}: assets {sorted(assets)} do not match {layout}")
        for name, path in layout.items():
            a = assets[name]
            url = a["browser_download_url"]
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
        print(f"{repo}: {rel['tag_name']}, {len(layout)} files")

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
