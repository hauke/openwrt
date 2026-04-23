#!/usr/bin/env python3
"""
Match each component in a CycloneDX SBOM against the NVD database.

Reads a CycloneDX JSON SBOM (as produced by
`scripts/package-metadata.pl allpkgcyclonedxsbom`), a local git clone
of https://github.com/fkie-cad/nvd-json-data-feeds/ under --nvd-dir/git,
and emits:

  * a flat list of findings at --out-cves (consumed by render.py)
  * an enriched CycloneDX SBOM at --out-sbom with a 'vulnerabilities'
    array per CDX 1.4 spec (for downstream tools like DependencyTrack)

Matching is done using the vendored cve.py (from Buildroot), which
implements proper NIST IR 7696 CPE matching and version-range checks.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cve import CPE, CVE  # noqa: E402


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


def cpe22_to_23(uri: str) -> str | None:
    """Convert a CPE 2.2 URI (cpe:/a:vendor:product:version) to CPE 2.3
    formatted string (cpe:2.3:a:vendor:product:version:*:*:*:*:*:*:*)."""
    if not uri:
        return None
    if uri.startswith("cpe:2.3:"):
        return uri
    if not uri.startswith("cpe:/"):
        return None
    body = uri[5:]
    parts = body.split(":")
    while len(parts) < 7:
        parts.append("*")
    parts = [p if p else "*" for p in parts[:7]]
    parts_23 = parts + ["*", "*", "*", "*"]
    return "cpe:2.3:" + ":".join(parts_23)


def cpe_for_component(comp: dict) -> CPE | None:
    """Return a CPE 2.3 object for a SBOM component, or None if we can't
    build one with enough information to match."""
    cpe = comp.get("cpe")
    version = comp.get("version")
    name = comp.get("name")
    if cpe:
        as_23 = cpe22_to_23(cpe)
        if as_23:
            return CPE(as_23)
    if name and version:
        return CPE(f"cpe:2.3:*:*:{name}:{version}:*:*:*:*:*:*:*")
    return None


def severity_from_cve(cve: CVE) -> str:
    return cve.severity


def cve_url(cve_id: str) -> str:
    if cve_id.startswith("CVE-"):
        return f"https://nvd.nist.gov/vuln/detail/{cve_id}"
    return f"https://nvd.nist.gov/vuln/detail/{cve_id}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom", required=True, type=Path)
    ap.add_argument("--nvd-dir", required=True, type=Path)
    ap.add_argument("--out-cves", required=True, type=Path)
    ap.add_argument("--out-sbom", required=True, type=Path)
    ap.add_argument(
        "--only-with-cpe",
        action="store_true",
        help="Only match components that have an explicit CPE (skips fuzzy "
             "name-based fallbacks that tend to false-positive).",
    )
    args = ap.parse_args()

    sbom = json.loads(args.sbom.read_text())
    components = sbom.get("components", [])

    # Build an index: product -> [(component, CPE)]
    components_by_product: dict[str, list[tuple[dict, CPE]]] = defaultdict(list)
    kept = 0
    for comp in components:
        if args.only_with_cpe and not comp.get("cpe"):
            continue
        cpe_obj = cpe_for_component(comp)
        if not cpe_obj or not cpe_obj.product or cpe_obj.product == "*":
            continue
        components_by_product[cpe_obj.product].append((comp, cpe_obj))
        kept += 1
    print(f"Indexed {kept}/{len(components)} components across "
          f"{len(components_by_product)} products", file=sys.stderr)

    # Findings are keyed by (cve_id, cpe_product, component_version).
    # This collapses the common "one kernel CVE affects 1000+ kmod-*
    # packages" case into a single finding with a packages[] list,
    # because all the kmod subpackages share the kernel's CPE and
    # version — they are the same upstream artifact.
    findings_by_key: dict[tuple[str, str, str], dict] = {}
    started = time.time()
    cves_checked = 0
    cves_matched = 0

    for cve in CVE.read_nvd_dir(str(args.nvd_dir)):
        cves_checked += 1
        if cves_checked % 20000 == 0:
            dt = time.time() - started
            print(f"  scanned {cves_checked} CVEs, {cves_matched} matches "
                  f"({dt:.1f}s)", file=sys.stderr)

        affected_products = cve.affected_products
        if not affected_products:
            continue

        # Only consider CVEs that touch a product we have
        relevant_products = affected_products & components_by_product.keys()
        if not relevant_products:
            continue

        for product in relevant_products:
            # Probe the CVE once per (product, version) pair rather than
            # once per component — components that share the same CPE
            # get the same match outcome.
            probed: dict[str, int] = {}
            for comp, cpe_obj in components_by_product[product]:
                version = comp.get("version", "")
                if version in probed:
                    result = probed[version]
                else:
                    result = cve.affects(
                        comp.get("name", ""), version, cpe_obj
                    )
                    probed[version] = result
                if result != CVE.CVE_AFFECTS:
                    continue

                key = (cve.identifier, product, version)
                finding = findings_by_key.get(key)
                if finding is None:
                    finding = {
                        "id": cve.identifier,
                        "severity": severity_from_cve(cve),
                        "cpe_product": product,
                        "version": version,
                        "package": comp.get("name", ""),
                        "packages": [],
                        "fixed_version": "",
                        "title": cve.description[:240],
                        "source": "nvd",
                        "url": cve_url(cve.identifier),
                        "cpe": cpe_obj.cpe,
                    }
                    findings_by_key[key] = finding
                    cves_matched += 1
                finding["packages"].append(comp.get("name", ""))

    findings = list(findings_by_key.values())
    for f in findings:
        # Prefer a stable primary package name (shortest, alphabetically
        # first) so the report has a consistent "package" column.
        if f["packages"]:
            f["packages"].sort(key=lambda n: (len(n), n))
            f["package"] = f["packages"][0]

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9),
                                 f["package"], f["id"]))

    args.out_cves.parent.mkdir(parents=True, exist_ok=True)
    args.out_cves.write_text(json.dumps(findings, indent=2))
    print(f"Wrote {args.out_cves} — {len(findings)} findings "
          f"(scanned {cves_checked} CVEs in {time.time() - started:.1f}s)",
          file=sys.stderr)

    # Enrich the SBOM with CycloneDX-native 'vulnerabilities' array.
    vuln_by_id: dict[str, dict] = {}
    for f in findings:
        v = vuln_by_id.setdefault(f["id"], {
            "id": f["id"],
            "source": {"name": "NVD",
                       "url": f["url"]},
            "ratings": [{"severity": f["severity"].lower()}]
                        if f["severity"] != "UNKNOWN" else [],
            "description": f["title"],
            "affects": [],
        })
        seen_refs = {a["ref"] for a in v["affects"]}
        for pkg in f.get("packages", [f.get("package", "")]):
            if pkg and pkg not in seen_refs:
                v["affects"].append({"ref": pkg})
                seen_refs.add(pkg)

    sbom["vulnerabilities"] = list(vuln_by_id.values())
    args.out_sbom.parent.mkdir(parents=True, exist_ok=True)
    args.out_sbom.write_text(json.dumps(sbom, indent=2))
    print(f"Wrote {args.out_sbom} — enriched SBOM with "
          f"{len(sbom['vulnerabilities'])} unique vulnerabilities",
          file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
