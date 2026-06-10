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
the P2 — an idiomatic Spin2 object that a P2 application drops in to listen for spoken
commands and react to them.

## Status

**Shipping — v1.0.0.** The I2C driver is implemented and compiles clean under `pnut-ts`.
See [`CHANGELOG.md`](CHANGELOG.md) for what's in each release and the
[Releases page](https://github.com/ironsheep/P2-Gravity-Voice-Sensor/releases) for
downloadable bundles. To start using it, read [`DOCs/USER-GUIDE.md`](DOCs/USER-GUIDE.md)
(§0 is the minimal drop-in).

> **Transport scope:** the DF2301Q sensor speaks both **I2C** and **UART**; this driver
> implements the **I2C** transport. UART is not implemented.

## What the driver does

The core loop is simple: the sensor recognizes a phrase and hands the host a command ID;
the host decides what to do with it.

- **Listen for commands** — poll for the most recently recognized command word and read
  back its ID over I2C (`0` means "nothing recognized"; ~50 ms read spacing is enforced).
- **Speak replies** — trigger the module to play its built-in reply audio for a given
  command ID, and enter the wake state.
- **Configure the module** — set playback volume, mute/unmute, and the wake-state duration.

Every bus method is **non-blocking**, so the driver can be polled from a shared device-scanner
cog without stalling it. Three usage profiles (scanner-poll, self-poller cog, synchronous) are
documented in the user's guide.

### Command words

Each recognizable phrase maps to a fixed numeric ID. The module includes **~150 built-in
command words** (movement, display, media, lighting, climate, and more) plus a **wake
word**, and reserves **17 slots (IDs 5–21)** for user-trained custom commands. The full
command-word ID table is ported to Spin2 `CON` symbols (`voice.CMD_*`) so application code
references commands by name instead of magic numbers — see
[`DOCs/COMMAND-CATALOG.md`](DOCs/COMMAND-CATALOG.md). The optional `isp_voice_command_names`
object maps an ID back to its human phrase and lets your app register the text for its custom
slots.

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
| `src/` | the P2 Spin2/PASM2 driver: `isp_voice_recognizer` (driver), `isp_voice_command_names` (optional phrases), `isp_i2c_singleton` (shared bus), and `demo_voice_recognizer` (DEBUG-panel demo) |
| `examples/` | worked examples (e.g. `custom_words_example.spin2`) |
| `DOCs/` | documentation: `USER-GUIDE.md`, `COMMAND-CATALOG.md`, spec/design/reference, and `policy/` (authoring guide, changelog style, release process) |
| `tools/` | the command-catalog/table generator and `build-check.sh` (the local release gate) |
| `.github/workflows/` | the tag-triggered release-packaging workflow |
| `.devcontainer/` | dev container; installs the `pnut-ts` P2 compiler |

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
