# P2-Gravity-Voice-Sensor overlay — test-playbook

## Augments §4 (Account for the verification surface's nature)

The verification surface is a P2 board wired to the DF2301Q, flashed over USB
with `pnut-term-ts`. Two project-specific constraints shape every exercise:

**1. Host-native only.** Any exercise that flashes / runs / observes hardware
can run **only on the host** (Mac + `pnut-term-ts`); the container can author
and compile the playbook but cannot execute hardware steps. Mark each hardware
exercise host-only so a container session knows to defer it.

**2. DEBUG-display rendering limits (learned over many flashes).**

- PLOT vector `TEXT` is **not** rendered usefully (position / color / textsize
  are ignored) — panel text must be pre-rendered `crop` bitmaps; use a **TERM
  window** for variable/arbitrary text.
- A TERM-window create line takes **no** `color` token (it silently breaks
  window construction, and the window then drops all routed output).
- Named windows require the backtick/TIC form `` debug(`name …) ``; plain
  `debug("…", UDEC_(v))` only reaches the default terminal.
- TERM control bytes: `12` = clear+home (not `0`), `13` = newline (no
  auto-newline), `9` = tab, `8` = backspace.

Full detail: the `debug-display-host-quirks` auto-memory and
`DOCs/dbg-display-theory/`.
