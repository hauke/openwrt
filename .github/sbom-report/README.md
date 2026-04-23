# SBOM report

Generates a weekly HTML report of CVEs, outdated versions, and EOL
components for every package known to the OpenWrt build tree.

The report is built and published by [`.github/workflows/sbom-report.yml`](../workflows/sbom-report.yml).

## One-time setup

Enable GitHub Pages with source set to **GitHub Actions** in the repo's
settings (Settings → Pages → "Build and deployment" → Source → GitHub Actions).
Without this, the `deploy` job will fail on the first run.

## Triggers

- **Weekly cron**: Mondays at 04:17 UTC.
- **Manual (`workflow_dispatch`)** for smoke tests. Two inputs:
  - `skip_publish`: build the artifact without deploying to Pages.
  - `skip_versions`: skip the Repology + endoflife.date scan. It's
    the slowest step of the pipeline (Repology is rate-limited to
    ~1 req/sec), so turning it off makes iteration on the rest of
    the workflow much faster.

## Pipeline

1. `make prepare-tmpinfo` parses every feed Makefile into `tmp/.packageinfo`.
2. `scripts/package-metadata.pl allpkgcyclonedxsbom` dumps that as CycloneDX JSON.
3. [`scan_cves.py`](scan_cves.py) matches each SBOM component's CPE against the NVD database. Matching logic ([`cve.py`](cve.py)) is vendored from [Buildroot](https://git.buildroot.net/buildroot/tree/support/scripts/cve.py) (GPL-2.0-or-later): NIST IR 7696 CPE comparison and NVD version-range operators (`versionStartIncluding`, `versionEndExcluding`, …). NVD data is a shallow `actions/checkout` of [fkie-cad/nvd-json-data-feeds](https://github.com/fkie-cad/nvd-json-data-feeds).
4. [OSV-Scanner](https://osv.dev/) runs as a secondary source to catch GHSA advisories the NVD doesn't yet cover. Results are merged by `(CVE id, package name)`.
5. [`check_versions.py`](check_versions.py) queries [Repology](https://repology.org/) for newer upstream versions and [endoflife.date](https://endoflife.date/) for EOL status. Responses are cached under `actions/cache` (Repology is rate-limited to ~1 req/sec).
6. [`render.py`](render.py) renders `index.html`, `cves.html`, `outdated.html`, `eol.html`, a machine-readable `report.json`, and `sbom.cdx.json` — a CycloneDX SBOM enriched with a standard `vulnerabilities[]` array for downstream tools like DependencyTrack.
7. The `public/` directory is uploaded as a Pages artifact and deployed via `actions/deploy-pages`.

## Local dry run

```bash
pip install --user jinja2
./scripts/feeds update -a
./scripts/feeds install -a
make defconfig
make prepare-tmpinfo
mkdir -p /tmp/sbom && cd /tmp/sbom

# 1. SBOM
"$OLDPWD"/scripts/package-metadata.pl allpkgcyclonedxsbom \
  "$OLDPWD"/tmp/.packageinfo > sbom.cdx.json

# 2. NVD mirror (first run: ~5 min, ~1 GB on disk)
mkdir -p nvd
git clone --depth=1 https://github.com/fkie-cad/nvd-json-data-feeds.git nvd/git

# 3. Match CVEs
python3 "$OLDPWD"/.github/sbom-report/scan_cves.py \
  --sbom sbom.cdx.json --nvd-dir nvd \
  --out-cves cves.json --out-sbom sbom-enriched.json \
  --only-with-cpe

# 4. (Optional) OSV-Scanner — skip if not installed
osv-scanner -L sbom.cdx.json --format=json --output-file=osv.json \
  || echo '{"results":[]}' > osv.json

# 5. Versions (add --limit 20 for a quick test)
python3 "$OLDPWD"/.github/sbom-report/check_versions.py \
  --sbom sbom.cdx.json --out versions.json --cache cache.json --limit 20

# 6. Render
python3 "$OLDPWD"/.github/sbom-report/render.py \
  --sbom sbom.cdx.json --cves cves.json --osv osv.json \
  --versions versions.json \
  --templates "$OLDPWD"/.github/sbom-report/templates \
  --out public --sbom-source "local dry run"

xdg-open public/index.html
```

## Notes and caveats

- CPE-based matching produces false positives for packages that OpenWrt
  has backported a fix for but kept the same `PKG_VERSION`. Suppressions
  aren't implemented yet — add them after the first real run reveals the
  worst offenders.
- `scan_cves.py --only-with-cpe` skips components that don't declare a
  CPE in `package-metadata.pl`. Dropping the flag enables a name-based
  fallback that has significantly more false positives.
- The `allpkgcyclonedxsbom` subcommand is a candidate to upstream to the
  OpenWrt project — it has no dependencies outside the existing
  `scripts/metadata.pm` helpers.
- The NVD mirror is refreshed daily by fkie-cad. Week-to-week report
  diffs can reflect DB updates rather than code changes.
