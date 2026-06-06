# Punch List — P2 Gravity Voice-Sensor (DF2301Q)

Active outstanding work. At sprint closeout, completed items are swept into the
dated **Done / Archive** section so the **Open** list only carries what's left.

Created 2026-06-04 (build 0.1.0, during hardware bring-up).

---

## Open

### Hardware verification (build 0.1.0)
- [ ] Confirm `showPhrase` on hardware — the **HEARD** line shows the recognized
      words (backtick fix `text \`zstr_(pStr)`; built, not yet hardware-confirmed).
- [ ] Confirm live recognition in **Sync / Scanner / Poller** modes, and that the
      active-mode button highlight is visibly clear on the panel.
- [ ] **F1 — wake CMDID:** both CMDID 1 and 2 wake the module (observed). Lock
      `enterWakeState()` to the documented default `CMD_HELLO_ROBOT` (2) and revert
      the Wake button from the 1↔2 experiment back to `voice.enterWakeState()`.
- [ ] **F2 — volume range:** sweep `setVolume` to find the real accepted range vs
      the documented 1–7; adjust the optional clamp (`VOL_MIN`/`VOL_MAX`) if needed.

### Features
- [ ] **SPEAK row** (parked feature): grow the panel; add `ID−` / `ID+` / `Speak`
      buttons plus keyboard type-in (PC_KEY); step **all** IDs 0–208; play via
      `playByCMDID`. (Design agreed 2026-06-04: grow panel, all IDs, type-in.)

### Spec & requirements parity (WonderCam-pattern review, 2026-06-04)

**Real design/capability gaps (decisions, not just docs):**
- [ ] **Bus LOCK** — add an *optional* P2 lock id to `start()` and acquire/release it around each
      I²C transaction, so the driver coexists with other I²C drivers driven from other cogs on a
      shared bus. Today it assumes sole ownership via the singleton (only the single-cog scanner
      profile is safe). The reference pattern makes this first-class for "drops into a robot's
      sensor mix."
- [ ] **Error model** — `DOCs/policy/SPIN2-AUTHORING-GUIDE.md` mandates **error CODES**
      (`SUCCESS=0` / negative), but our methods return booleans/raw (`start→bFound`, `setVolume→none`,
      `getCMDID→0=none`). Decide: retrofit a named error-code set, or document the deviation.
- [ ] **Clock-stretch is a REQUIREMENT** — record in the spec + theory-of-ops that reads MUST honor
      SCL clock-stretching for this device (the singleton had it *removed*; that caused the bring-up
      failure). Guard against future "optimization."
- [ ] **Regression test top** — there is no `src/test_*.spin2`. Add one (bus ACK, wake-time
      write→read round-trip, volume-shadow round-trip) so every change can re-verify on hardware.
- [ ] **Portability** — confirm a clean compile under host **flexspin** (NFR), or explicitly
      document pnut-ts-only.

**Spec document sections to add (to match the pattern):**
- [ ] Explicit **Purpose & scope** (in/out — e.g. out: UART transport for now, custom-command
      enrollment is camera/voice-UI only).
- [ ] **Source-of-truth & caveats** — frame F1/F2 and the catalog-reshuffle risk as named,
      overridable constants each retired by a bring-up layer.
- [ ] **Numbered Functional + Non-functional requirements** (FR-x / NFR-x).
- [ ] **Demo specification** (what it shows, the `gen_panel_assets.py` asset pipeline, the
      dirty-flag interaction loop, host-only run rule).
- [ ] **Test strategy** — bottom-up bring-up layering table (bus → read → write/echo →
      recognition decode) + the regression top + compile-clean baseline.
- [ ] **Deliverables checklist** and **Acceptance criteria (v1)**.
- [ ] **Process / history document** (narrative of the build, incl. the clock-stretch bring-up).

### Cleanup / release
- [x] **Driver channel-debug** (2026-06-04): `DEBUG_MASK = 0`; channel-1 trace normalized to a
      uniform `voice:` prefix and made complete across the whole object (kept in, masked off —
      costs nothing, coherent if re-enabled). Policy: keep masked `debug[]` in, don't strip it.
- [ ] **Demo plain (unmasked) bring-up scaffolding** still to remove: raw-pin test,
      `wakeTime BEFORE/AFTER` prints, MOUSE-on-change diagnostic. Left in for the F1/F2 +
      SPEAK-verify run; strip after. (CMDID / SPEAK prints are intentional demo output.)
- [ ] **Keep the clock-stretch fix permanently.**
- [ ] Re-tune `STRETCH_LIMIT` (currently ~120 ms generous) now that reads work.
- [ ] Record resolved **F1/F2** values into `DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md`
      (§8) and `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` (closes the bring-up TBDs).
- [ ] Sprint closeout (exit baseline vs entry baseline).

---

## Future / parked

- [ ] **Awaken the UART transport** (9600 8N1) for richer communication not available
      over I²C: module **reset**, OTA update, detailed **version** queries, audio
      **play start / pause / resume / stop**, and event **notifications** — notably
      *wakeup-enter* and *wakeup-exit* (which would let the panel reflect the module's
      **live wake state**). Mirror the reference's two-class split (I²C class + UART
      class). **Staying I²C-only for now** (decision 2026-06-04).

---

## Decisions (standing — recorded so we don't relitigate)

- **I²C public API is complete** — every I²C-accessible capability has a named public
  method; all five registers (`0x02`–`0x06`) are represented.
- **No low-level register read/write in the public API** — `readReg`/`writeReg` stay
  private; the public surface is capability-named methods only (decision 2026-06-04).
- **`SET_MUTE` (`0x04`) and `SET_VOLUME` (`0x05`) are write-only in silicon** — there is
  no `getMute`/`getVolume` to expose.
- **STOP = stop polling only** (idle). It does **not** command the device and does **not**
  mute; the device is left in its current state. The DF2301Q has no I²C "stop-listening" /
  sleep command — it is an always-on wake-word listener; the wake *state* auto-expires
  after `WAKE_TIME` seconds.
- **Active-mode running indicator** already implemented: the selected Sync/Scanner/Poller
  button stays highlighted; switching between modes is direct (no STOP needed between).

---

## Done / Archive

### 2026-06-04 (later)
- **Error model:** added `E_OK`/`E_NAK` status returns to all write methods (`setVolume`,
  `setMuteMode`, `setWakeTime`, `playByCMDID`, `enterWakeState`) per the authoring guide; queries
  stay value/boolean-by-nature. `start()`/`startPoller()` remain boolean presence queries.
- **Volume shadow:** `DEF_VOLUME` applied at `start()`, tracked on every `setVolume()`, exposed via
  `getVolume()`; demo shows it (no more blank VOLUME box).
- **`showPhrase` fix:** `` text `zstr_(pStr) `` (was missing the backtick → rendered literally).
- **SPEAK row built** (compiles; verify on next run): panel grew to 412px; `ID−`/`ID+`/`Speak`
  buttons + keyboard type-in (`PC_KEY`) step the target ID 0–208 and play via `playByCMDID`.
- **Spec expanded** to the WonderCam pattern: scope (§1), return convention/error model (§3),
  device-protocol requirements incl. the clock-stretch REQUIREMENT (§3.2), test strategy (§9),
  NFRs (§10), deliverables (§11), acceptance (§12). *Still to add:* numbered FR-x list, a dedicated
  demo-spec section, the "source-of-truth & caveats" framing, and the process/history doc.

### 2026-06-04
- **Root-cause I²C read fix (commit `890aa4b`):** bit-bang now honors SCL
  clock-stretching in `start()` / `stop()` / `read()`. Confirmed on a logic analyzer
  (clean repeated-START + `0x64(R)` + data + STOP); reads return real CMDIDs.
- **Pull-up fix:** demo uses `PU_1K5` (internal 1.5 kΩ); `PU_3K3`'s 1 mA source idled
  the bus low (no external pull-ups on this rig).
- Panel polish: label-overlap fix, active-mode highlight layer, mute glyph + mute-aware
  volume readout, non-forced (module-retained) volume.
