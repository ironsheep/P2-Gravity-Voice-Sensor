# DF2301Q Voice Recognition Sensor — Theory of Operations

**Device:** DFRobot DF2301Q "Gravity: Offline Voice Recognition Sensor" (SKU SEN0539)
**Source of this document:** reverse-read of the reference library in
`REF/DFRobot_DF2301Q-master/` — the Arduino/C++ driver, three Python ports
(Raspberry Pi, CircuitPython, UNIHIKER), and all five example programs.

This document describes **what the hardware does and how a host talks to it**, so the
P2 (Spin2/PASM2) port can be written against behavior rather than against any one
implementation. It is the protocol spec; `REF/` is the source it was distilled from.

> Scope note: the reference code never *reads* version/FLASH-UID/ACK/NOTIFY traffic — it
> only defines the constants. So the parts of this document covering those message types
> are derived from the constant tables and frame grammar, not from observed driver use.
> They are marked **(constants only)** where that distinction matters.

---

## 1. What the device is

A self-contained **offline** automatic speech recognition (ASR) module. No cloud, no
network — recognition runs on the module's own DSP. From the host's point of view it is a
peripheral that:

- continuously listens on a **dual-microphone** array,
- recognizes a spoken phrase against its vocabulary,
- exposes the recognized phrase to the host as a small integer **command ID (CMDID)**,
- can **speak a reply** through an onboard speaker (or an external speaker via a jack),
- can be **configured** (volume, mute, wake-duration) and **driven** (play a reply, reset).

Hardware features relevant to operation (from the product README):

- **Gravity interface**, plug-and-play, **3.3 V and 5 V tolerant**.
- **Two host transports on the same connector: I2C and UART** — pick one.
- **~150 built-in fixed command words** plus **user-trainable custom command words**
  ("command word self-learning" — any audio can become a command).
- Onboard **speaker** + external-speaker interface for spoken recognition feedback.
- Indicators: **red = power**, **blue = recognition status**.

---

## Choosing a transport: I2C vs UART (quick reference)

The module exposes the **same recognizer** over two wire protocols on the same connector —
**pick one**. They are *not* feature-symmetric: each can do something the other can't.
Use this section to decide; §3 (I2C) and §4 (UART) are the byte-level detail, and §6 F5
records that the asymmetry is inherent to the device, not a bug.

### Capability matrix

| Capability | I2C (`0x64`) | UART (9600 8N1) | Notes |
|------------|:---:|:---:|-------|
| Read recognized CMDID (`getCMDID`) | ✅ reg `0x02` | ✅ `CMD_UP` frame, `msgData[0]` | 0 = nothing recognized on both |
| Speak a reply (`playByCMDID`) | ✅ reg `0x03` | ✅ `PLAY_VOICE` frame | ~1 s to play on both |
| Set volume | ✅ reg `0x05` | ✅ `settingCMD(SET_VOLUME)` | range caveat in §6 F2 |
| Set mute / unmute | ✅ reg `0x04` | ✅ `settingCMD(SET_MUTE)` | |
| Set wake-up duration | ✅ reg `0x06` | ✅ `settingCMD(SET_WAKE_TIME)` | |
| **Read back** wake-up duration (`getWakeTime`) | ✅ reg `0x06` | ❌ — | **I2C only** (§6 F5) |
| **Explicit** enter-wake command | ⚠️ play-path only (ID-1, ambiguous §6 F1) | ✅ `settingCMD(SET_ENTERWAKEUP)` | clean on UART; a guess on I2C |
| **Reset the module** (`resetModule`) | ❌ — | ✅ `RESET_MODULE`, ~3 s settle | **UART only** |
| Presence probe in `begin()` | ✅ real ACK check (write `0x00`) | ❌ just opens the port | only I2C confirms "sensor is there" (§3.5) |
| Async status events (power-on, wake enter/exit, play start/end) | ❌ — | ⚠️ `NOTIFY_STATUS` *(constants only)* | protocol supports it; reference never reads it (§4.8) |
| ACK / version / FLASH-UID queries | ❌ — | ⚠️ defined *(constants only)* | UART frame grammar allows; unused by reference (§4.8) |

✅ = supported & exercised by the reference · ⚠️ = possible but caveated/unproven · ❌ = not available on that transport

### Why pick one over the other

| | I2C | UART |
|---|---|---|
| **Wire mechanics** | Trivial: write-reg-then-byte, single-byte payloads, repeated-START read. No framing. | Framed, length-prefixed, **checksummed** packets parsed by a byte-at-a-time state machine. |
| **Best when** | You want the simplest possible host code, need to **read back wake-time**, want a real **presence probe**, or are sharing a bus from a scanner cog. | You need **module reset**, a **clean explicit wake**, or want to consume **async notifications** / ACK / version traffic. |
| **Costs you** | Wake-ID is ambiguous (§6 F1); no reset; no async events. | A whole frame/checksum state machine to implement; **no `getWakeTime`**; a dedicated TX/RX pair. |
| **Public surface** | `begin`, `getCMDID`, `playByCMDID`, `getWakeTime`, `setWakeTime`, `setVolume`, `setMuteMode` | `begin`, `getCMDID`, `playByCMDID`, `resetModule`, `settingCMD` |

> **This port's choice:** the P2 driver implements **I2C only** (`isp_voice_recognizer`),
> matching the reference's two-object split — simplest mechanics, real presence probe, and
> wake-time read-back, and it sits cleanly on a shared I2C bus driven by a scanner cog. A
> UART sibling (`isp_voice_recognizer_uart`) is the path to reset / explicit-wake / async
> events if a future application needs them.

---

## 2. The operating model (transport-independent)

The behavior below is the same whether you reach the module over I2C or UART; only the
byte-level mechanics differ.

### 2.1 Wake → command window → sleep

The module is normally **asleep** (idle, not acting on speech beyond the wake word). The
interaction cycle is:

1. **Wake.** The user speaks the wake word (factory default phrase **"Hello Robot"**), or
   the host triggers wake programmatically (see §2.3). The blue LED indicates the awake
   state.
2. **Command window.** While awake, spoken **command phrases** are recognized and each
   produces a CMDID. The module optionally speaks a reply for that command.
3. **Wake timeout.** If no command is heard for the **wake-up duration** (a configurable
   number of seconds, `WAKE_TIME`, range 0–255), the module returns to sleep and must be
   woken again. Setting/getting this duration is a first-class host operation.

So a typical session is: *"Hello Robot"* → (blue LED on) → *"go forward"* → CMDID 22 →
… → silence for `WAKE_TIME` seconds → asleep.

### 2.2 Recognition result delivery

A recognized phrase becomes a **command ID (CMDID)**, an unsigned byte:

- **0 is the sentinel for "nothing recognized."** Every read path treats `CMDID == 0` as
  "no new result," and the host polls until it sees non-zero.
- Non-zero IDs map to vocabulary entries (built-in or custom — see §5).
- The result is **latched** by the module and **consumed on read**: once the host reads a
  non-zero CMDID, subsequent reads return 0 until the next recognition. The host model is
  therefore a **poll-and-clear** loop.

### 2.3 Programmatic control the host can exert

Beyond passively reading results, the host can:

- **Play a reply by CMDID** — make the module speak the audio response associated with a
  command, without anyone saying it. Used both for feedback and (per the reference) to
  **force the module awake** (§2.4).
- **Set volume** of spoken replies.
- **Mute / unmute** spoken replies.
- **Set / get the wake-up duration.**
- **Enter wake state** explicitly (UART has a dedicated config sub-command for this; on
  I2C it is done via the play path — see the open question in §6).
- **Reset the module** (UART only in this library).

### 2.4 Two ways to wake programmatically

- **I2C:** via `playByCMDID` with the wake command word (the reference's `@note` says you
  "enter wake-up state through ID-1 in I2C mode"). **The examples disagree on which ID
  this is** — see §6, finding F1. Treat the exact wake ID as hardware-verify-on-bringup.
- **UART:** via the explicit config sub-command `SET_ENTERWAKEUP` (0x81) with value 0.

---

## 3. I2C transport — theory of operations

### 3.1 Bus parameters

- **7-bit address `0x64`, fixed.** (The header's doc-comment claiming a default of `0x50`
  with "first three bits" selectable is copy-paste boilerplate from another sensor — see
  §6, finding F6. The code unconditionally uses `0x64`.)
- Plain register-oriented access: **write a register index, then write or read one data
  byte.** All transactions in the reference are single-byte payloads.

### 3.2 Register map

| Reg  | Name        | Access | Meaning                                              |
|------|-------------|--------|------------------------------------------------------|
| 0x02 | `CMDID`     | read   | Latched recognized command ID; **0 = none**          |
| 0x03 | `PLAY_CMDID`| write  | Speak the reply for this command ID                  |
| 0x04 | `SET_MUTE`  | write  | 1 = mute, 0 = unmute                                 |
| 0x05 | `SET_VOLUME`| write  | Playback volume (documented 1–7; see §6 finding F2)  |
| 0x06 | `WAKE_TIME` | r/w    | Wake-up duration in seconds, 0–255                   |

### 3.3 Byte-level sequences

**Write a register** (`writeReg`): START → `addr+W` → `reg` → `dataByte` → STOP.

**Read a register** (`readReg`) — uses a **repeated START**, no STOP between the address
write and the data read:

```
START → addr+W → reg
REPEATED START → addr+R → read 1 byte → STOP
```

This repeated-START framing is mandatory and is the single most important detail for the
P2 port: do **not** issue a STOP between writing the register index and reading the byte.
All four reference transports honor it —
- C++ `Wire.endTransmission(false)` then `requestFrom` (the `false` = no STOP),
- Raspberry Pi `smbus.read_i2c_block_data` (repeated-START internally),
- CircuitPython `writeto_then_readfrom`,
- UNIHIKER `readfrom_mem_restart_transmission` (the name says it).

### 3.4 Timing requirements (these are real, the module needs them)

| Operation       | Required delay        | Why                                                       |
|-----------------|-----------------------|----------------------------------------------------------|
| `getCMDID` read | **50 ms** per read    | Polling faster starves/interferes with the module's other functions. The reference enforces 50 ms around every CMDID read. |
| `playByCMDID`   | **~1 s** after write  | The reply audio needs ~1 second to play; the write returns immediately, the delay lets it finish. |

Note the 50 ms is placed **before** the read in the Python ports and **after** the read in
C++; in a steady poll loop the net cadence is identical (see §6, F3). For the P2 port,
guaranteeing ≥50 ms between consecutive CMDID reads is what matters.

### 3.5 `begin()` / presence probe

The C++ `begin()` is a **bus presence check**: address the device and write a single
`0x00` byte; success = the device ACKed (`endTransmission()` returned 0). The Python ports
skip this and just open the bus. The P2 `begin` should do the probe (write `0x00`, confirm
ACK) and return pass/fail, because it's the only "is the sensor actually there" signal.

### 3.6 I2C public surface

`begin`, `getCMDID`, `playByCMDID`, `getWakeTime`, `setWakeTime`, `setVolume`,
`setMuteMode`.

---

## 4. UART transport — theory of operations

### 4.1 Line parameters

- **9600 baud, 8N1.** Same logical device, different wire.
- Communication is **framed, length-prefixed, and checksummed**, parsed by a
  byte-at-a-time **state machine** so the two header bytes (and the rest) may arrive in
  separate reads.

### 4.2 Frame layout

All multi-byte integer fields are **little-endian (low byte first)**.

```
Offset  Field        Size  Notes
------  -----------  ----  ---------------------------------------------
0       header       2     0xF4 0xF5  (low byte 0xF4 first)
2       dataLength   2     u16-LE; number of msgData bytes, 0..8
4       msgType      1     CMD_UP / CMD_DOWN / ACK / NOTIFY
5       msgCmd       1     operation selector (see tables)
6       msgSeq       1     increments once per outbound packet
7       msgData[]    N     N == dataLength, max 8
7+N     checksum     2     u16-LE
9+N     tail         1     0xFB
```

### 4.3 Checksum

**Checksum = the arithmetic sum of every byte from offset 4 (`msgType`) through the last
`msgData` byte**, i.e. `msgType + msgCmd + msgSeq + Σ msgData`, which is `dataLength + 3`
bytes. Emitted little-endian (`sum & 0xFF`, then `(sum >> 8) & 0xFF`). The header, length,
checksum, and tail bytes are **not** included in the sum. The receiver recomputes over the
same range and drops the frame on mismatch.

### 4.4 Receive state machine (`recvPacket`)

States, in order: `HEAD0 → HEAD1 → LENGTH0 → LENGTH1 → TYPE → CMD → SEQ → DATA(×N) →
CKSUM0 → CKSUM1 → TAIL`. Behavior to reproduce exactly:

- **HEAD0:** wait for `0xF4`; ignore everything else.
- **HEAD1:** expect `0xF5`. If it's another `0xF4`, stay hunting in HEAD1; any other byte
  resets to HEAD0. (This lets `F4 F4 F5...` resync correctly.)
- **LENGTH0/1:** assemble `dataLength` LE. **If it exceeds 8, abandon the frame** (reset
  to HEAD0) — bounds check before trusting the length.
- **TYPE/CMD/SEQ:** store each. After SEQ, if `dataLength == 0` skip straight to CKSUM0,
  else go to DATA.
- **DATA:** collect exactly `dataLength` bytes.
- **CKSUM0/1:** assemble the received checksum LE, **recompute** over offset 4..end-of-data,
  and only advance to TAIL if they match; otherwise reset to HEAD0.
- **TAIL:** if the byte is `0xFB` the frame is accepted. **If the accepted frame's
  `msgType == CMD_UP (0xA0)`, the recognized command ID is `msgData[0]`** — this is the
  UART equivalent of reading I2C register 0x02. Then reset to HEAD0 for the next frame.

`getCMDID` over UART = run `recvPacket` once, return the captured `msgData[0]` (or 0 if no
`CMD_UP` frame completed). As with I2C, **0 means nothing recognized**, and the captured ID
is cleared each call (poll-and-clear).

### 4.5 Transmit (`sendPacket`)

1. **Drain the RX buffer first** (read and discard any pending input) so the reply lines up
   with this request.
2. Write header(2) + dataLength(2) verbatim.
3. Write `msgType`, `msgCmd`, `msgSeq`, and the `dataLength` data bytes, **accumulating the
   checksum** over exactly those bytes.
4. Write checksum LE (2 bytes), then tail `0xFB`.
5. **Delay ~100 ms** after the frame (lets the module process before the next packet).

`msgSeq` starts at 0 (reset in `begin()`) and **post-increments on every outbound packet**.

### 4.6 Outbound operations the reference builds

| Operation     | msgType   | msgCmd            | dataLength | msgData                                              | Post-delay |
|---------------|-----------|-------------------|-----------:|------------------------------------------------------|-----------:|
| `playByCMDID` | CMD_DOWN  | PLAY_VOICE (0x92) | 6          | `PLAY_START(0x80)`, `PLAY_BY_CMD_ID(0x92)`, then the ID as u32-LE (4 bytes) | ~1 s |
| `resetModule` | CMD_DOWN  | RESET_MODULE(0x95)| 5          | ASCII `"reset"`                                       | ~3 s |
| `settingCMD`  | CMD_DOWN  | SET_CONFIG (0x96) | 5          | `setType`, then `setValue` as u32-LE (4 bytes)        | (none) |

`settingCMD` is the UART catch-all for configuration; `setType` selects which knob:

| setType (sub-cmd)            | Value | Meaning / range                    |
|------------------------------|-------|------------------------------------|
| `SET_VOLUME`                 | 0x80  | volume 1–7                         |
| `SET_ENTERWAKEUP`            | 0x81  | enter wake state; value 0          |
| `SET_PRT_MID_RST`            | 0x82  | (protocol-middleware reset)        |
| `SET_MUTE`                   | 0x83  | 1 = mute, 0 = unmute               |
| `SET_WAKE_TIME`              | 0x84  | wake duration 0–255 s              |
| `SET_NEEDACK` / `SET_NEEDSTRING` | 0x90 / 0x91 | request ACK / string reporting |

> Note the asymmetry vs I2C: over UART there is **no `getWakeTime`** and the volume/mute/
> wake-time setters all funnel through `settingCMD(SET_CONFIG, …)` rather than dedicated
> calls. There is, however, a dedicated `resetModule` and an explicit enter-wake config.

### 4.7 UART public surface

`begin`, `getCMDID`, `playByCMDID`, `resetModule`, `settingCMD`.

### 4.8 Message-type / command vocabulary (constants only)

Defined in the header for completeness; the reference driver only *sends* `CMD_DOWN` and
only *acts on* `CMD_UP`. The rest are documented here for a fuller P2 implementation that
might parse ACKs, notifications, or version queries.

- **msgType:** `CMD_UP 0xA0` (module→host result), `CMD_DOWN 0xA1` (host→module command),
  `ACK 0xA2`, `NOTIFY 0xA3`.
- **msgCmd:** `ASR_RESULT 0x91`, `PLAY_VOICE 0x92`, `GET_FLASHUID 0x93`,
  `GET_VERSION 0x94`, `RESET_MODULE 0x95`, `SET_CONFIG 0x96`, `ENTER_OTA_MODE 0x97`,
  `NOTIFY_STATUS 0x9A`, `ACK_COMMON 0xAA`; user commands start at `USER_START 0xB0`.
- **NOTIFY_STATUS events:** `POWERON 0xB0`, `WAKEUPENTER 0xB1`, `WAKEUPEXIT 0xB2`,
  `PLAYSTART 0xB3`, `PLAYEND 0xB4` — i.e. the module can asynchronously announce
  power-on, wake-enter/exit, and play start/end. A polling-only port ignores these; an
  event-driven port could surface "is awake" / "is speaking" from them.
- **ACK error codes:** `NONE 0x00`, `CHECKSUM 0xFF`, `NOSUPPORT 0xFE`.
- **GET_VERSION sub-selectors:** protocol / SDK / ASR / preprocess / player / app version.

---

## 5. Command-word ID space

CMDIDs are a flat byte namespace shared by built-in and custom words (full list in
`REF/.../circuitpython/DFRobot_DF2301Q_Commands.py`). The structure:

- **0** — `Silence` (the "nothing" sentinel).
- **1** — `WakeUpWordsForLearning`.
- **2** — `HelloRobot` (the default spoken wake word's command entry).
- **5–21** — `CustomCommand1..17`: the **user-trainable** slots (note IDs 3–4 are
  unused/reserved in the enum).
- **22–142** — the bulk of the **~150 built-in fixed commands**: motion ("go forward" 22,
  "retreat" 23…), robot/vision modes, dot-matrix display, sensors, fan/AC/lighting/curtain
  control, media playback, etc. These exist whether or not the host uses them; the module
  recognizes the phrase and reports the ID.
- **200–208** — **learning/maintenance control words**: `LearningWakeWord 200`,
  `LearningCommandWord 201`, `ReLearn 202`, `ExitLearning 203`, `IWantToDelete 204`,
  `DeleteWakeWord 205`, `DeleteCommandWord 206`, `ExitDeleting 207`, `DeleteAll 208`.
  These drive the **on-device self-learning workflow by voice** — the host doesn't train
  the module via the bus; the user speaks these words to enroll/delete custom commands,
  and the module simply reports the IDs as they happen.

For the P2 port these are data, not behavior: a `CON` table of named IDs is a convenience,
but the driver's job is just to move the byte. Custom-command *training* is a spoken
on-device procedure, not a host-bus operation.

---

## 6. Example programs & applications

### 6.1 The five demo programs (summary overview)

There are five example programs — `examples/i2c/i2c.ino`, `examples/uart/uart.ino`,
`python/circuitpython/examples/i2c.py`, `python/raspberrypi/examples/i2c.py`, and
`python/raspberrypi/examples/uart.py`. **They are all the same program in different
languages/transports**, and they establish the canonical usage pattern the P2 driver
should make easy:

```
setup():
    begin()  (retry until the device answers)        # I2C only does a real probe
    setVolume(...)                                    # I2C: direct;  UART: settingCMD(SET_VOLUME)
    setMuteMode(0)                                    # I2C: direct;  UART: settingCMD(SET_MUTE)
    setWakeTime(~20)                                  # I2C: direct;  UART: settingCMD(SET_WAKE_TIME)
    getWakeTime() and print it                        # I2C only
    playByCMDID(23)                                   # speak one reply as a startup sign-of-life

loop():
    id = getCMDID()
    if id != 0: print id
    delay 2–3 s
```

So the reference "application" is a **poll loop**: configure once, then repeatedly read
CMDID and react to non-zero values. Everything a real integrator does hangs off "got
CMDID N → do something." This is the shape the P2 object should serve.

### 6.2 The one genuine application beyond the demos — UNIHIKER `test.py`

`python/unihiker/test.py` is the only example that does more than print. It's a small
**voice-controlled GPIO application**:

- Initializes the board and an LED on pin P24.
- Configures the module (volume 5, unmute, wake-time 20) and plays CMDID 2 as a sign of
  life.
- In its loop, reads CMDID and **maps custom commands to hardware actions**:
  `CustomCommand1 (ID 5)` → LED on; `CustomCommand2 (ID 6)` → LED off.

It demonstrates the intended end-use: **train two custom phrases on the module, then let
recognition events drive real outputs.** For the P2, this is the archetypal downstream
app — the driver hands up a CMDID, the application maps it to P2 pin/peripheral actions.
Nothing in it is P2-specific; the value is the pattern (custom-ID → action table).

The UNIHIKER port also differs mechanically in two harmless ways: it **comments out the
entire UART class** (I2C-only on that board) and moves the 50 ms CMDID pacing into the
application loop rather than the driver. Neither changes the protocol.

---

## 7. "Does this all make sense?" — cross-implementation findings

Reading the four implementations against each other surfaced a handful of
inconsistencies and ambiguities. None block the port, but each is a decision the P2
implementation should make deliberately rather than inherit by accident. **Anything that
needs hardware to settle is flagged for bringup.**

- **F1 — Which CMDID wakes the module is ambiguous (verify on hardware).** The C++ I2C
  example comments `playByCMDID(1)` as "Wake-up command"; the CircuitPython example
  comments `playByCMDID(HelloRobot == 2)` as "Wake-up command"; UNIHIKER plays ID 2 at
  startup. The header note ("enter wake-up state through ID-1 in I2C mode") is itself
  unclear — "ID 1" vs "ID − 1." **Recommendation:** on bringup, test which of CMDID 1 / 2
  actually wakes the module on I2C, and document it; expose wake as a named method rather
  than a magic number. (UART sidesteps this with the explicit `SET_ENTERWAKEUP`.)

- **F2 — Volume range is documented 1–7 but examples exceed it.** Every doc-comment says
  1–7, yet `circuitpython/examples/i2c.py` calls `set_volume(15)`, and the commented-out
  clamp logic in the drivers references an upper bound of **20**, not 7. So the true
  hardware range is probably 0–20 (or similar) with 1–7 being a conservative
  documented subset. **Recommendation:** don't hard-clamp to 1–7 in the P2 driver; pass
  the value through (optionally clamp to 0–20) and note the real range after a hardware
  check.

- **F3 — The 50 ms CMDID delay is placed differently across ports.** C++ delays *after*
  the read; the Python ports sleep *before* it; UNIHIKER puts it in the app loop. The
  invariant that actually matters is **≥50 ms between consecutive CMDID reads**.
  **Recommendation:** enforce the spacing inside `getCMDID` so callers can't accidentally
  poll too fast.

- **F4 — `playByCMDID`/`settingCMD` payload width differs but is wire-compatible.** C++
  writes the ID/value as a full **u32 little-endian** (`memcpy` of 4 bytes) into the
  declared `dataLength`; the Python ports write only the low byte and leave the rest at
  their zero-initialized default. Because the IDs/values in use are small and the trailing
  bytes are zero, the bytes on the wire are identical. **Recommendation:** the P2 port
  should emit the full declared width (6 data bytes for play, 5 for setting) with the
  number in low-byte-first order and high bytes zeroed — matching C++, which is the most
  literal reading of `dataLength`.

- **F5 — UART omits `getWakeTime`; I2C omits an explicit enter-wake.** The two transports
  are not feature-symmetric (UART can't read back wake-time; I2C has no `SET_ENTERWAKEUP`
  sub-command, only the play-based wake). This is inherent to the device, not a bug.
  **Recommendation:** mirror the reference's two-object split and don't try to force a
  uniform surface across both; document the gaps.

- **F6 — Stale I2C-address doc-comment.** The header claims a default address of `0x50`
  with "the first three bits determine the value of the address." That is boilerplate from
  a different DFRobot sensor; this device's address is the fixed **`0x64`** the code
  actually uses. **Recommendation:** ignore the comment; hardcode `0x64` (configurable
  only if a real strap/variant is discovered).

- **F7 — A dead `0x5A` "tail" constant.** The Python ports define
  `DF2301Q_I2C_MSG_TAIL = 0x5A`, which is never referenced anywhere. The real UART tail is
  `0xFB`; I2C has no framing/tail at all. **Recommendation:** do not port `0x5A`.

**Bottom line:** the protocol itself is coherent and the four implementations agree on all
the load-bearing details — addresses, register map, frame format, checksum range,
repeated-START, the 0-means-nothing convention, and the required delays. The
discrepancies are at the edges (wake-ID semantics, volume range, payload padding, doc
typos) and are exactly the points to pin down on first hardware bringup. The reference is
a sound basis for the P2 port; port the C++ behavior as the primary spec and use the
Python ports as the tie-breaker where C++ is silent.
