# Changelog Style Guide

Style conventions for P2-Gravity-Voice-Sensor changelog entries.

---

## Core Principles

1. **Terse over verbose** - State what changed, not why it was wrong
2. **Additive framing** - Focus on what the driver NOW provides, not what was broken before
3. **User-focused** - Include only changes users care about
4. **No implementation details** - Omit root causes, debugging info, internal processes
5. **Aggregate corrections** - Group related fixes into themes rather than itemizing each one

---

## What to Include

- API changes (new methods, changed signatures, changed return values)
- Bug fixes affecting driver behavior (recognition results, error handling, I2C timing)
- New compile-time DEBUG channels or configuration constants users would set
- Performance improvements users would notice (e.g. poll spacing, non-blocking behavior)
- New or expanded regression test coverage
- Breaking changes (removed methods, renamed APIs, changed CMD_* or status constants)

## What to Exclude

- Internal refactoring (method reordering, PRI renames, code style)
- Root cause explanations
- Before/after comparisons (just state current state)
- Internal process notes and debugging details
- Build tooling and release-packaging changes (workflow, build-check, generator scripts)
- Internal regressions fixed before release
- Comment and documentation-only changes within source files

**The Exclusion Test:** Ask "Would a user of this driver have been affected by or need to know about this change?" If no, exclude it.

---

## Framing Corrections

Changelogs should communicate strength, not confess weakness. Users want to know what they're getting, not what was broken.

### Aggregate into Themes

Instead of listing each correction, summarize the improvement:

```markdown
# Bad - itemizes each problem
- Fixed getCMDID() returning a stale value when polled too soon
- Fixed getCMDID() not enforcing the 50 ms read spacing
- Fixed getCMDID() missing the clock-stretch wait

# Good - describes the result
- getCMDID(): Recognition reads verified across poll-timing edge cases
```

### Use Additive Language

Describe what exists now, not what changed:

```markdown
# Bad - highlights the error
- Corrected: registerCustomTable() was storing object-relative pointers that did not resolve
- Removed broken @phrase pointer-table path

# Good - states current reality
- registerCustomTable(): Custom phrases resolved from a single absolute table pointer
- (don't mention removed code - users never saw it)
```

### Section Structure for Mixed Releases

When a release has both new features and fixes:

```markdown
## vX.Y.Z (YYYY-MM-DD)

**Release Theme**

### New Features
- Bullet list of additions

### Bug Fixes
- Summary lines covering corrections

### Tests
- New or expanded test coverage (if significant)
```

---

## Entry Format

### Simple Fixes

```markdown
- method(): Brief description of fix
```

Examples:
- `pollCMDID(): Cached value returned when polled inside the 50 ms window`
- `setVolume(): Shadow updated so getVolume() reflects the last set level`
- `start(): FALSE returned when the module does not acknowledge at $64`

### Grouped Fixes

```markdown
**Category Name:**
- method1(): Fix description
- method2(): Fix description
```

### New Features

```markdown
- method(): Added [what it does]
```

Examples:
- `setWakeTime(): Set the module's wake-state duration in seconds`
- `cmdName(): Return the human phrase for a recognized command ID`

### New DEBUG Channels / Config Constants

```markdown
- DBG_CHANNEL: Enables [capability summary]
```

Example:
- `DBG_VOICE: Enables compile-time tracing of recognitions and config writes`

### Breaking Changes

```markdown
- BREAKING: method() [what changed]
```

Examples:
- `BREAKING: startPoller() now returns a status code instead of a boolean`
- `BREAKING: getCMDID() renamed (use pollCMDID())`

---

## Section Structure

```markdown
## vX.Y.Z (YYYY-MM-DD)

**Release Theme** - One-sentence summary.

### New Features
- New public API methods or DEBUG channels

### Improvements
- Enhancements to existing functionality

### Bug Fixes
- Corrections to driver behavior

### Breaking Changes
- API changes that require user code updates

### Tests
- Significant new test coverage (optional, for major additions)
```

Omit any section that has no entries for a given release.

The version heading (`## vX.Y.Z (YYYY-MM-DD)`) is the project's **version of record** and is
parsed by the release workflow. It must match the driver's `version()` string and the git tag;
keep the format exactly so the parser and the three-way version lock keep working.

---

## Length Guidelines

| Entry Type | Target Length |
|------------|---------------|
| Simple fix | 5-10 words |
| With detail | 10-20 words |
| Maximum | 25 words |

Parenthetical explanations: 10 words maximum.

---

## Examples

### Good (Terse)

```markdown
- setWakeTime(): Public API for the module's wake-state duration
- pollCMDID(): Non-blocking, 50 ms read spacing enforced internally
- Poller cog: Dedicated cog mailbox keeps the scanner cog from stalling on the bus
```

### Bad (Verbose)

```markdown
- **pollCMDID()**: Added new PUB method that reads register 0x02 over I2C but only
  every 50 ms because the DF2301Q needs that spacing or polling starves the module,
  and it uses a repeated-START so no STOP is issued between the register write and
  the data read which would otherwise break the transaction
- **registerCustomTable()**: Fixed the custom-word path that was using @phrase pointers
  storing object-relative offsets that the names object could not resolve across object
  bases, switched to an inline single-pointer table, and updated all callers
```

---

## Reference

Model changelog: v1.0.0 section in CHANGELOG.md
