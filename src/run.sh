#!/bin/bash
# test.sh -- compile a P2 Spin2 top WITH DEBUG, then download-to-RAM and run it.
#
#   usage:  ./test.sh <basename>        e.g.  ./test.sh test_dog_stand
#           (the .spin2 extension is optional: ./test.sh test_dog_stand.spin2 also works)
#
# Operates on <basename>.spin2 in this script's own directory (src/), so it works
# from any current directory. Runs interactive at the project-standard 2 Mbaud; for
# an auto-exit headless capture add:  --headless --end-marker "<MARKER>" --timeout <s>
set -u

BAUD=2000000                                  # project standard: ALL P2 comms at 2 Mbaud

# the directory this script lives in (so basenames resolve regardless of cwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. a basename argument is required
if [[ $# -lt 1 || -z "${1:-}" ]]; then
    echo "usage: $(basename "$0") <basename>   e.g. $(basename "$0") test_dog_stand" >&2
    exit 2
fi

FILE="${1%.spin2}"                            # accept 'name' or 'name.spin2'
SRC="${SCRIPT_DIR}/${FILE}.spin2"
BIN="${SCRIPT_DIR}/${FILE}.bin"

# 2. the .spin2 source must be present
if [[ ! -f "$SRC" ]]; then
    echo "error: source not found: ${SRC}" >&2
    exit 1
fi

# 3. compile with DEBUG (quiet) -- bail if it fails, do NOT download
echo ">> compiling ${FILE}.spin2 (with DEBUG) ..."
if ! pnut-ts -d -q "$SRC"; then
    echo "error: compile FAILED -- not downloading." >&2
    exit 1
fi

# 4. compile OK -> download to RAM and run @ 2 Mbaud (exec so Ctrl-C goes to the terminal)
echo ">> download-to-RAM + run ${FILE}.bin @ ${BAUD} baud ..."
exec pnut-term-ts -r "$BIN" -b "$BAUD"
