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
- **Manual (`workflow_dispatch`)**: useful for smoke tests. Two inputs:
  - `sbom_source`: `metadata` (all packages, ~3500 components, ~3 min) or
    `snapshot` (fetch the published image SBOM for `armsr/armv8`, ~200 components, seconds).
  - `skip_publish`: generate and upload artifact only; don't deploy to Pages.

## Pipeline

1. `make prepare-tmpinfo` parses every feed Makefile into `tmp/.packageinfo`.
2. `scripts/package-metadata.pl allpkgcyclonedxsbom` dumps that as CycloneDX JSON.
3. [Trivy](https://trivy.dev/) and [OSV-Scanner](https://osv.dev/) each scan the SBOM; results are merged (union, keeping the lowest severity number when both report the same CVE).
4. [`check_versions.py`](check_versions.py) queries [Repology](https://repology.org/) for newer upstream versions and [endoflife.date](https://endoflife.date/) for EOL status. Responses are cached under `actions/cache` to keep runs under the 6-hour limit (Repology is rate-limited to 1 req/sec).
5. [`render.py`](render.py) renders `index.html`, `cves.html`, `outdated.html`, `eol.html`, and a machine-readable `report.json` from the Jinja templates in [`templates/`](templates/).
6. The `public/` directory is uploaded as a Pages artifact and deployed.

## Local dry run

```bash
pip install --user jinja2
./scripts/feeds update -a
./scripts/feeds install -a
make defconfig
make prepare-tmpinfo
mkdir -p /tmp/sbom && cd /tmp/sbom

# 1. SBOM
"$OLDPWD"/scripts/package-metadata.pl allpkgcyclonedxsbom "$OLDPWD"/tmp/.packageinfo > sbom.json

# 2. CVE scanners (skip if not installed — render.py handles empty files)
trivy sbom --format json --output trivy.json sbom.json || echo '{"Results":[]}' > trivy.json
osv-scanner --sbom=sbom.json --format=json --output=osv.json || echo '{"results":[]}' > osv.json

# 3. Versions (use --limit 20 for a quick test)
python3 "$OLDPWD"/.github/sbom-report/check_versions.py \
  --sbom sbom.json --out versions.json --cache cache.json --limit 20

# 4. Render
python3 "$OLDPWD"/.github/sbom-report/render.py \
  --sbom sbom.json --trivy trivy.json --osv osv.json \
  --versions versions.json \
  --templates "$OLDPWD"/.github/sbom-report/templates \
  --out public --sbom-source "local dry run"

xdg-open public/index.html
```

## Notes and caveats

- CPE-based matching produces false positives for packages OpenWrt has
  backported a fix for but kept the same `PKG_VERSION`. Suppressions
  aren't implemented yet — add them in the workflow after the first real
  run reveals the worst offenders.
- The `allpkgcyclonedxsbom` subcommand is a candidate to upstream to
  the OpenWrt project — it has no dependencies outside the existing
  `scripts/metadata.pm` helpers.
- The CVE scan hits public databases that change daily, so week-to-week
  report diffs can reflect DB updates rather than code changes.
