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
stalling it.

**In scope (v0.1.0):** full I²C register control with a capability-named public method for
everything the I²C interface can do (§3.1); the three usage profiles (§4); a configurable
power-on volume with a driver-side volume shadow; an interactive DEBUG PLOT "front panel" demo.

**Out of scope (v0.1.0):** the device's **UART** transport (module reset, OTA, version detail,
audio play start/pause/resume/stop, wakeup-enter/exit notifications) — a future widening of this
same interface (`DOCs/PUNCH-LIST.md`); on-device enrollment of custom command words (done through
the module's own voice-UI, not I²C); an optional shared-bus lock (deferred, punch-list).

## 2. Object & dependencies

```
  demo_voice_recognizer.spin2     top / interactive demo ({Spin2_v50} DEBUG PLOT panel)
        v
  isp_voice_recognizer.spin2      THIS object
        v
  isp_i2c_singleton.spin2         shared bit-banged I²C bus (singleton)
```

The I²C layer is a **singleton** — one bus instance shared by every I²C driver in the
application, which is what makes the scanner-cog model viable.

## 3. Public API contract

All 15 public methods. "Blocks?" = whether the call waits on the bus/time; every method
here is non-blocking unless noted.

**Return convention** (per `DOCs/policy/SPIN2-AUTHORING-GUIDE.md`): *action* methods that write
the device return a status **code** — `E_OK` (0) on success, `E_NAK` (−1) if the device did not
acknowledge a bus byte. *Value* queries (`getCMDID`/`getVolume`/`getWakeTime`) return their value
(0 = "none recognized" is a value, not an error). *Presence* queries (`start`/`startPoller`) are
boolean-by-nature and return TRUE/FALSE.

| Method | Returns | Blocks? | Behavior |
|--------|---------|---------|----------|
| `version()` | `pStr` | no | Pointer to the zero-terminated version string (`"0.1.0"`). |
| `start(scl, sda, khz, pullup)` | `bFound` | no¹ | Init the I²C bus on the given pins (`khz` = 100/400/1000; `pullup` = `i2c.PU_NONE/PU_1K5/PU_3K3/PU_15K`), probe address `$64`. On success, applies `DEF_VOLUME` so the volume shadow is seeded. Returns TRUE if the device ACKs, FALSE if absent. Call once before any other method. |
| `getCMDID()` | `cmdId` | no | Simple-profile alias of `pollCMDID()`. |
| `pollCMDID()` | `cmdId` | no | Latest recognized command ID; **0 = none**. Enforces ≥50 ms between actual bus reads via a tick check — if polled sooner, returns the cached value without touching the bus. The chip latch-clears on read. |
| `playByCMDID(cmdId)` | — | no² | Play the reply audio for `cmdId`. Fire-and-return: issues the write and returns; the ~1 s play window is reported by `isSpeaking()`, not waited on. |
| `isSpeaking()` | `bSpeaking` | no | TRUE while still within the ~1 s window opened by the last `playByCMDID()`. |
| `enterWakeState()` | — | no² | Put the module into its wake state via the play path. |
| `getWakeTime()` | `wakeSecs` | no | Read the configured wake-up duration (seconds). |
| `setWakeTime(wakeSecs)` | — | no | Set wake-up duration, 0–255 s. |
| `setVolume(volLevel)` | — | no | Set playback volume **and update the volume shadow**. Value passed through **without clamping** (see F2). |
| `getVolume()` | `volLevel` | no | Current volume from the driver's **shadow** (last value written; seeded by `DEF_VOLUME` at `start()`). `SET_VOLUME` is write-only in silicon, so this is the commanded value, not a device read. |
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

### 3.1 Register coverage & transport architecture

**Design principle:** *every capability the device exposes is reachable through a high-level,
capability-named public method.* The user reads and writes **values through named methods**, never
through register numbers — how a call transports to the device (which register, what framing) is an
internal detail and is **not** part of the public surface. Raw register read/write
(`readReg`/`writeReg`) is deliberately **private**.

The I²C interface is **fully covered** — all five registers have a public representative:

| Register | Dir | Public representative(s) |
|----------|-----|--------------------------|
| `0x02` CMDID | read | `getCMDID()` / `pollCMDID()` / `getLatest()` |
| `0x03` PLAY_CMDID | write | `playByCMDID()` / `enterWakeState()` |
| `0x04` SET_MUTE | write | `setMuteMode()` |
| `0x05` SET_VOLUME | write | `setVolume()` / `getVolume()` (shadow) |
| `0x06` WAKE_TIME | read/write | `getWakeTime()` / `setWakeTime()` |

`SET_MUTE` and `SET_VOLUME` are **write-only in silicon** — the chip will not report those values
back over the bus. **Requirement (volume shadow):** because knowing the current volume makes both
the driver's users and the test interfaces materially better, the driver **SHALL** maintain a
**volume shadow** — it applies a driver-configurable default (`DEF_VOLUME`) at `start()`, updates
the shadow on every `setVolume()`, and exposes it via `getVolume()`. The shadow reflects the value
the driver last commanded (authoritative as long as all volume changes go through the driver), not
a device read-back. The same shadow pattern MAY later be applied to mute. There is **no I²C
"stop-listening" / sleep capability**: the module is an always-on wake-word listener and the wake
*state* simply auto-expires after `WAKE_TIME` seconds. A demo "Stop" therefore stops *polling*, not
the device.

**Transport roadmap (interface width):** the driver is **I²C-only** today. The DF2301Q's second
transport, **UART** (9600 8N1), exposes capabilities I²C does not — module reset, OTA, detailed
version queries, audio **play start/pause/resume/stop**, and event **notifications** including
*wakeup-enter* / *wakeup-exit* (which would make the wake state observable in real time). Bringing
up UART later **widens this same public interface** with additional capability-named methods,
mirroring the reference's two-class split (an I²C class and a UART class). Tracked in
`DOCs/PUNCH-LIST.md`.

### 3.2 Device-protocol requirements (hard rules for the bus layer)

- **Clock-stretching MUST be honored.** The DF2301Q holds SCL low after an ACK while it prepares
  to be read; a master that does not wait for SCL to rise produces malformed repeated-STARTs and
  all-zero reads. `isp_i2c_singleton`'s `start()`, `stop()`, and `read()` therefore wait (bounded
  by `STRETCH_LIMIT`) for SCL to read high before proceeding. This is a **requirement, not an
  optimization** — the original singleton had clock-stretch support *removed*, which is exactly
  what broke register reads during bring-up. Do not remove it.
- **Register read framing.** Reads use a write-of-the-register-pointer then a **repeated-START**
  to the read address (no intervening STOP), matching the reference (`endTransmission(false)`).
- **Pull-up posture.** The driver drives no assumptions about external pull-ups; the caller picks
  the P2 internal pull-up via `start(..., pullup)`. On a no-external-parts bench, `PU_1K5`
  (1.5 kΩ) is required — the weaker `PU_3K3` (1 mA) idles the bus low.

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

## 9. Test strategy

Two tracks: a one-time bottom-up bring-up that proves the hardware layer by layer (and retires
the §8 unverified facts), and a repeatable regression top for the automatable subset.

| Layer | Proves | Retires | Auto? |
|-------|--------|---------|-------|
| L0 Bus presence | device ACKs at `$64` (wiring, pull-ups, address) | pull-up choice (`PU_1K5`) | yes (ACK probe) |
| L1 Register read | `WAKE_TIME` write→read round-trip returns the written value → **clock-stretch + read framing** | clock-stretch handling, read framing | yes |
| L2 Register write + shadow | volume/mute/wake-time writes ACK; `getVolume()` tracks `setVolume()` | volume-shadow correctness | yes |
| L3 Recognition decode | spoken wake word + command → correct CMDID over I²C; phrase via `cmdName()` | catalog ID↔phrase mapping | manual (needs voice) |
| L4 Usage profiles | Sync / Scanner / Poller each deliver CMDIDs; clean `stopPoller`; profile switches never hang | bus-ownership handoff | partial |
| F1 / F2 | wake CMDID; real volume range | §8 placeholders | manual |

**Regression top (`src/test_voice_recognizer.spin2`, TODO):** the automatable subset of L0–L2 —
bus ACK, `WAKE_TIME` write→read round-trip, volume-shadow round-trip — emitting pass/fail to the
log so every change can re-verify against hardware. L3/L4/F1/F2 stay a manual playbook (need
spoken input). The regression top names anything it could not exercise (no silent coverage gaps).

**Compile-clean baseline (container):** `pnut-ts -d` compiles the demo top (and, once it exists,
the regression top); an in-container "failure" is a non-compiling object — behavioral health is the
on-hardware work above.

## 10. Non-functional requirements

- **NFR-1 Authoring-guide conformance.** Every `.spin2` file follows `DOCs/policy/SPIN2-AUTHORING-GUIDE.md`
  (named constants, error-code returns, doc-comments, ASCII-only).
- **NFR-2 Dual-environment.** Compile in the container; flash/run on the macOS host
  (`pnut-term-ts -r … -b 2000000`). The driver assumes no runtime tool the container lacks.
- **NFR-3 Reuse / portability.** Self-contained, dependency-light (driver + I²C singleton +
  optional names catalog) so it drops into a robot's sensor mix. Host **flexspin** compat check is
  a punch-list item.
- **NFR-4 Documentation parity.** Public methods carry doc-comments; this spec tracks the API.

## 11. Deliverables

1. `src/isp_voice_recognizer.spin2` — the driver (`version()` → `"0.1.0"`).
2. `src/isp_voice_command_names.spin2` — optional ID→phrase catalog.
3. `src/demo_voice_recognizer.spin2` (+ `tools/gen_panel_assets.py` + `panel_*.bmp`) — the DEBUG
   PLOT front-panel demo.
4. `src/test_voice_recognizer.spin2` — the regression top (§9). *(TODO)*
5. This specification + `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` + `DOCs/PUNCH-LIST.md`.

## 12. Acceptance (v0.1.0)

- Driver compiles clean under pnut-ts (container).
- Every I²C capability has a public representative (§3.1); raw register access stays private.
- Reads proven on hardware (`WAKE_TIME` write→read round-trip).
- Real spoken commands produce correct CMDIDs over I²C, surfaced on the demo panel.
- F1 (wake CMDID) and F2 (volume range) resolved on hardware and recorded in §8.
- Demo renders and operates all rows — modes, bring-up, HEARD line, SPEAK row.

## 13. Related documents

- `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` — internal design and rationale.
- `DOCs/reference/THEORY-OF-OPERATIONS.md` — DF2301Q device protocol and reference library
  (register map, command-word table, findings F1–F7).
- `DOCs/plans/VOICE-RECOGNIZER-DRIVER-SPRINT-PLAN.md` — the build that produced 0.1.0.
