# P2-Gravity-Voice-Sensor overlay — baseline-health

## Augments §2 (Run the full test suite) and §3 (Never allow skips) — host-only test leg

The baseline has two legs that live in different environments (shared project
folder, two toolchains):

- **Compile baseline (§1)** — `pnut-ts -d` zero-warning clean build. Runs in
  **both** container and host; fully measurable in-container.
- **Hardware test baseline (§2)** — {{TEST_COMMAND}} against
  {{CANONICAL_TEST_TARGET}}. Requires `pnut-term-ts`, which exists
  **host-native only**.

In-container, the hardware test leg is **environment-unavailable, not skipped**.
§3's "never allow skips" still holds — the test is not `.skip`/`xfail`/gated-out;
it runs on its canonical target (the host). An in-container hand-back must say
exactly: "compile-clean; hardware suite not exercised in-container — owed to a
host run," and must **never** report "green" as if the hardware leg passed.

## Augments §5 (Entry vs. exit baseline)

An entry or exit baseline is complete only after a **host-native** run. A
container-only measurement records the compile leg and explicitly marks the
hardware leg as not-yet-measured, to be completed host-side before the baseline
is treated as agreed.
