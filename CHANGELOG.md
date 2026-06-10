# Changelog

Notable changes to the P2 DF2301Q Voice Sensor driver. Entry style follows
`DOCs/policy/changelog-style-guide.md`.

This file is the **version of record**: the top version here must match the driver's internal
`version()` string (`DRIVER_VERSION` in `src/isp_voice_recognizer.spin2`) **and** the git tag
(`vX.Y.Z`). The release workflow refuses to publish if any of the three drift.

## v1.0.0 (2026-06-10)

**First public release of the I2C voice-recognition driver.**

### New Features
- `getCMDID()` / `pollCMDID()`: Non-blocking poll for the recognized command ID
- `playByCMDID()`: Play the module's reply audio for a command ID
- `setVolume()` / `setMuteMode()` / `setWakeTime()`: Configure playback and wake duration
- Three usage profiles: scanner-poll, self-poller cog (`startPoller`/`getLatest`), synchronous
- `cmdName()`: ID→phrase lookup via the optional `isp_voice_command_names` object
- `registerCustomTable()`: Register an application's custom words for slots 5–21
- `CMD_*` constants for the full built-in command-word vocabulary

### Tests
- `cmdName()` custom-table round-trip test
