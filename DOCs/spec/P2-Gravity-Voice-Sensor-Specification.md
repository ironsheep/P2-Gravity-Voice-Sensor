# P2 Gravity Voice Sensor — Specification

**Object:** `isp_voice_recognizer.spin2` — P2 (Spin2) driver for the DFRobot DF2301Q
"Gravity: Offline Voice Recognition Sensor" (SKU SEN0539) over **I²C**. Build **0.1.0**.

This is the authoritative API/behavior specification. For *how it works internally* see
`DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md`; for the *device protocol* it ports see
`DOCs/reference/THEORY-OF-OPERATIONS.md`.

---

## 1. Overview

The DF2301Q is a self-contained **offline** speech-recognition module: it listens on a dual
microphone array, recognizes a spoken phrase from its ~150-word built-in vocabulary (plus
user-trained custom words), and exposes the result to the host as a small integer **command
ID (CMDID)**. It can also speak reply audio and be configured (volume / mute / wake
duration).

This driver presents that capability to P2 applications as an I²C object whose bus methods
are **non-blocking**, so the driver can be polled by a shared "device scanner" cog without
stalling it. The UART transport the device also offers is out of scope for this build.

## 2. Object & dependencies

```
  demo_voice_recognizer.spin2     top / interactive demo (TERM-window menu)
        v
  isp_voice_recognizer.spin2      THIS object
        v
  isp_i2c_singleton.spin2         shared bit-banged I²C bus (singleton)
```

The I²C layer is a **singleton** — one bus instance shared by every I²C driver in the
application, which is what makes the scanner-cog model viable.

## 3. Public API contract

All 14 public methods. "Blocks?" = whether the call waits on the bus/time; every method
here is non-blocking unless noted.

| Method | Returns | Blocks? | Behavior |
|--------|---------|---------|----------|
| `version()` | `pStr` | no | Pointer to the zero-terminated version string (`"0.1.0"`). |
| `start(scl, sda, khz, pullup)` | `bFound` | no¹ | Init the I²C bus on the given pins (`khz` = 100/400/1000; `pullup` = `i2c.PU_NONE/PU_1K5/PU_3K3/PU_15K`), probe address `$64`. Returns TRUE if the device ACKs, FALSE if absent. Call once before any other method. |
| `getCMDID()` | `cmdId` | no | Simple-profile alias of `pollCMDID()`. |
| `pollCMDID()` | `cmdId` | no | Latest recognized command ID; **0 = none**. Enforces ≥50 ms between actual bus reads via a tick check — if polled sooner, returns the cached value without touching the bus. The chip latch-clears on read. |
| `playByCMDID(cmdId)` | — | no² | Play the reply audio for `cmdId`. Fire-and-return: issues the write and returns; the ~1 s play window is reported by `isSpeaking()`, not waited on. |
| `isSpeaking()` | `bSpeaking` | no | TRUE while still within the ~1 s window opened by the last `playByCMDID()`. |
| `enterWakeState()` | — | no² | Put the module into its wake state via the play path. |
| `getWakeTime()` | `wakeSecs` | no | Read the configured wake-up duration (seconds). |
| `setWakeTime(wakeSecs)` | — | no | Set wake-up duration, 0–255 s. |
| `setVolume(volLevel)` | — | no | Set playback volume. Value passed through **without clamping** (see F2). |
| `setMuteMode(muteOn)` | — | no | Nonzero `muteOn` mutes, 0 unmutes (normalized to 1/0 for the device). |
| `startPoller()` | `ok` | no | Launch a background cog that polls and publishes to a mailbox. TRUE on success; FALSE if already running or no free cog. |
| `stopPoller()` | — | no | Stop the poller cog and release the bus. |
| `getLatest()` | `cmdId` | no | Non-blocking read of the poller's latest-CMDID mailbox; **0 = none since last read**. Cleared on read (latest-only). |

¹ `start()` performs one short probe transaction but does not wait on time.
² Issues one short bus write; the device's ~1 s audio playback happens asynchronously.

**Error / edge semantics:**
- `start()` returning FALSE means the device did not ACK — wiring or address fault.
- `pollCMDID()`/`getCMDID()`/`getLatest()` returning 0 means "nothing recognized," not an error.
- `startPoller()` returning FALSE: either already running (idempotent guard) or no free cog
  (`cogspin` returned −1).
- While the poller runs, the foreground must use `getLatest()` only — see §4.

## 4. Usage profiles & the bus-ownership rule

The driver supports three usage profiles over the same primitives; the demo selects one:

1. **Passive scanner-poll** (primary): a foreign cog that iterates over many devices calls
   `pollCMDID()` on its pass over this one. No driver-owned cog; one quick non-blocking read.
2. **Self-poller cog**: `startPoller()` runs a dedicated cog that polls and publishes to a
   mailbox; the foreground reads `getLatest()` non-blocking.
3. **Simple synchronous**: a foreground loop calls `getCMDID()` directly.

**Bus-ownership rule:** when the self-poller cog (profile 2) is running, **it owns the bus**.
Callers must read results via `getLatest()` only and must configure
`setVolume`/`setMuteMode`/`setWakeTime` **before** `startPoller()`. To reconfigure later:
`stopPoller()`, change settings, `startPoller()` again. Calling the synchronous bus methods
while the poller runs puts two cogs on one bus.

## 5. Timing guarantees

- **No `waitms` in any bus method** — safe to call from a shared scanner cog.
- **≥50 ms between actual CMDID reads**, enforced by a `GETCT` tick check inside
  `pollCMDID()` (not a busy-wait): a too-soon poll returns the cached value.
- **`playByCMDID()` is fire-and-return**; the ~1 s audio window is exposed via `isSpeaking()`
  (a tick comparison), never a stall.

## 6. DEBUG channel map

Tracing uses the P2 channel-based DEBUG facility (`{Spin2_v46}` + `DEBUG_MASK`). Each object
ships with its channel **off** (`DEBUG_MASK = 0`, zero code emitted); set the bit and rebuild
to trace. Channels are reserved project-wide:

| Channel | Owner | Enable in |
|--------:|-------|-----------|
| 0 | `isp_i2c_singleton` — I²C bus transactions (`DBG_I2C`) | `isp_i2c_singleton.spin2` |
| 1 | `isp_voice_recognizer` — recognized/play/config/start events (`DBG_VOICE`) | `isp_voice_recognizer.spin2` |

Both can be enabled independently in one build. Driver trace points: recognized CMDID
(non-zero reads), play issued, volume/mute/wake-time writes, and the `start()` probe result —
none inside a poll loop.

## 7. Public command-word IDs

The driver's `{Spin2_Doc_CON}` block names the **full built-in catalog** as `CMD_*` constants:
the sentinel/wake words (`CMD_NONE`=0, `CMD_WAKE_LEARN`=1, `CMD_HELLO_ROBOT`=2), the custom slots
(`CMD_CUSTOM_1`..`CMD_CUSTOM_17`, IDs 5–21), the ~120 built-in fixed commands
(`CMD_GO_FORWARD`=22 … `CMD_CLOSE_THE_DOOR`=142), and the learning/delete control words (200–208).
Applications **react by ID** via `voice.<NAME>` — e.g. `case id: voice.CMD_RETREAT:`. Constants
cost nothing unless referenced.

For the **human-readable phrase**, include the optional object `isp_voice_command_names` and call
`names.cmdName(cmdId) : pStr` (returns e.g. `"Retreat"`; `"(custom)"` for 5–21, `"(unknown)"`
otherwise). It is a *separate* object so its string table is compiled in **only when included** —
react-by-ID apps don't pay for it.

IDs and phrases are ported from `DFRobot_DF2301Q_Commands.py`. **Validate against the product's
printed command-word card on hardware** (#9) — firmware revisions have reshuffled lists. Full table
also in `DOCs/reference/THEORY-OF-OPERATIONS.md` §5.

## 8. Bring-up determinations (resolved on hardware — task §9)

Two values cannot be settled without the physical module; until then the driver uses the
noted placeholders:

- **F1 — wake CMDID.** Which CMDID `enterWakeState()` plays to wake the module is ambiguous
  in the reference (HelloRobot=2 vs WakeUpWordsForLearning=1). Current placeholder:
  `CMD_HELLO_ROBOT` (2). To be confirmed on hardware and recorded here.
- **F2 — volume range.** Documented 1–7 but the reference's dead clamp implies a wider range
  (~0–20). `setVolume()` therefore does **not** clamp. True accepted range to be confirmed on
  hardware and recorded here.

## 9. Related documents

- `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` — internal design and rationale.
- `DOCs/reference/THEORY-OF-OPERATIONS.md` — DF2301Q device protocol and reference library
  (register map, command-word table, findings F1–F7).
- `DOCs/plans/VOICE-RECOGNIZER-DRIVER-SPRINT-PLAN.md` — the build that produced 0.1.0.
