# Sprint Plan — ISP Voice Recognizer Driver + Demo

**Deliverable:** a working P2 Spin2 driver `src/isp_voice_recognizer.spin2` for the DFRobot
DF2301Q voice sensor over **I²C**, plus `src/demo_voice_recognizer.spin2`, the formal
specification, and current documentation.

**Scope (confirmed):** full — all three usage profiles (passive scanner-poll, self-poller cog,
simple synchronous) in one sprint; self-poller hands results to the foreground via a **latest-CMDID
mailbox**; the demo selects the profile through a **runtime menu in a DEBUG window**; the
**specification document is authored** this sprint.

**Foundations already in place:**
- I²C layer `src/isp_i2c_singleton.spin2` — bit-banged singleton, API verified, compiles under
  `pnut-ts -d`. Key entry points: `setup` (`isp_i2c_singleton.spin2:110`), `present` (`:156`),
  `start` (`:176`), `write` (`:198`), `read` (`:276`), `wr_block` (`:235`), `rd_block` (`:314`),
  `stop` (`:360`). Constants `ACK`/`NAK` and `PU_*` at `:33–34`.
- Device protocol & constants — `DOCs/reference/THEORY-OF-OPERATIONS.md` (from
  `REF/DFRobot_DF2301Q-master/`). Register map in `REF/.../DFRobot_DF2301Q.h:27–34`; command-word
  IDs in `REF/.../python/circuitpython/DFRobot_DF2301Q_Commands.py`.
- Driver design — `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` (this plan implements it).
- Channel-based DEBUG pattern proven in the I²C layer (`isp_i2c_singleton.spin2:31` CON block,
  `record`/`report` at `:58`/`:64`).

There are **no blocking open questions.** Two values are determined empirically at bring-up (§9):
the wake-state CMDID (reference finding **F1**) and the true volume range (**F2**).

---

## Sprint start record (2026-06-03)

- **Outgoing build:** `0.1.0` — will be `DRIVER_VERSION` in `src/isp_voice_recognizer.spin2` (§1).
- **Working tree:** the I²C foundation `src/isp_i2c_singleton.spin2` and this plan were committed
  at sprint start (they were untracked); the sprint builds from a committed state.
- **Tracking-readiness (entry):** READY — 0 todo-mcp tasks, 0 context keys, `MEMORY.md` ~6 lines.
  Nothing to archive or prune.
- **Baseline-health (entry):** clean. `isp_i2c_singleton.spin2` compiles under `pnut-ts -d` with
  **0 warnings**; the top-level target `demo_voice_recognizer.spin2` does not exist yet (greenfield);
  no automated test suite (verification is compilation + on-hardware), no skips. This is the entry
  baseline closeout compares against.

---

## 1. Driver object skeleton, constants, and version

**Why.** Everything else builds on a correct constant set and object frame. The part-number
constants must be ported verbatim rather than re-derived.

**Starting point.** File does not exist. Port from `REF/.../DFRobot_DF2301Q.h:27–34` and the
command-word enum; structure per `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` §2, §5.

**Target.**
- `{Spin2_v46}` directive (consistent with the I²C layer; needed if the driver uses channel DEBUG).
- `CON`: `DEV_ADDR = $64`, derived `DEV_WR = $C8` / `DEV_RD = $C9`; register indices
  `REG_CMDID=$02`, `REG_PLAY_CMDID=$03`, `REG_SET_MUTE=$04`, `REG_SET_VOLUME=$05`,
  `REG_WAKE_TIME=$06`; a documentation `{Spin2_Doc_CON}` block of public command-word IDs (at least
  `CMD_NONE=0` and the wake-related IDs) for consumers.
- `DRIVER_VERSION` string constant and `PUB version() : pStr` (per `.claude/skill-conventions.md`
  Build version; start at `0.0.1`). Demo reads it back for display.
- `OBJ i2c : "isp_i2c_singleton"`.
- `VAR` instance state: bus pins, last-read tick, cached CMDID, speak-until tick, poller cog id +
  mailbox long (see §4).

**Integration.** Consumed by §2–§6; `version()` displayed by §5.

**Verification.** Normal: object compiles standalone under `pnut-ts -d`. Edge: derived
`DEV_WR`/`DEV_RD` equal `$C8`/`$C9`. Error: no constant collides with a Spin2/PASM2 reserved word
(authoring-guide Rule).

---

## 2. I²C register access layer (writeReg / readReg / begin)

**Why.** The DF2301Q is register-then-byte with a **repeated-START** read; getting this exactly
right is the crux of the whole driver.

**Starting point.** `isp_i2c_singleton` primitives cited above; mapping defined in
`DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` §8.2.

**Target.**
- `PRI writeReg(reg, val)` → `i2c.start; i2c.write(DEV_WR); i2c.write(reg); i2c.write(val); i2c.stop`.
- `PRI readReg(reg) : val` → `start; write(DEV_WR); write(reg); start (repeated); write(DEV_RD);
  val := read(NAK); stop`. **No STOP between the register write and the data read.**
- `PUB start(sclPin, sdaPin, khz, pullup) : ok` → `i2c.setup(...)` then probe `i2c.present(DEV_WR)`
  (+`i2c.stop`); return present/absent. (Method named to avoid colliding with `i2c.start`.)

**Integration.** Sole bus path for §3; reused unchanged by the poller cog in §4.

**Verification.** Normal: `readReg(REG_WAKE_TIME)` returns the value last written by
`setWakeTime`. Edge: reading `REG_CMDID` with nothing recognized returns 0. Error: absent device →
`start()` returns false (probe NAK). Bus-trace (I²C DEBUG channel 0) shows
`start/write($C8)/write($02)/start/write($C9)/read/stop` with **no intervening stop** on reads.

---

## 3. Synchronous primitives & non-blocking timing

**Why.** The driver must never block its caller (the scanner-cog requirement); the reference's
`delay(50)`/`delay(1000)` are replaced by tick-checks.

**Starting point.** Reference behavior in `DOCs/reference/THEORY-OF-OPERATIONS.md` §3.4;
non-blocking rules in `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` §4.

**Target.**
- `PUB pollCMDID() : id` — if `GETCT() - lastReadTick` < 50 ms, return cached id (or 0) **without a
  bus transaction**; else `readReg(REG_CMDID)`, stamp `lastReadTick`, cache, return. No `waitms`.
- `PUB getCMDID() : id` — simple-profile alias of `pollCMDID()` (same non-blocking body).
- `PUB playByCMDID(id)` — `writeReg(REG_PLAY_CMDID, id)`; set `speakUntilTick := GETCT() + 1 s`;
  return immediately. **No 1 s stall.**
- `PUB isSpeaking() : flag` — `GETCT() - speakUntilTick` sign test.
- `PUB getWakeTime() : secs` / `PUB setWakeTime(secs)` — `readReg`/`writeReg` `REG_WAKE_TIME`.
- `PUB setVolume(vol)` — `writeReg(REG_SET_VOLUME, vol)`, **no hard clamp** (ref F2).
- `PUB setMuteMode(onOff)` — `writeReg(REG_SET_MUTE, onOff <> 0)`.
- `PUB enterWakeState()` — programmatic wake via the play path; exact CMDID constant resolved in §9
  (ref F1). Named method so callers never hardcode the magic ID.

**Integration.** Called directly in profiles 1 and 3; called by the poller cog in §4.

**Verification.** Normal: spoken command → `pollCMDID()` returns its ID once, then 0 (latch-clear).
Edge: two `pollCMDID()` calls < 50 ms apart cause exactly one bus transaction (verify via I²C
trace). Error: `playByCMDID` followed immediately by `isSpeaking()` returns true, then false after
~1 s, with the caller never blocked. `setWakeTime(n)`/`getWakeTime()` round-trips for n at 0, 1, 255.

---

## 4. Self-poller cog + latest-CMDID mailbox

**Why.** Profile 2 — standalone non-blocking use without an external scanner.

**Starting point.** `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` §3 (profile 2) and §6
(bus-ownership rule).

**Target.**
- `PUB startPoller() : ok` — launch a Spin2 cog (`cogspin`) running a `PRI pollerTask()`; store the
  cog id; return ok/fail (no free cog). Idempotent guard: refuse if already running.
- `PRI pollerTask()` — loop: `pollCMDID()`; if non-zero, write it to the **mailbox long** (hub);
  pace with a tick-delay so it honors the 50 ms spacing. This is the **only** place blocking-style
  waiting is allowed, because it is the poller's own cog.
- `PUB getLatest() : id` — non-blocking read of the mailbox; clear to 0 on read (latest-only
  semantics, matching the chip's own latch).
- `PUB stopPoller()` — `cogstop` the poller, mark stopped.
- **Bus-ownership contract** documented at the methods: while the poller runs it owns the bus;
  callers use `getLatest()` only and configure (`setVolume`/`setMuteMode`/`setWakeTime`) **before**
  `startPoller()`.

**Integration.** Mailbox long in §1 `VAR`; reuses §3 `pollCMDID`.

**Verification.** Normal: with the poller running, `getLatest()` returns recognized IDs while the
foreground does unrelated work (LED toggle) without stalling. Edge: no command → `getLatest()`
returns 0; reading twice returns the id once then 0. Error: second `startPoller()` while running is
refused (no second cog, no double bus owner); `stopPoller()` then `getCMDID()` from foreground works
again (bus released).

---

## 5. Demo with runtime DEBUG-window menu

**Why.** Exercises and demonstrates all three profiles from a single flashed build.

**Starting point.** Top-file slot `src/demo_voice_recognizer.spin2`
(`.claude/skill-conventions.md` SPIN2_TOP_FILE). No file exists.

**Target.**
- A clearly-marked **wiring config CON** (SCL pin, SDA pin, bus kHz, pull-up choice) the user edits
  for their board — documented defaults (e.g. 100 kHz), not assumed correct for every wiring.
- `start()` the driver; on failure, print a connection error and retry (mirrors reference setup).
- Display `version()` and a menu in a **DEBUG terminal window**; read selection via `PC_KEY()`:
  1. **Simple synchronous** — loop `getCMDID()`, print non-zero IDs.
  2. **Passive scanner-poll** — simulate a scanner cog: each pass call `pollCMDID()` among other
     (stub) "device" reads, print non-zero IDs, demonstrating the non-blocking spacing.
  3. **Self-poller cog** — `startPoller()`, then loop `getLatest()` while blinking an LED to show
     the foreground stays responsive; menu key stops the poller.
- A startup `playByCMDID(...)` sign-of-life and `setVolume`/`setMuteMode`/`setWakeTime` config
  before entering profiles (and, for profile 3, before `startPoller()` per the contract).

**Integration.** Top object; compiles the whole tree (`demo → isp_voice_recognizer → isp_i2c_singleton`).

**Verification.** Normal: each menu choice runs its profile and reports CMDIDs from real speech.
Edge: switching from profile 3 back to the menu cleanly `stopPoller()`s (bus released, no hang).
Error: with the sensor unplugged, `start()` reports the connection failure rather than faulting.

---

## 6. Channel-based DEBUG in the driver

**Why.** Driver-level tracing consistent with the I²C layer, without sitting in any timing path.

**Starting point.** Pattern in `isp_i2c_singleton.spin2:31–`; allocation table in
`DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` §7.

**Target.**
- Driver owns **DEBUG channel 1** (`DBG_VOICE`), per the reserved allocation; ship `DEBUG_MASK = 0`.
- Trace at semantic boundaries only (recognized id, play issued, config writes) — outside any tight
  loop. Driver bus calls already get I²C-level tracing from channel 0 when that mask bit is set.
- Confirm channels 0 (I²C) and 1 (voice) can be enabled independently in one build without collision.

**Verification.** Normal: `DEBUG_MASK = (1<<DBG_VOICE)` compiles voice trace in; `0` compiles it out
(binary-size delta, as proven for the I²C layer). Edge: enabling both channels 0 and 1 builds and
runs. Error: no `debug[...]` appears inside a poller-pace or bit-timing loop.

---

## 7. Specification document

**Why.** Confirmed deliverable: a formal spec at the `SPEC_DOC` slot.

**Starting point.** `DOCs/spec/` does not exist. Source material: the two theory-of-ops docs and the
final public API from §1–§6.

**Target.** Author `DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md` covering: device summary and
transport choice (I²C); the **public API contract** (every PUB: parameters, return, blocking
behavior, error/edge semantics); the three usage profiles and the bus-ownership rule; timing
guarantees (50 ms spacing, fire-and-return play); DEBUG channel map; and the bring-up determinations
(F1, F2) with their resolved values once known. Cross-link the reference and design docs.

**Verification.** Spec's API table matches the implemented signatures exactly (no drift); every
behavior the spec asserts is covered by a verification case in §2–§5.

---

## 8. Documentation currency

**Why.** Keeping project docs current is sprint work, not an afterthought.

**Target.**
- `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` — flip the *(designed)* markers to *(implemented)*
  for what shipped; reconcile the API sketch (§5 there) with the final signatures; set DEBUG
  channel 1 status to *implemented* in the allocation table.
- `.claude/skill-conventions.md` — update the greenfield note now that real files exist; confirm
  `BUILD_VERSION_LOCATION`/`SPIN2_TOP_FILE` resolve to the created files.
- No `STYLE_GUIDE_DOC`/`HELP_VOICING_GUIDE`/`MANUAL_VOICING_GUIDE` are set for this project, so
  those adherence steps do not apply.

**Verification.** No *(designed)* marker remains for shipped behavior; conventions file references
only files that exist.

---

## 9. Build & on-hardware verification (incl. bring-up determinations)

**Why.** Verification here is compilation **plus** on-hardware behavior; two reference unknowns are
resolved empirically.

**Starting point.** Build/test commands in `.claude/skill-conventions.md`
(`pnut-ts -d src/demo_voice_recognizer.spin2`; host-native `pnut-term-ts` flash+run). Container
compiles only; flashing/running is host-native (env memory).

**Target / procedure.**
- Compile-clean the full tree under `pnut-ts -d` in the container.
- On a P2 wired to the DF2301Q (host-native), flash the demo and run each profile.
- **F1 — wake CMDID:** test whether `playByCMDID(1)` vs `playByCMDID(2)` enters wake state; set
  `enterWakeState()`'s constant accordingly and record it in the spec.
- **F2 — volume range:** sweep `setVolume` to find the real accepted range vs the documented 1–7;
  record in the spec; adjust any (optional) clamp.
- Confirm: latch-clear `getCMDID` semantics; 50 ms spacing via I²C trace; `playByCMDID` non-blocking
  with `isSpeaking()` window; poller mailbox delivery with responsive foreground; clean
  `stopPoller()`.

**Verification.** Normal: real spoken commands produce correct CMDIDs in all three profiles. Edge:
CMDID 0 when idle; rapid commands behave per latest-only mailbox. Error: unplugged sensor →
`start()` fails gracefully; profile switches never hang.

---

## Build order

§1 → §2 → §3 establish the testable core (simple + scanner profiles work on hardware here). §4 adds
the poller cog. §5 wraps the demo around all three. §6 adds driver tracing. §7–§8 produce the spec
and refresh docs. §9 validates on hardware and resolves F1/F2. Each section is a complete,
first-testable deliverable.
