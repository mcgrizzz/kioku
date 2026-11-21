#!/bin/bash
# Build aqt's and anki's wheels from an Anki source checkout (anki_source.sh),
# for builds from a fork (ANKI_REF in shared/versions.env), whose wheels are
# not on PyPI. Uses Anki's own build (./ninja wheels: it fetches node, yarn and
# its Python itself; needs rustup, protoc, git). Prints the folder that holds
# exactly one aqt-*.whl and one anki-*.whl.
#
# The build hash in the wheels must match the one built into rsbridge
# (ios/tools/build_rust.sh, android/tools/build_rust.sh): both are the short
# sha of the checkout, written to out/buildhash, which Anki's build keeps when
# it exists.
# Usage: build_anki_wheels.sh <anki source dir>
set -euo pipefail
DIR=$(cd "$1" && pwd)
LOG=$DIR/out/kioku-wheels.log

mkdir -p "$DIR/out"
HASH=$(git -C "$DIR" rev-parse --short=8 HEAD)
[ "$(cat "$DIR/out/buildhash" 2>/dev/null)" = "$HASH" ] || echo "$HASH" > "$DIR/out/buildhash"
# a wheel of an earlier version would stay next to the new one
rm -rf "$DIR/out/wheels"

# not a release build: Rust in the dev profile (the anki wheel's native module
# is thrown away, the app links its own rsbridge), and the build hash file
# above is kept
(cd "$DIR" && env -u RELEASE ./ninja wheels) > "$LOG" 2>&1 || {
    tail -40 "$LOG" >&2
    echo "Anki's wheel build failed; full log: $LOG" >&2
    exit 1
}

count() { find "$DIR/out/wheels" -maxdepth 1 -name "$1" | wc -l | tr -d ' '; }
if [ "$(count 'aqt-*.whl')" != 1 ] || [ "$(count 'anki-*.whl')" != 1 ]; then
    echo "expected one aqt and one anki wheel in $DIR/out/wheels:" >&2
    ls -l "$DIR/out/wheels" >&2
    exit 1
fi
echo "$DIR/out/wheels"
