#!/usr/bin/env python3
"""
Read a CycloneDX SBOM and, for each component, look up newer upstream
versions via Repology and EOL status via endoflife.date.

Outputs a JSON document with one entry per component that has useful data
(newer version available and/or EOL info). Uses an on-disk cache so
repeated runs don't hammer the Repology API.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOLOGY_URL = "https://repology.org/api/v1/project/{name}"
ENDOFLIFE_URL = "https://endoflife.date/api/{product}.json"
USER_AGENT = "openwrt-sbom-report/1.0 (+https://github.com/openwrt/openwrt)"

REPOLOGY_DELAY_SEC = 1.0
CACHE_MAX_AGE_SEC = 6 * 24 * 3600  # 6 days — cron runs weekly


def http_get_json(url: str, timeout: int = 30):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    except URLError:
        return None


def version_tuple(v: str):
    out = []
    cur = ""
    for ch in v:
        if ch.isdigit():
            cur += ch
        else:
            if cur:
                out.append(int(cur))
                cur = ""
            if ch == ".":
                continue
            break
    if cur:
        out.append(int(cur))
    return tuple(out) if out else (0,)


def repology_newest(name: str) -> dict | None:
    data = http_get_json(REPOLOGY_URL.format(name=quote(name.lower())))
    if not data:
        return None
    newest = None
    repos = set()
    for entry in data:
        repos.add(entry.get("repo", ""))
        if entry.get("status") == "newest":
            v = entry.get("version")
            if v and (newest is None or version_tuple(v) > version_tuple(newest)):
                newest = v
    if newest:
        return {"newest_version": newest, "sources": sorted(r for r in repos if r)[:8]}
    return None


def endoflife_lookup(product: str, version: str) -> dict | None:
    data = http_get_json(ENDOFLIFE_URL.format(product=quote(product)))
    if not data:
        return None
    v_major = ".".join(str(p) for p in version_tuple(version)[:2])
    for cycle in data:
        cycle_id = str(cycle.get("cycle", ""))
        if cycle_id == v_major or version.startswith(cycle_id):
            return {
                "cycle": cycle_id,
                "eol": cycle.get("eol"),
                "latest": cycle.get("latest"),
                "support": cycle.get("support"),
            }
    return None


EOL_PRODUCTS = {
    "kernel": "linux",
    "linux-kernel": "linux",
    "openssl": "openssl",
    "nodejs": "nodejs",
    "node": "nodejs",
    "python3": "python",
    "python": "python",
    "postgresql": "postgresql",
    "mariadb": "mariadb",
    "dropbear": None,
    "dnsmasq": None,
}


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cache", default=Path(".cache/repology.json"), type=Path)
    ap.add_argument("--limit", type=int, default=0, help="Limit components (0 = all). Debug only.")
    args = ap.parse_args()

    sbom = json.loads(args.sbom.read_text())
    components = sbom.get("components", [])
    if args.limit:
        components = components[: args.limit]

    cache = load_cache(args.cache)
    now = time.time()
    results = []
    new_lookups = 0

    for idx, comp in enumerate(components):
        name = comp.get("name")
        version = comp.get("version")
        if not name or not version:
            continue

        cache_key = name.lower()
        cached = cache.get(cache_key)
        if cached and (now - cached.get("ts", 0)) < CACHE_MAX_AGE_SEC:
            repo_info = cached.get("repology")
        else:
            repo_info = repology_newest(name)
            cache[cache_key] = {"ts": now, "repology": repo_info}
            new_lookups += 1
            time.sleep(REPOLOGY_DELAY_SEC)
            if new_lookups % 50 == 0:
                save_cache(args.cache, cache)
                print(f"[{idx}/{len(components)}] {new_lookups} live lookups so far", file=sys.stderr)

        eol_key = EOL_PRODUCTS.get(name.lower())
        eol_info = endoflife_lookup(eol_key, version) if eol_key else None

        entry = {"name": name, "version": version}
        outdated = False
        if repo_info and repo_info.get("newest_version"):
            newest = repo_info["newest_version"]
            if version_tuple(newest) > version_tuple(version):
                entry["newest_version"] = newest
                entry["sources"] = repo_info.get("sources", [])
                outdated = True
        if eol_info:
            entry["eol"] = eol_info
        if outdated or eol_info:
            results.append(entry)

    save_cache(args.cache, cache)

    out = {
        "generated": int(now),
        "total_components": len(components),
        "new_lookups": new_lookups,
        "outdated": [r for r in results if "newest_version" in r],
        "eol": [r for r in results if "eol" in r],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {args.out}: {len(out['outdated'])} outdated, {len(out['eol'])} EOL entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
