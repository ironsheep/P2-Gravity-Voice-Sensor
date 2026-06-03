# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A Parallax Propeller 2 (P2) driver — written in **Spin2 / PASM2** — for the DFRobot
**DF2301Q "Gravity: Offline Voice Recognition Sensor"** (SKU SEN0539). The goal is a P2
object exposing the sensor's built-in command words plus user-trained custom commands.

This is a **greenfield port**. The driver source does not exist yet: `src/` and `DOCs/`
are empty. The work is to reimplement the behavior of the reference Arduino/C++ + Python
library (in `REF/DFRobot_DF2301Q-master/`) as idiomatic P2 code. Treat `REF/` as the
protocol specification — read it, don't ship it.

## Build / compile

The P2 compiler is **`pnut-ts`** (the PNut TypeScript port), installed to
`/usr/local/bin/pnut-ts` by the devcontainer's `postCreateCommand` from
`.devcontainer/pnut-ts-linux-arm64-015500.zip` (version 1.55.00). If the binary is
missing, that postCreate step has not run — reinstall by unzipping that archive.

- `pnut-ts <file.spin2>` compiles a top-level Spin2/PASM2 object to a P2 binary.
- `pnut-ts --help` for flags (compile-only, listing, debug, etc.) — check it rather than
  guessing options.

There is no test runner, linter, or package manager here; verification is compilation
plus on-hardware behavior.

## Authoritative reference for P2 work

Use the **`p2kb-mcp`** MCP server for anything about P2 silicon, the PASM2 instruction
set, or Spin2 syntax/methods — it is curated and version-tracked. Do **not** rely on web
search for "Propeller 2"; results are sparse and routinely conflate P1 with P2.

- `p2kb_get` / `p2kb_find` — instructions, methods, concepts.
- `p2kb_obex_find` / `p2kb_obex_get` / `p2kb_obex_download` — OBEX community objects.
  Before writing I2C or async-serial bit-banging from scratch, check OBEX for an existing
  P2 I2C/serial object to build on (the DF2301Q speaks plain I2C and 9600-baud UART).

## Protocol the driver must implement (from `REF/`)

The sensor offers **two independent transports**; mirror the reference's two-class split
(an I2C object and a UART object).

### I2C transport — `DFRobot_DF2301Q.cpp` / `.h`
- 7-bit address `0x64`. Simple register-then-byte access (write reg, write/read one byte).
- Registers: `CMDID`=0x02 (read), `PLAY_CMDID`=0x03 (write), `SET_MUTE`=0x04,
  `SET_VOLUME`=0x05, `WAKE_TIME`=0x06.
- `getCMDID`: read 1 byte from 0x02; **0 means "no command recognized."** The reference
  enforces a **50 ms** delay after each read so polling doesn't starve the module.
- `playByCMDID`: write the ID to 0x03; needs ~**1 s** to play. **ID − 1 enters wake
  state** in I2C mode.
- Register reads use an I2C repeated-START (write reg, then re-START to read) — preserve
  that, don't issue a STOP between the address write and the data read.

### UART transport — same files, `DFRobot_DF2301Q_UART`
- 9600 baud, 8N1. Framed, checksummed packets parsed by a byte-at-a-time state machine
  (`recvPacket`). Frame layout (note **little-endian** multi-byte fields):
  - header `0xF4 0xF5` (low byte first), `dataLength` u16-LE, `msgType`, `msgCmd`,
    `msgSeq`, `msgData[0..dataLength]` (max 8), checksum u16-LE, tail `0xFB`.
  - **Checksum = sum of all bytes from offset 4 (msgType) through end of msgData**, i.e.
    `dataLength + 3` bytes, emitted little-endian.
  - `msgSeq` increments per outbound packet.
- Recognition results arrive as `msgType = CMD_UP (0xA0)`; the command ID is `msgData[0]`.
- Outbound ops build a packet and call `sendPacket`: `playByCMDID`, `resetModule`
  (payload ASCII `"reset"`, ~3 s settle), `settingCMD` (volume / enter-wakeup /
  mute / wake-time, via `SET_CONFIG` 0x96).

All the `0x..` constants (msg types, sub-commands, ACK error codes, notify events) are
defined at the top of `REF/DFRobot_DF2301Q-master/DFRobot_DF2301Q.h` — port them as Spin2
`CON` symbols rather than re-deriving them.

The public surface to reproduce (see `keywords.txt` and the `examples/`): `begin`,
`getCMDID`, `playByCMDID`, `getWakeTime`, `setWakeTime`, `setVolume`, `setMuteMode`
(I2C); plus `resetModule`, `settingCMD` (UART).

## Conventions

From `.devcontainer/devcontainer.json`: **4-space indentation**, **LF** line endings,
trailing whitespace trimmed. Keep these in generated Spin2 files.
