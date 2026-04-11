# Contributing to OpenWrt

This document describes conventions for commits, pull requests, and code
style in the OpenWrt repository. The CI system enforces many of these rules
automatically via `check_formalities.sh`. Please follow all guidelines to
avoid unnecessary review round-trips.

---

## Where to Submit

Changes go to different repositories depending on scope:

| Content | Repository |
|---|---|
| Core OpenWrt, device support, kernel | This repository |
| LuCI web interface | `openwrt/luci` |
| Routing packages | `openwrt/routing` |
| Telephony packages | `openwrt/telephony` |
| Miscellaneous community packages | `openwrt/packages` |

---

## Commit Messages

### Subject line

The subject line must follow this pattern:

```
<component>: <description starting with lowercase>
```

- Use colon-space (`: `) as separator. Nested components use multiple
  segments: `mediatek: filogic: add support for foo`
- The description must start with a **lowercase** letter (CI hard fails on
  uppercase)
- Use the **imperative form**: "add support", "fix crash", "update to v2.1"
  — not "added" or "adds"
- Do **not** end the subject line with a period
- Keep it at most **60 characters** (CI fails above 60, warns above 50)
- Valid component characters: `[0-9A-Za-z,+/._-]`; `Revert ` is also
  accepted as a subject prefix

Good examples:

```
ipq40xx: avoid randomized MAC address on boot
kernel: net: sfp: add quirks for GPON ONT SFP sticks
wifi-scripts: fix txpower 0 treated as auto in ucode
treewide: strip trailing whitespace
arm-trusted-firmware-mvebu: bump to 2.14
```

### Body

- A non-empty body is **required** — CI fails with "Commit message is
  missing" when only `Signed-off-by:` is present
- Wrap all lines at **75 characters** (URLs included)
- Explain **why** the change is needed, not just what it does. Describe
  symptoms of bugs, motivation for new features, or device characteristics
  for new hardware support
- Write in third person / imperative — do **not** write "This PR adds …";
  write "This adds …" or just "Add …"
- For reverts, include: `This reverts commit <sha>.`
- For cherry-picks to stable branches, include:
  `(cherry picked from commit <sha>)`

### Signed-off-by

Every commit **must** contain a `Signed-off-by:` line:

```
Signed-off-by: First Last <email@example.com>
```

Configure git once:

```sh
git config --global user.name "Your Real Name"
git config --global user.email "you@example.com"
```

- Use your **real name** (first + last) — a single-word name causes a CI
  warning
- The name and email must **exactly match** the commit author field
- Do **not** use GitHub noreply addresses (`@users.noreply.github.com`) —
  CI hard fails on these

### Attribution tags

Beyond `Signed-off-by`, use these standard tags where applicable:

| Tag | Meaning |
|---|---|
| `Acked-by:` | Approval from a code maintainer |
| `Reviewed-by:` | Formal technical review |
| `Tested-by:` | Confirmed working in some environment |
| `Reported-by:` | Credits the person who found the bug (with permission) |
| `Fixes: <sha> ("<subject>")` | Links to the commit that introduced a bug |

### AI-assisted commits

If you used AI assistance (e.g. GitHub Copilot, Claude) to write code or
the commit message, disclose it with a `Co-authored-by:` trailer:

```
Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>
Signed-off-by: Your Real Name <you@example.com>
```

The `Signed-off-by:` must still be a real human name. Submitting
AI-generated code without disclosure is grounds for rejection.

---

## Pull Requests

### Scope and structure

- **One topic per PR.** Do not bundle unrelated changes — a new device and
  an unrelated driver fix belong in separate PRs.
- **Atomic commits.** Each commit must be a self-contained logical change.
  Never have a later commit undo or partially revert an earlier one in the
  same PR — restructure the series instead.
- Keep the series small enough to review. Preparatory refactors (e.g.
  extracting a shared `.dtsi`) should be a **separate first commit** so the
  structural change is easy to review independently.

### No merge commits

Rebase your branch on top of `main` before submitting and after addressing
feedback:

```sh
git fetch origin
git rebase origin/main
git push --force-with-lease
```

Do **not** use the GitHub "Update branch" button — it creates merge commits
that CI will reject. Use `git rebase -i` to clean up the commit history.

### Draft / WIP PRs

Use the GitHub **Draft** state (or `[WIP]` in the title) while hardware
testing is still ongoing. Convert to ready-for-review only when the change
is complete and tested.

### File changes

- Verify there are no accidental file mode changes (`100644 → 100755`) in
  your diff — a common side-effect of certain editors.
- Do not modify files unrelated to your change.

### Hardware testing

For new device support, reviewers expect evidence of successful boot and
basic operation: boot log, `ip link show`, ping output, or similar. For
regression fixes, describe how you reproduced and verified the fix. For
changes affecting many platforms, serial console output is strongly
preferred.

### After addressing review

Ping the relevant maintainer explicitly once all feedback is addressed,
e.g. `ping @maintainer, all comments addressed`. Maintainers do the final
rebase before merge — you do not need to rebase again just before merge.

---

## Kernel Patches

### Upstream first

Send fixes and new drivers to upstream Linux **before or alongside**
submitting to OpenWrt. This applies to:

- General kernel subsystem patches
- mac80211 / cfg80211 patches
- mt76 patches (send to the `openwrt/mt76` upstream repo)
- Any driver that will appear in multiple platforms

When a fix is already queued for an upcoming kernel version (e.g. landing
in 6.18 naturally), a separate backport for that version may not be needed.

### Patch placement

| Patch status | Directory |
|---|---|
| Accepted upstream | `target/linux/generic/backport-<version>/` |
| Submitted upstream, not yet merged | `target/linux/generic/patches-<version>/` |
| Platform-specific, not upstreamable | `target/linux/<target>/patches-<version>/` |

When a new kernel version is added (e.g. 6.18), **all** existing patches in
`patches-<old>/` must also be added to `patches-<new>/`. When a pending
patch is accepted upstream, convert it from `patches-*/` to `backport-*/`.

Before adding a patch, check whether it already landed upstream. If so,
write a proper backport instead of copying the code.

If a driver fix applies to hardware from multiple SoC vendors, place it in
`target/linux/generic/` rather than a vendor-specific target directory.

### Backporting from upstream

Use the upstream commit message verbatim and append:

```
(cherry picked from commit <upstream-sha>)
```

### Kernel version bumps

Use `scripts/kernel_bump.sh` when porting target patches to a new kernel
version. Do not manually rename or move patch files — this breaks git
history for target-specific files.

---

## Backports to Stable Branches

Changes must first be merged to `main`, then backported as a **separate
PR** targeting the stable branch (e.g. `openwrt-25.12`):

```sh
git cherry-pick --signoff -x <commit-sha>
```

The `-x` flag appends `(cherry picked from commit <sha>)` automatically.

---

## Device Support (DTS / Platforms)

### DTS file location

Place DTS files in `target/linux/<arch>/dts/`, **not** inside patch files.
Reference them from the Makefile via `DEVICE_DTS`. This avoids patching
`Kconfig` and keeps DTS changes reviewable independently of driver patches.

Base device DTS on upstream `.dtsi` files where they exist rather than
duplicating nodes.

### DTS style

Follow the [kernel DTS coding style](https://docs.kernel.org/devicetree/bindings/dts-coding-style.html):

- Use the new array syntax for `reg` and similar properties
- Add a blank line after `/dts-v1/;` before `#include`
- Use consistent SPDX license identifiers across related `.dts`/`.dtsi`
  files in the same series
- Do not include `default-state = "off"` in LED nodes
- Use generic node names that reflect device function, not model number
- Remove deprecated `device_type` properties (except for `memory` and
  `cpu` nodes)

### Device variants with shared hardware

When a device comes in multiple storage variants (e.g. NAND and eMMC),
extract common nodes into a `<device>-common.dtsi` referenced by both
variant `.dts` files. Add the extraction as a **separate preparatory
commit** before the device-specific commits.

For NAND devices: set `KERNEL_IN_UBI := 1` in the Makefile profile.

### Device naming

Align `DEVICE_TITLE` and DTS filenames with existing naming conventions for
the target: lowercase, hyphens as word separators, `<vendor>_<model>` or
`<vendor>_<model>-<variant>`.

### MAC addresses

Use `nvmem` cells defined in DTS for MAC address assignment where possible,
rather than relying on randomised addresses at boot.

### Backwards compatibility

When renaming a device profile, add the old name to `SUPPORTED_DEVICES` so
existing installations can sysupgrade without reinstalling.

### Devices with known build problems

If a device profile exceeds its `KERNEL_SIZE` limit (CI warning: "Image
file is too big"), add `DEFAULT := n` to exclude it from buildbots while
the issue is investigated.

---

## Coding Style

### General

- Match the indentation style of the surrounding file (tabs or spaces
  consistently)
- Keep lines at most **80 characters**
- Sort list entries (package dependencies, device profiles, etc.)
  alphabetically
- Check kernel patches with `./scripts/checkpatch.pl`

### C code (kernel / drivers)

- Use `device_for_each_child_node_scoped` instead of
  `device_for_each_child_node` to avoid fwnode reference leaks on early
  return paths
- Remove dead code (unreachable statements after `return`)
- Comments must accurately describe the code — update them when behaviour
  changes
- Name variables to reflect their semantic role

### Shell / ucode scripts

- Keep shell and ucode code paths in sync: if you fix a bug in one, apply
  the equivalent fix in the other
- Do not set the execute bit on files that are not executable scripts

---

## Common Mistakes That Get PRs Rejected

| Mistake | Why it is rejected |
|---|---|
| Merge commit in PR history | CI hard fail; use `git rebase` |
| Empty commit body (only `Signed-off-by:`) | CI: "Commit message is missing" |
| Subject not matching `component: lowercase...` | CI regex hard fail |
| GitHub noreply email in `Signed-off-by` | CI hard fail |
| Subject line over 60 characters | CI hard fail |
| "This PR adds …" in commit body | Reads as PR description, not commit message |
| Accidental file mode changes (`+x`) | Flagged immediately in review |
| Bundling device support with unrelated driver fixes | Asked to split into separate PRs |
| DTS in patch files instead of `dts/` directory | Asked to move in review |
| Patch not ported to new kernel version | Reviewer will request it |
| Downstream-only patch that belongs upstream | Reviewer will request upstream submission |
| Commit N undoes part of commit N-1 in same PR | Asked to restructure the series |
| AI-generated code without disclosure | Grounds for rejection |
| Commit author does not match `Signed-off-by` | Reviewer will request a fix |
