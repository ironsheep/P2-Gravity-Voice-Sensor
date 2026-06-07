# P2-Gravity-Voice-Sensor overlay — p2-dev-cycle

## Augments §1 (Compile) and §3 (Flash to RAM and run) — the two-environment split

The project folder is shared between two environments with different P2 tool
availability:

- **In-container:** `pnut-ts` (compile) is available; `pnut-term-ts`
  (download/run) is **not**. The dev cycle runs §0–§1 and stops: a clean
  `pnut-ts -d` compile of {{SPIN2_TOP_FILE}} is the complete in-container bar.
  §2 (pre-flash sanity), §3 (flash to RAM and run), and §4–§5 (inspect /
  diagnose) cannot execute in-container — do **not** report the inability to
  flash as a failure; it is an environment limit, not a defect.
- **Host-native (Stephen's Mac):** both `pnut-ts` and `pnut-term-ts` are
  available — the full §1 → §3 → §4 compile → flash → DEBUG-observe cycle runs
  here.

State which environment you are in before claiming a cycle result; reaching §3+
requires a host-native session.
