#!/usr/bin/env bash
#
# build-check.sh -- the LOCAL RELEASE GATE.
#
# We cannot compile remotely, so this is the certification you run BEFORE tagging a release:
# it compiles every Spin2 source with pnut-ts and fails if ANY file fails to build.  It also
# stages the integration-kit and demo bundles into their flat zip layout and compiles them
# there, which certifies that each bundle is self-contained (pnut-ts resolves OBJ relative to
# the top file's own directory, so a bundle that compiles flat will compile for a downloader).
#
# Finally it checks the two halves of the version lock that live in the tree -- the CHANGELOG
# version of record and the driver's DRIVER_VERSION -- so drift is caught before you tag.  The
# tag itself is verified in CI (.github/workflows/release.yml).
#
# Usage:   tools/build-check.sh
# Exit:    0 = green (safe to tag/release),  non-zero = a file failed or versions drifted.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PNUT="${PNUT:-pnut-ts}"
fail=0

if ! command -v "$PNUT" >/dev/null 2>&1; then
    echo "ERROR: '$PNUT' not found on PATH (see CLAUDE.md for install)"; exit 2
fi

compile() {  # compile <dir> <topfile>
    local dir="$1" top="$2"
    if ( cd "$dir" && "$PNUT" "$top" >/dev/null 2>&1 ); then
        echo "  OK    $dir/$top"
    else
        echo "  FAIL  $dir/$top"; fail=1
    fi
}

echo "== 1. Compile every source object in place =="
for f in isp_voice_recognizer isp_i2c_singleton isp_voice_command_names \
         demo_voice_recognizer test_cmdname_roundtrip; do
    [ -f "src/$f.spin2" ] && compile "src" "$f.spin2"
done

echo "== 2. Compile bundles in their flat zip layout =="
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/kit"
cp src/isp_voice_recognizer.spin2 src/isp_i2c_singleton.spin2 \
   src/isp_voice_command_names.spin2 examples/custom_words_example.spin2 "$TMP/kit/"
compile "$TMP/kit" "custom_words_example.spin2"

mkdir -p "$TMP/demo"
cp src/isp_voice_recognizer.spin2 src/isp_i2c_singleton.spin2 \
   src/isp_voice_command_names.spin2 examples/custom_words_example.spin2 \
   src/demo_voice_recognizer.spin2 \
   src/panel_bg.bmp src/panel_font.bmp src/panel_hi.bmp "$TMP/demo/"
compile "$TMP/demo" "demo_voice_recognizer.spin2"

echo "== 3. Version lock (in-tree halves) =="
CHANGELOG_VER="$(grep -m1 -oE '^## v[0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
DRIVER_VER="$(grep -m1 -E '^DRIVER_VERSION' src/isp_voice_recognizer.spin2 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
echo "  CHANGELOG=$CHANGELOG_VER  driver version()=$DRIVER_VER"
if [ -z "$CHANGELOG_VER" ] || [ -z "$DRIVER_VER" ] || [ "$CHANGELOG_VER" != "$DRIVER_VER" ]; then
    echo "  FAIL  version drift -- align CHANGELOG.md top entry with DRIVER_VERSION, then tag v$CHANGELOG_VER"
    fail=1
else
    echo "  OK    tag this release  v$CHANGELOG_VER"
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "GREEN -- safe to commit, tag, and push."
else
    echo "RED -- fix the failures above; release is blocked."
fi
exit "$fail"
