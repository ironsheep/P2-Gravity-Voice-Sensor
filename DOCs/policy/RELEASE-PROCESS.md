# Release Process

How to cut a release of this driver. The repository cannot build remotely, so **the build gate
is local**: you certify the code compiles, then push a tag, and a GitHub Actions workflow packages
and publishes the downloadable bundles. Releases are cheap to make but **public and awkward to
unpublish** — work through this checklist in order; do not skip the audit.

---

## The version of record (three-way lock)

One version number lives in **three** places and they must be identical for a release to publish:

| # | Where | Form |
|---|-------|------|
| 1 | `CHANGELOG.md` — top heading | `## vX.Y.Z (YYYY-MM-DD)` |
| 2 | `src/isp_voice_recognizer.spin2` — `DRIVER_VERSION` | `byte "X.Y.Z", 0` |
| 3 | The git tag | `vX.Y.Z` |

`tools/build-check.sh` verifies (1)==(2) locally; `.github/workflows/release.yml` re-verifies
(1)==(2)==(3) in CI and **refuses to publish on any drift**. Version strings *quoted in docs*
(USER-GUIDE, spec, design) are not parsed but must be updated too — the audit step below catches them.

Versioning is [SemVer](https://semver.org/). Changelog entries follow
[`changelog-style-guide.md`](changelog-style-guide.md).

---

## Procedure

### 1. Documentation audit — bring every public-facing doc current
Before touching version numbers, confirm the docs describe **what the driver actually does now**, not
what it did or was planned to do. Public-facing = anything that ships in a release bundle or the
auto-attached source archive. Audit at minimum:

- [ ] `README.md` — status, capability list, transport scope (this driver is **I2C-only**), repo
      layout, and any "will / planned / greenfield" language that has since shipped.
- [ ] `DOCs/USER-GUIDE.md` — method table, profiles, and the version string in §4.
- [ ] `DOCs/COMMAND-CATALOG.md` — regenerate if `tools/cmdname_catalog.tsv` changed
      (`python3 tools/gen_cmdname_table.py --catalog-md`).
- [ ] `DOCs/spec/…` and `DOCs/design/…` — API tables, status banners, version mentions.
- [ ] `DOCs/reference/…` and any guide docs — still accurate against the code.

Fix anything stale **in this release's commit** — docs and code ship together.

### 2. Update the changelog
Add a new `## vX.Y.Z (YYYY-MM-DD)` section at the top of `CHANGELOG.md`, written per the style guide
(terse, additive, method-focused; exclude tooling and doc-only churn).

### 3. Bump the driver version
Set `DRIVER_VERSION` in `src/isp_voice_recognizer.spin2` to `X.Y.Z`, and update the version string
quoted in the docs (`grep -rn 'X\.Y\.Z'` of the *previous* version finds them all).

### 4. Certify the build (the gate)
Run `tools/build-check.sh`. It must print **GREEN**: every source object compiles, both bundles
compile in their flat layout, and the in-tree version halves match. **Red blocks the release.**

### 5. Commit
Commit the code + doc changes together with a clean message. The working tree must be **clean at
tag time** — the auto-attached "Source code" archive is `git archive` of the tag, so anything
uncommitted is simply absent from that asset. Do **not** sweep in unrelated or
hardware-unverified work; hold it for a later release.

### 6. Tag and push
```
git tag vX.Y.Z          # must equal the CHANGELOG heading
git push                # push the commit first
git push --tags         # pushing the v* tag fires the release workflow
```

### 7. Verify the published release
The workflow enforces the three-way lock, then creates the GitHub Release with this version's
changelog section as the notes and uploads:
- `Voice-Sensor-X.Y.Z.zip` — integration kit (driver + i2c + names + example + guide + catalog)
- `Voice-Sensor-demo-X.Y.Z.zip` — superset with the demo app, artwork, docs, and tools
- `Source code (zip/tar.gz)` — attached automatically by GitHub; the complete repo at the tag
  (tests included). We do **not** build a separate tests bundle.

Open the release page and confirm all three assets are present and the version is correct.

---

## If something is wrong after publishing
Prefer rolling **forward** (a new patch release) over deleting a published tag. If you must pull a
release, delete the GitHub Release and its tag, fix, and re-tag — but assume someone may already
have downloaded the assets.
