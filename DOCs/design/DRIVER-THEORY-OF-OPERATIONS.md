# ISP Voice Recognizer — Driver Theory of Operations

**Driver:** `isp_voice_recognizer.spin2` (Spin2 / PASM2-if-needed) for the DFRobot DF2301Q
"Gravity: Offline Voice Recognition Sensor" (SKU SEN0539), **I²C transport**.

This document describes **how our P2 driver works** — its architecture, usage modes, timing
discipline, and the I²C layer it rests on. It is distinct from
`DOCs/reference/THEORY-OF-OPERATIONS.md`, which describes the *DFRobot reference library and the
device protocol* we ported from. Read the reference doc for what the chip does on the wire; read
this one for how our object is built.

> **Status: living design doc.** Build 0.1.0 is implemented: `src/isp_voice_recognizer.spin2`
> (driver), `src/demo_voice_recognizer.spin2` (demo/top), on `src/isp_i2c_singleton.spin2` (bus) —
> all compile clean under `pnut-ts -d`. Sections marked *(implemented)* are code; *(planned)* are
> not yet built (the `test_` harness). On-hardware behavior + the F1/F2 values land in task §9.
> The formal API contract is `DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md`.

---

## 1. Purpose & scope

Expose the DF2301Q's recognition results and configuration to P2 applications over I²C, as an
idiomatic P2 object that:

- hands the application the recognized **command ID (CMDID)** (0 = nothing recognized),
- plays reply audio, sets volume / mute / wake-duration, reads wake-duration,
- **never blocks its caller** in the bus path, so it can be driven by a shared "device scanner"
  cog alongside many other peripherals.

UART transport is **out of scope** for now (the reference splits I²C and UART into two classes; we
implement only the I²C class). If added later it would be a sibling object, `isp_voice_recognizer_uart`.

---

## 2. File set & layering *(designed; I²C layer implemented)*

```
  demo_voice_recognizer.spin2     top / demo — selects which usage mode to exercise   (implemented)
  test_voice_recognizer.spin2     on-hardware test harness                            (planned)
        |
        v
  isp_voice_recognizer.spin2      THIS driver — DF2301Q register semantics            (implemented)
        |
        v
  isp_i2c_singleton.spin2         bit-banged I²C bus (shared by all I²C drivers)       (implemented)
```

Naming follows the project convention (parallel role prefixes, not stacked): `isp_` = a driver we
ship, `demo_` = a demo, `test_` = a test harness. The driver name is descriptive because the part
number (DF2301Q / SEN0539) says nothing about function.

The I²C object is a **singleton**: one bus instance shared by every I²C driver in the application.
This is what makes the scanner-cog model work — many device drivers, one bus.

---

## 3. Usage profiles *(implemented)*

The driver offers **three ways to be used**, all built on the same synchronous bus primitives. The
demo selects one.

1. **Passive scanner-poll (primary use).** An existing cog that iterates over all external devices
   and gathers state calls into this driver on each pass. The driver owns **no cog**; it just does
   one quick I²C read when polled. This is the lead use case and the reason the bus path is
   non-blocking (§4).

2. **Self-poller cog.** The driver's `startPoller()` launches a dedicated cog that polls the chip
   and publishes the latest CMDID to a hub mailbox; the application reads the mailbox non-blocking
   via `getLatest()`. For standalone use where no external scanner exists.

3. **Simple synchronous.** A demo/foreground cog calls `getCMDID()` directly and is fine to block.
   Mirrors the reference library's poll loop; simplest to validate on hardware first.

The chip **latches** a recognized CMDID and **clears it on read**, so all three profiles are
poll-and-clear: read returns the latched ID once, then 0 until the next recognition. Polling slower
than commands arrive can coalesce results — profile 2 (a tight poller cog) minimizes that.

---

## 4. Non-blocking timing discipline *(implemented)*

The reference library blocks its caller: `getCMDID` does `delay(50)`, `playByCMDID` does
`delay(1000)`. A shared scanner cog cannot tolerate that. Our rules:

- **No `waitms` in any bus method.** Methods do their I²C transaction and return immediately.
- **50 ms read spacing is enforced by time-check, not busy-wait.** The driver records the tick of
  the last bus read (`GETCT`). `pollCMDID()` called sooner than 50 ms returns the cached value (or
  0) **without touching the bus**. A round-robin scanner naturally spaces its calls past 50 ms; the
  guard only protects against accidental hammering, which the reference's 50 ms delay was really
  there to prevent.
- **`playByCMDID` is fire-and-return.** It issues the write and records a "busy until `ct + 1 s`"
  deadline (the chip's audio play time) as a time-check the caller can consult via `isSpeaking()`,
  instead of stalling a full second.

The net effect: a scanner pass that includes this device costs **one short I²C read** (a few hundred
µs at 100–400 kHz), bounded and predictable.

---

## 5. Public API — as implemented *(implemented)*

The full contract (parameters, returns, blocking, edge semantics) is in
`DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md` §3. The 14 public methods:

| Method | Blocks? | Notes |
|---|---|---|
| `version() : pStr` | no | pointer to the version string (`"0.1.0"`) |
| `start(scl, sda, khz, pullup) : bFound` | no | init bus (via I²C singleton), probe 0x64, return present/absent |
| `pollCMDID() : cmdId` | no | scanner entry point: one read or cached, 50 ms spacing by time-check |
| `getCMDID() : cmdId` | no | alias/simple form for synchronous use |
| `playByCMDID(cmdId)` | no | issue write; track busy-until `ct+1s` |
| `isSpeaking() : bSpeaking` | no | true while inside the post-play window |
| `enterWakeState()` | no | wake via the play path (CMDID per F1) |
| `getWakeTime() : wakeSecs` | no | read reg 0x06 |
| `setWakeTime(wakeSecs)` | no | write reg 0x06 (0–255) |
| `setVolume(volLevel)` | no | write reg 0x05 (no hard-clamp — see ref doc finding F2) |
| `setMuteMode(muteOn)` | no | write reg 0x04 (normalized to 1/0) |
| `startPoller() : ok` / `stopPoller()` | no | profile 2: launch/stop the poller cog |
| `getLatest() : cmdId` | no | profile 2: non-blocking mailbox read, clear-on-read |

Open hardware questions resolved at bring-up (task §9): **F1** (which CMDID enters wake state) and
**F2** (true volume range) — see reference doc §7.

---

## 6. Concurrency & bus-ownership rule *(implemented)*

When the self-poller cog (profile 2) is running, **that cog owns the bus**. The foreground must
read results via `getLatest()` and must **not** call the synchronous bus primitives directly, or
two cogs hit the shared `isp_i2c_singleton` at once. The contract:

- **Configure before you start:** call `setVolume` / `setMuteMode` / `setWakeTime` **before**
  `startPoller()`.
- To reconfigure later, `stopPoller()`, change settings, `startPoller()` again — or (future) add a
  bus lock / route config through a request flag the poller services.

In the passive scanner model (profile 1) there is no driver-owned cog, so the scanner cog is the
sole bus user for this device and no locking is needed beyond whatever the scanner already does
across its device list.

---

## 7. DEBUG channel allocation *(implemented for I²C)*

Tracing uses the P2 **channel-based DEBUG facility** (`{Spin2_v46}` + `DEBUG_MASK`). Each object
that wants trace output owns one DEBUG **channel** (0–31). `DEBUG_MASK` is a compile-time bitmask:
a clear bit means `debug[n](...)` emits **no code at all** (zero overhead); set the bit to compile
the trace in. Plain `DEBUG()` (no channel) ignores the mask.

Because channels are global to a build, we **reserve channel numbers project-wide** so masks don't
collide when several ISP drivers trace in one application:

| Channel | Owner | Status |
|--------:|-------|--------|
| 0 | `isp_i2c_singleton` — I²C bus trace (`DBG_I2C`) | implemented |
| 1 | `isp_voice_recognizer` — recognized / play / config / start trace (`DBG_VOICE`) | implemented |
| 2 | poller-cog activity | reserved |
| 3–31 | unassigned | — |

**Discipline for keeping DEBUG out of the critical path.** Two mechanisms, by layer: the I²C
layer **buffers cheaply during** a transaction (a single `mode|value` WORD per bus op, outside the
inline-PASM `org…end` blocks) via `record()` and only **emits after** the transaction (at `stop()`)
via `report()`; the driver emits `debug[DBG_VOICE]()` **only at semantic boundaries** (recognized
CMDID, play issued, config writes, the `start()` probe) — never inside the poller-pace loop or any
tight loop. Each object ships with its channel **off** (`DEBUG_MASK = 0`); a developer flips one
line (`DEBUG_MASK = (1 << DBG_x)`) and rebuilds to trace.

---

## 8. The underlying I²C interface — `isp_i2c_singleton` *(implemented)*

Bit-banged I²C master, adapted from `jm_i2c` as a **singleton**. Key properties:

- **No P2 smart-pin I²C mode is used or possible.** The sync-serial smart-pin modes are SPI-shaped
  (no per-byte ACK, no START/STOP, push-pull, fixed direction) and don't fit I²C. The object
  bit-bangs SDA/SCL with `DRVL`/`DRVH`; it uses smart-pin *drive modes* only to emulate open-drain
  pull-ups (`P_HIGH_1K5` / `P_HIGH_15K` / etc.). I²C is master-polled by protocol — nothing
  "arrives by itself" on this transport. (UART would be the autonomous-receive transport; out of
  scope here.)
- **Clock stretching removed** (deliberate, per the object's note — unused by nearly all devices).
- Timing is `clktix` system ticks per ¼-bit-period, from `setup(..., khz, ...)` (100 / 400 / 1000).

### 8.1 Public API

`setup(pScl, pSda, khz, pullup)` · `quiesce(pScl, pSda, pullup)` · `present(devid) : ok` ·
`wait(devid)` · `start()` · `write(byte) : ackbit` · `read(ackbit) : byte` ·
`wr_block(pBlock, count) : ackbit` · `rd_block(pBlock, count, ackbit)` · `stop()`.
Exported constants: `PU_NONE / PU_1K5 / PU_3K3 / PU_15K`, `ACK` (0) / `NAK` (1).

Addresses are **8-bit**: 7-bit ID `0x64` → write `$C8`, read `$C9`.

### 8.2 The two DF2301Q core operations on this API

```
' writeReg(reg, val)
i2c.start()
i2c.write($C8)          ' device write address
i2c.write(reg)
i2c.write(val)
i2c.stop()

' readReg(reg) -> val   — uses a REPEATED START (no STOP mid-transaction)
i2c.start()
i2c.write($C8)          ' write the register pointer
i2c.write(reg)
i2c.start()             ' repeated START — start() raises both lines high first, so this is valid
i2c.write($C9)          ' device read address
val := i2c.read(NAK)    ' single byte, NAK on the last byte
i2c.stop()
```

The repeated-START (no STOP between the register write and the data read) is mandatory for the
DF2301Q and is supported by simply calling `start()` again. `begin()` maps to
`i2c.present($C8)` (+ `stop()`).

---

## 9. Related documents

- `DOCs/reference/THEORY-OF-OPERATIONS.md` — DF2301Q device protocol and the reference library
  (register map, UART frame format, command-word ID space, cross-implementation findings F1–F7).
- `.claude/skill-conventions.md` — build/test commands, file-name slots, version-string location.
