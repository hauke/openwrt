#!/usr/bin/env python3
"""
Merge CVE and version-check outputs into a static HTML report
(index.html, cves.html, outdated.html, eol.html).

CVE input is the flat list produced by scan_cves.py plus optionally
OSV-Scanner's JSON, merged by (CVE id, package name).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


def normalize_severity(s: str | None) -> str:
    if not s:
        return "UNKNOWN"
    s = s.upper()
    return s if s in SEVERITY_ORDER else "UNKNOWN"


def cve_url(cve_id: str) -> str:
    if cve_id.startswith("CVE-"):
        return f"https://nvd.nist.gov/vuln/detail/{cve_id}"
    if cve_id.startswith("GHSA-"):
        return f"https://github.com/advisories/{cve_id}"
    return f"https://osv.dev/vulnerability/{cve_id}"


def load_cves_json(path: Path) -> list[dict]:
    """Load the flat list produced by scan_cves.py."""
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        return []
    out = []
    for v in data:
        out.append({
            "id": v.get("id", ""),
            "severity": normalize_severity(v.get("severity")),
            "package": v.get("package", ""),
            "packages": v.get("packages", []),
            "version": v.get("version", ""),
            "fixed_version": v.get("fixed_version", ""),
            "title": v.get("title", ""),
            "source": v.get("source", "nvd"),
        })
    return out


def load_osv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    out = []
    for res in data.get("results", []) or []:
        for pkg in res.get("packages", []) or []:
            pinfo = pkg.get("package", {}) or {}
            pkg_name = pinfo.get("name", "")
            pkg_ver = pinfo.get("version", "")
            for vuln in pkg.get("vulnerabilities", []) or []:
                severity = "UNKNOWN"
                for s in vuln.get("severity", []) or []:
                    score = s.get("score", "")
                    if "CVSS" in s.get("type", "") and score:
                        try:
                            val = float(score.split("/")[0].split(":")[-1]) if "/" in score else float(score)
                            if val >= 9.0:
                                severity = "CRITICAL"
                            elif val >= 7.0:
                                severity = "HIGH"
                            elif val >= 4.0:
                                severity = "MEDIUM"
                            elif val > 0:
                                severity = "LOW"
                        except ValueError:
                            pass
                out.append({
                    "id": vuln.get("id", ""),
                    "severity": severity,
                    "package": pkg_name,
                    "version": pkg_ver,
                    "fixed_version": "",
                    "title": vuln.get("summary", "") or (vuln.get("details", "") or "")[:200],
                    "source": "osv",
                })
    return out


def merge_cves(*sources: list[dict]) -> list[dict]:
    by_key: dict[tuple, dict] = {}
    for v in [x for src in sources for x in src]:
        key = (v["id"], v["package"])
        if key in by_key:
            existing = by_key[key]
            existing_sources = set(existing.get("sources", [existing["source"]]))
            existing_sources.add(v["source"])
            existing["sources"] = sorted(existing_sources)
            if SEVERITY_ORDER[v["severity"]] < SEVERITY_ORDER[existing["severity"]]:
                existing["severity"] = v["severity"]
            if not existing.get("fixed_version") and v.get("fixed_version"):
                existing["fixed_version"] = v["fixed_version"]
            if not existing.get("packages") and v.get("packages"):
                existing["packages"] = v["packages"]
        else:
            v = dict(v)
            v["sources"] = [v["source"]]
            v["url"] = cve_url(v["id"])
            by_key[key] = v
    result = list(by_key.values())
    result.sort(key=lambda x: (SEVERITY_ORDER[x["severity"]], x["package"], x["id"]))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom", required=True, type=Path)
    ap.add_argument("--cves", type=Path, help="Flat CVE JSON from scan_cves.py")
    ap.add_argument("--osv", type=Path, help="OSV-Scanner JSON output")
    ap.add_argument("--versions", required=True, type=Path)
    ap.add_argument("--templates", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--sbom-source", default="openwrt all-packages metadata")
    args = ap.parse_args()

    sbom = json.loads(args.sbom.read_text())
    components = sbom.get("components", [])
    nvd = load_cves_json(args.cves) if args.cves else []
    osv = load_osv(args.osv) if args.osv else []
    cves = merge_cves(nvd, osv)
    versions = json.loads(args.versions.read_text())

    per_pkg = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0})
    for v in cves:
        per_pkg[v["package"]]["total"] += 1
        if v["severity"] == "CRITICAL":
            per_pkg[v["package"]]["critical"] += 1
        elif v["severity"] == "HIGH":
            per_pkg[v["package"]]["high"] += 1

    pkg_versions = {c.get("name"): c.get("version", "") for c in components}
    top_vulnerable = sorted(
        [{"name": n, "version": pkg_versions.get(n, ""), **s} for n, s in per_pkg.items()],
        key=lambda x: (-x["critical"], -x["high"], -x["total"]),
    )[:50]

    counts = {
        "components": len(components),
        "cves": len(cves),
        "critical": sum(1 for v in cves if v["severity"] == "CRITICAL"),
        "high": sum(1 for v in cves if v["severity"] == "HIGH"),
        "outdated": len(versions.get("outdated", [])),
        "eol": len(versions.get("eol", [])),
    }

    env = Environment(
        loader=FileSystemLoader(str(args.templates)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
    )

    ctx = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "sbom_source": args.sbom_source,
        "counts": counts,
    }

    args.out.mkdir(parents=True, exist_ok=True)

    (args.out / "index.html").write_text(
        env.get_template("index.html.j2").render(
            page="index", title="Overview", top_vulnerable=top_vulnerable, **ctx
        )
    )
    (args.out / "cves.html").write_text(
        env.get_template("cves.html.j2").render(page="cves", title="CVEs", cves=cves, **ctx)
    )
    (args.out / "outdated.html").write_text(
        env.get_template("outdated.html.j2").render(
            page="outdated", title="Outdated", outdated=versions.get("outdated", []), **ctx
        )
    )
    (args.out / "eol.html").write_text(
        env.get_template("eol.html.j2").render(
            page="eol", title="EOL", eol=versions.get("eol", []), **ctx
        )
    )

    (args.out / "report.json").write_text(
        json.dumps({"counts": counts, "cves": cves, "versions": versions}, indent=2)
    )

    print(f"Wrote report to {args.out}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
