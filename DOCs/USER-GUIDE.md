# DF2301Q Voice Recognizer — Library User's Guide

A task-oriented manual for using the P2 (Spin2) driver for the DFRobot **DF2301Q "Gravity:
Offline Voice Recognition Sensor"** (SKU SEN0539) over I2C.

**Audience:** P2 application developers *and* AI coding agents integrating this object. It is
written to be read top-to-bottom by a human or consumed in pieces by an agent — every method has
a signature, a one-line contract, and a runnable snippet.

**How this fits the other docs** (read these for depth; this guide is the "how do I use it"):
- `DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md` — the **formal API/behavior contract**.
- `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` — **how the driver works inside**.
- `DOCs/reference/THEORY-OF-OPERATIONS.md` — the **device protocol** we ported from.
- `DOCs/COMMAND-CATALOG.md` — the **full built-in command-word list** (generated; machine-readable).

---

## 0. Minimal integration — the least you must add

**The question this section answers:** *what is the smallest set of files I drop into an existing
P2 system to make it respond to spoken commands?* Pick a tier and copy exactly those files.

| Tier | Add these files | You get |
|------|-----------------|---------|
| **Minimal** (react by ID) | `isp_voice_recognizer.spin2` **+** `isp_i2c_singleton.spin2` | poll `getCMDID()`, `case` on `voice.CMD_*` |
| **+ Phrases / custom words** | also `isp_voice_command_names.spin2` | `cmdName(id)` → text; register custom slots 5–21 |
| **+ Visual demo** | also `demo_voice_recognizer.spin2` + `panel_bg/font/hi.bmp` | the DEBUG-panel reference app |

**Recipe (minimal tier):**
1. Copy the two `.spin2` files next to your top-level object (pnut-ts resolves `OBJ` relative to
   the *including* file's directory).
2. Add the `OBJ` lines and call `start()` once, then poll — see [§2 Quick start](#2-quick-start).

**Shared-bus caveat:** `isp_i2c_singleton` is a *shared* I2C bus object. If your system already
includes it for another device, **reuse that instance** — do not add a second copy; the singleton
is meant to back every I2C device on the bus. You include it here only to bring up the bus and to
name the `i2c.PU_*` pull-up selectors.

> The integration-kit release zip (`Voice-Sensor-<version>.zip`) ships these files **flat**, plus
> this guide, the command catalog, and a worked `custom_words_example.spin2` — so it compiles in
> PNut as unpacked. The `demo` zip is the superset with the demo app and artwork.

---

## 1. What you get

A self-contained, **offline** speech-recognition peripheral exposed as a P2 object. The module
listens continuously, recognizes a spoken phrase from its ~150-word built-in vocabulary (plus up to
17 user-trained custom words), and reports the result to your application as a small integer
**command ID (CMDID)**. It can also speak reply audio and be configured (volume / mute / wake time).

Every bus method is **non-blocking**, so the driver can be polled from a shared "device scanner" cog
without stalling it.

### The object set (include what you need)

```
  your_app.spin2  / demo_voice_recognizer.spin2     your application / the demo
        |
        v
  isp_voice_recognizer.spin2     THE DRIVER — recognition, playback, config; CMD_* catalog
        |
        v
  isp_i2c_singleton.spin2        shared bit-banged I2C bus (one instance for all I2C devices)

  isp_voice_command_names.spin2  OPTIONAL — ID->phrase cmdName() + custom-word registration
```

- Need only to **react to commands**? Include `isp_voice_recognizer`; switch on its `CMD_*` constants.
- Need the **human phrase** (to print/display) or **custom words**? Also include
  `isp_voice_command_names`. It is opt-in so react-by-ID apps don't pay for the string table.

---

## 2. Quick start

```spin2
OBJ
    voice : "isp_voice_recognizer"
    i2c   : "isp_i2c_singleton"     ' only needed to reference the PU_* pull-up selectors

CON
    SCL_PIN = 18
    SDA_PIN = 16
    BUS_KHZ = 100                    ' 100 (standard) / 400 / 1000

PUB main() | id
    ' 1. Bring up the bus and confirm the sensor answers (PU_1K5 = strong internal pull-up;
    '    use i2c.PU_NONE if your board has external pull-ups).
    if not voice.start(SCL_PIN, SDA_PIN, BUS_KHZ, i2c.PU_1K5)
        debug("DF2301Q not found - check wiring")
        return
    voice.setWakeTime(15)            ' seconds awake after the wake word

    ' 2. Poll for recognitions (0 = nothing recognized).
    repeat
        id := voice.getCMDID()
        if id <> 0
            debug("heard CMDID ", udec_(id))
        waitms(50)                   ' >=50 ms between reads is enforced internally anyway
```

The interaction model on the device: the user says the wake word ("Hello Robot" by default), the
module wakes (blue LED), recognized command phrases each produce a CMDID for `WAKE_TIME` seconds,
then it sleeps until woken again.

---

## 3. Usage profiles

The driver supports three ways to be used over the same non-blocking primitives. Pick one.

| # | Profile | How | Read results with |
|---|---------|-----|-------------------|
| 1 | **Passive scanner-poll** (primary) | a foreign "scan all devices" cog calls in on each pass | `pollCMDID()` |
| 2 | **Self-poller cog** | `startPoller()` runs a dedicated cog into a mailbox | `getLatest()` |
| 3 | **Simple synchronous** | a foreground loop polls directly | `getCMDID()` |

**Bus-ownership rule (profile 2):** while the poller cog runs it **owns the bus**. Read only via
`getLatest()`, and configure `setVolume`/`setMuteMode`/`setWakeTime` **before** `startPoller()`. To
reconfigure later: `stopPoller()`, change settings, `startPoller()` again.

---

## 4. API reference — `isp_voice_recognizer` (the driver)

**Return convention:** *action* methods return a status **code** — `E_OK` (0) or `E_NAK` (-1, the
device did not acknowledge a bus byte). *Value* queries return their value (`0` from a CMDID read
means "nothing recognized," which is a value, not an error). *Presence* queries return `TRUE`/`FALSE`.

| Method | Returns | Purpose |
|--------|---------|---------|
| `version()` | `pStr` | pointer to the version string (`"1.0.0"`) |
| `start(scl, sda, khz, pullup)` | `bFound` | init the bus on the pins, probe `$64`; seeds the volume shadow. `TRUE` if present. Call once first. |
| `getCMDID()` | `cmdId` | latest recognized ID, `0` = none (simple-profile alias of `pollCMDID`) |
| `pollCMDID()` | `cmdId` | latest recognized ID, `0` = none; non-blocking, >=50 ms read spacing enforced |
| `playByCMDID(cmdId)` | `status` | speak the reply audio for `cmdId` (fire-and-return; ~1 s plays async) |
| `isSpeaking()` | `bSpeaking` | `TRUE` while still inside the ~1 s window after `playByCMDID` |
| `enterWakeState()` | `status` | wake the module programmatically (via the play path) |
| `getWakeTime()` | `wakeSecs` | read the wake-up duration (seconds) |
| `setWakeTime(wakeSecs)` | `status` | set wake-up duration, 0..255 s |
| `setVolume(volLevel)` | `status` | set playback volume (passed through unclamped) and update the shadow |
| `getVolume()` | `volLevel` | current volume from the driver's **shadow** (the chip can't read it back) |
| `setMuteMode(muteOn)` | `status` | nonzero mutes, 0 unmutes |
| `startPoller()` | `ok` | profile 2: launch the poller cog. `TRUE` ok; `FALSE` if already running / no free cog |
| `stopPoller()` | — | profile 2: stop the poller cog, release the bus |
| `getLatest()` | `cmdId` | profile 2: non-blocking read of the poller mailbox, cleared on read |

**Useful constants:** `voice.CMD_*` (the full catalog — see §7), `voice.E_OK` / `voice.E_NAK`,
`voice.DEF_VOLUME`. The pull-up selectors passed to `start()` live on the I2C object
(`i2c.PU_NONE / PU_1K5 / PU_3K3 / PU_15K`) — include `isp_i2c_singleton` to name them, or pass the
numeric value.

---

## 5. API reference — `isp_voice_command_names` (optional phrases + custom words)

| Method | Returns | Purpose |
|--------|---------|---------|
| `cmdName(cmdId)` | `pStr` | pointer to the human phrase: a built-in phrase, a **registered custom** phrase, `(custom)` for an unregistered custom slot, or `(unknown)` for an unmapped ID |
| `registerCustomTable(pTable)` | `status` | validate + register an app's custom-word table (see §6); `REG_OK` or a `REG_E_*` reason |
| `clearCustomWords()` | — | forget all registered custom phrases |

```spin2
OBJ
    voice : "isp_voice_recognizer"
    names : "isp_voice_command_names"

' ... in your loop ...
id := voice.getCMDID()
if id <> 0
    debug("heard: ", zstr_(names.cmdName(id)))   ' e.g. "Go Forward"
```

---

## 6. Custom words (the 17 user-trainable slots, IDs 5-21)

### How custom words work on the device
Custom words are trained **on the module, by voice** (the user speaks them during the module's own
learning workflow — see the product card / reference doc). The module then recognizes them and
reports their **slot ID (5-21)** — but it **stores no text**. So your **application is the only
place** that knows "slot 7 means 'good night'."

### Telling the library what your custom words mean
Declare your custom vocabulary as an **inline table** in your DAT and register it once. Each entry is
**one index byte** (the custom slot) followed immediately by a **zero-terminated phrase**; a single
`0` byte ends the table. Phrases are variable length and may be multi-word.

```spin2
DAT ' ---- my application's custom voice words ----
myCustomWords
            byte    5, "open the garage door", 0     ' CMD_CUSTOM_1
            byte    6, "turn on the shop lights", 0  ' CMD_CUSTOM_2
            byte    7, "good night", 0               ' CMD_CUSTOM_3
            byte    0                                 ' end of table

PUB setup() | status
    status := names.registerCustomTable(@myCustomWords)
    if status <> names.REG_OK
        debug("custom table rejected: ", sdec_(status))
```

After a successful register, `cmdName(7)` returns `"good night"` and any display that already calls
`cmdName()` shows the real phrase automatically — **no display code changes needed**.

### Why inline (not a table of pointers)
The strings live **inside** the table on purpose. A table of `@phrase` pointers built in your DAT
would store **object-relative** offsets that this object cannot resolve (different object base). The
inline form needs only the single absolute `@myCustomWords` you pass — see §9 for the `@`/`@@` detail.

### `registerCustomTable` is a one-time validator
It walks your table once and **registers nothing unless the whole table is valid** (all-or-nothing),
returning a reason code:

| Code | Meaning |
|------|---------|
| `REG_OK` (0) | table validated and registered |
| `REG_E_INDEX` (-1) | an index byte is outside the custom range (5-21) |
| `REG_E_UNTERMINATED` (-2) | a phrase had no `0` within `CUSTOM_MAXLEN` (63) bytes |
| `REG_E_TOO_MANY` (-3) | more than `CUSTOM_COUNT` (17) entries |
| `REG_E_DUP` (-4) | the same custom index appears twice |

Storage note: the library keeps only a small pointer per slot (`CUSTOM_COUNT` longs); your strings
stay in your DAT (permanent), so nothing is copied and nothing dangles.

---

## 7. The built-in command catalog

The full ID->phrase list (≈150 commands) is in **[`DOCs/COMMAND-CATALOG.md`](COMMAND-CATALOG.md)** —
generated from `tools/cmdname_catalog.tsv`, so it never drifts from the code. React by ID using the
`voice.CMD_*` constants:

```spin2
case voice.getCMDID()
    voice.CMD_GO_FORWARD: ...     ' ID 22
    voice.CMD_RETREAT:    ...     ' ID 23
```

Custom slots are IDs 5-21 (`CMD_CUSTOM_1`..`CMD_CUSTOM_17`). **Validate IDs against the printed
command-word card for your firmware revision** — revisions have reshuffled lists.

---

## 8. DEBUG, timing, and troubleshooting

**DEBUG channels** (compile-time, zero overhead when off): set `DEBUG_MASK = (1 << DBG_I2C)` in
`isp_i2c_singleton` to trace bus bytes (channel 0), or `DEBUG_MASK = (1 << DBG_VOICE)` in
`isp_voice_recognizer` to trace recognitions/config (channel 1), then rebuild.

**Timing guarantees:** no `waitms` in any bus method; `>=50 ms` between actual CMDID reads is enforced
by a tick check (a too-soon poll returns the cached value); `playByCMDID` is fire-and-return with the
~1 s window exposed via `isSpeaking()`.

**Troubleshooting:**
- `start()` returns `FALSE` → wiring/address/pull-up. On a bare bench use `i2c.PU_1K5` (the weaker
  `PU_3K3` can idle the bus low).
- Reads always return 0 → ensure clock-stretching is intact in the I2C layer (the DF2301Q holds SCL
  low while preparing data; the singleton waits for it — do not remove that).
- `cmdName()` shows `(custom)` for a trained word → your app hasn't called `registerCustomTable`, or
  it returned a `REG_E_*` reason (check the return value).

---

## 9. For maintainers

**`@` vs `@@` (the addressing rule this object depends on):**
- In a **DAT** block, `@label` is an **object-relative** offset.
- In a **PUB/PRI** body, `@label` is an **absolute** hub address at runtime.
- To use a DAT-stored offset at runtime, convert with `@@` (`@@table[i]`).
The generated phrase table stores relative WORD offsets and reads them with `@@`; the custom-word
table is walked from the single absolute pointer the app passes, so no `@@` is needed there.

**Regenerating the phrase table / catalog** (source of truth = `tools/cmdname_catalog.tsv`):
- `python3 tools/gen_cmdname_table.py --apply` — re-splice `cmdName()` + the DAT table into
  `src/isp_voice_command_names.spin2` (between the `>>> GENERATED` markers).
- `python3 tools/gen_cmdname_table.py --catalog-md` — regenerate `DOCs/COMMAND-CATALOG.md`.
Edit the `.tsv`, run both; never hand-edit the generated regions.

---

## 10. Related documents

- `DOCs/spec/P2-Gravity-Voice-Sensor-Specification.md` — formal contract
- `DOCs/design/DRIVER-THEORY-OF-OPERATIONS.md` — internal design
- `DOCs/reference/THEORY-OF-OPERATIONS.md` — device protocol (I2C + UART), findings F1-F7
- `DOCs/COMMAND-CATALOG.md` — full built-in command-word list (generated)
