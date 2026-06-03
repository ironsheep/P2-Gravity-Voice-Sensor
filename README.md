# P2-Gravity-Voice-Sensor

A **Parallax Propeller 2 (P2)** driver — written in Spin2 / PASM2 — for the DFRobot
**DF2301Q "Gravity: Offline Voice Recognition Sensor"** (SKU **SEN0539**).

The DF2301Q is a self-contained, **offline** speech-recognition module: all recognition
happens on the sensor itself, with no cloud or network. Per DFRobot it ships with
**150 fixed, built-in commonly-used command words** plus a **command-word self-learning
function** for user-trained custom commands, and reports each recognized phrase to the
host as a numeric **command ID**. It has dual microphones for
noise rejection, an on-board speaker (plus an external-speaker header) for spoken replies,
and talks to a host over either **I2C** or **UART**.

This repository is a **port** of DFRobot's
[reference Arduino/C++ and Python library](https://github.com/DFRobot/DFRobot_DF2301Q) to
the P2. The aim is an idiomatic Spin2 object that a P2 application can drop in to listen
for spoken commands and react to them.

## Status

**Early / greenfield.** No driver source exists yet — `src/` is empty and the work is
in progress. DFRobot's upstream library is the protocol specification we are porting from;
this README describes the intended driver.

## What the driver will do

The core loop is simple: the sensor recognizes a phrase and hands the host a command ID;
the host decides what to do with it.

- **Listen for commands** — poll for the most recently recognized command word and read
  back its ID (`0` means "nothing recognized"). On UART the module pushes a framed packet
  per recognition; on I2C the host polls a register.
- **Speak replies** — trigger the module to play its built-in reply audio for a given
  command ID (and, in I2C mode, enter the wake state).
- **Configure the module** — set playback volume, mute/unmute, and the wake-state
  duration; on UART also reset the module outright.

Two transports are supported, mirroring the reference library's split into separate I2C
and UART objects:

| | I2C | UART |
|---|---|---|
| Wiring | 7-bit address `0x64` | 9600 baud, 8N1 |
| Recognition | host polls the command-ID register (~50 ms spacing) | module pushes a checksummed packet; host parses a byte-stream state machine |
| Plug-and-play | Gravity I2C connector | Gravity UART connector |

Both are 3.3 V / 5 V tolerant via the standard Gravity interface.

### Command words

Each recognizable phrase maps to a fixed numeric ID. The module includes **150 built-in
command words** (movement, display, media, lighting, climate, and more) plus a **wake
word**, and reserves slots for **custom commands**. The full command-word ID table
(published in DFRobot's library) will be ported to Spin2 `CON` symbols so application
code can reference commands by name instead of magic numbers.

A few IDs are special and relevant to training (below): `1` = wake-words-for-learning,
`46` = learn once, `47` = forget, `48`/`49` = load/save model, and `200`–`208` =
learn / re-learn / delete wake and command words.

## Teaching the sensor new words

The DF2301Q's "command word self-learning" is **driven entirely by voice** — there is no
separate training API on the wire. You put the module into learning mode and teach it a
phrase by *speaking to it*: say the learning wake word, issue the "learn" command, then
say your custom phrase; the module stores it against a custom-command slot. The host's
only role is the same two primitives it always has — **play prompt/confirmation audio**
(by command ID) and **observe which IDs come back**. So once the driver can read command
IDs and trigger playback, it can already drive a guided training session.

## Possible companion tooling (exploratory, not committed)

Because training is interactive, a small helper that *walks a person through* recording a
new word would be genuinely useful. We are **not committing** to building these — they are
noted as plausible follow-ons (DFRobot's upstream library has Arduino and Python examples
that show the host-side interaction in full):

- **A P2-native "word trainer"** — a Spin2 program that sequences the learning commands,
  plays the module's prompts, and confirms each recognized ID on a terminal or display,
  so a word can be taught with only the P2 and the sensor.
- **A macOS host tool** — a small command-line / desktop utility talking to the sensor
  over a USB-to-I2C or USB-to-serial bridge, to record, audit, and verify custom words
  from a laptop during bring-up and testing.

Scope and whether either is worth building will be decided once the core driver is
working on hardware.

## Repository layout

| Path | Contents |
|---|---|
| `src/` | P2 Spin2/PASM2 driver (to be written) |
| `DOCs/` | Project documentation, including `DOCs/policy/SPIN2-AUTHORING-GUIDE.md` (Spin2 coding standards) |
| `.devcontainer/` | Dev container; installs the `pnut-ts` P2 compiler |

## Building

The P2 compiler is **`pnut-ts`**, installed into the dev container. Compile a top-level
object with `pnut-ts <file.spin2>`; see `pnut-ts --help` for options.

## Hardware

- DFRobot DF2301Q Gravity Offline Voice Recognition Sensor — SKU **SEN0539**
  ([product page](https://www.dfrobot.com/)).
- A Parallax Propeller 2 board, connected over the Gravity I2C **or** UART interface.

## License

See [LICENSE](LICENSE). DFRobot's upstream library, which this driver is ported from, is
distributed by DFRobot under the MIT License.

## Credits

Ported from DFRobot's library (`qsjhyy`, 2022):
https://github.com/DFRobot/DFRobot_DF2301Q
