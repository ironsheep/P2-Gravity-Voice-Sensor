# Project skill conventions

Slot values for the central skill set. See
`~/.claude/skills-docs/SKILLS-MAINT.md` for the full schema. Optional
slots whose defaults fit this project are omitted.

> **Greenfield note:** no `.spin2` source exists yet. `SPIN2_TOP_FILE`,
> the driver filename, and the `BUILD_*`/`TEST_*` commands reference
> *proposed* names (`src/isp_voice_recognizer.spin2` driver +
> `src/demo_voice_recognizer.spin2` top). Update them when the real files
> are created. Naming: `isp_` = drivers we ship, `demo_` = demos, `test_`
> = test harnesses (parallel role prefixes, not stacked).

---

## Identity

```yaml
USER_NAME:           Stephen
PROJECT_NAME:        P2-Gravity-Voice-Sensor
```

## Build & test

Declarative pnut-ts. Compile (`pnut-ts`) runs in **both** the container
and host-native. Flash + DEBUG run (`pnut-term-ts`) is **host-native
only** — the container has no download/run tools. The container-vs-host
split is a procedural delta documented in the per-skill overlays, not here.

```yaml
BUILD_COMMAND:           pnut-ts -d src/demo_voice_recognizer.spin2          # compile-only; container + host
TEST_COMMAND:            pnut-term-ts --headless -r src/demo_voice_recognizer.bin --end-marker --timeout 60   # host-native only
CANONICAL_TEST_TARGET:   P2 board wired to the DF2301Q, flashed over USB (host-native only)
```

## Build version

Version string lives as a constant in the driver object and is exposed
via `PUB version() : pStr`; the demo reads it back for display.
Version-aware skills grep `DRIVER_VERSION` in the driver file.

```yaml
BUILD_VERSION_LOCATION:  src/isp_voice_recognizer.spin2
BUILD_VERSION_KEY:       DRIVER_VERSION
BUILD_VERSION_EXAMPLE:   0.0.1
```

## Doc paths

Created on first use; only `DOCs/policy/` exists today.

```yaml
PLAN_DIR:           DOCs/plans/
PLAN_ARCHIVE_DIR:   DOCs/plans/archive/
ANALYSIS_DIR:       DOCs/analysis/
PUNCH_LIST_DOC:     DOCs/plans/PUNCH-LIST.md
RELEASE_NOTES_DOC:  DOCs/RELEASE-NOTES.md
SPEC_DOC:           DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md
```

## Audience & vocabulary

```yaml
RELEASE_NOTES_AUDIENCE:    P2 developers integrating the driver
TEST_FLEET_DESCRIPTION:    a P2 board wired to the DF2301Q voice sensor
```

## Tracking-readiness

```yaml
PROJECT_INIT_DATE:   2026-06-03
```

## P2 development cycle

Declarative path. `P2_WORK_DIR` is the repo root so `src/` stays clean
and logs land in `./logs/`. All other P2 slots use documented defaults
(baud 2000000, run timeout 60s, USB device auto-detect).

```yaml
P2_WORK_DIR:        .
SPIN2_TOP_FILE:     src/demo_voice_recognizer.spin2     # proposed name; no top .spin2 exists yet
```
