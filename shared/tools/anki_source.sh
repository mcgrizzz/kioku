#!/bin/bash
# Check out Anki's source at ANKI_TAG (shared/versions.env) into <dir> and
# apply shared/patches/anki-*.patch. With ANKI_REF set, the source is that
# commit of ANKI_REPO (a fork based on ANKI_TAG) instead. Run again after
# ANKI_TAG or ANKI_REF changes: a checkout of another tag or commit is replaced
# (its target/ is kept, so Rust rebuilds incrementally), and the patches are
# reapplied onto clean sources when they changed.
# Usage: anki_source.sh <dir>
set -euo pipefail
SHARED=$(cd "$(dirname "$0")/.." && pwd)
source "$SHARED/versions.env"
DIR=$1
ANKI_REF=${ANKI_REF:-}
ANKI_REPO=${ANKI_REPO:-https://github.com/ankitects/anki}

if [ -n "$ANKI_REF" ]; then
    WHAT="$ANKI_REPO at $ANKI_REF"
    current() { [ "$(git -C "$DIR" rev-parse HEAD 2> /dev/null)" = "$ANKI_REF" ]; }
else
    WHAT="Anki $ANKI_TAG"
    current() { [ "$(git -C "$DIR" describe --tags --exact-match 2> /dev/null)" = "$ANKI_TAG" ]; }
fi

if ! current; then
    # $DIR may hold an older checkout, or target/ alone (restored by CI's
    # Rust cache)
    rm -rf "$DIR.new"
    if [ -n "$ANKI_REF" ]; then
        # GitHub serves any commit by its full sha
        git init -q "$DIR.new"
        git -C "$DIR.new" remote add origin "$ANKI_REPO"
        git -C "$DIR.new" fetch -q --depth 1 origin "$ANKI_REF"
        git -C "$DIR.new" -c advice.detachedHead=false checkout -q FETCH_HEAD
    else
        git -c advice.detachedHead=false clone -q --depth 1 --branch "$ANKI_TAG" https://github.com/ankitects/anki "$DIR.new"
    fi
    git -C "$DIR.new" submodule update -q --init --depth 1
    [ -d "$DIR/target" ] && mv "$DIR/target" "$DIR.new/"
    # Anki's own build tree (the wheels, build_anki_wheels.sh) is kept too
    [ -d "$DIR/out" ] && mv "$DIR/out" "$DIR.new/"
    rm -rf "$DIR" && mv "$DIR.new" "$DIR"
fi

applied() {
    for patch in "$SHARED"/patches/anki-*.patch; do
        git -C "$DIR" apply -R --check "$patch" 2> /dev/null || return 1
    done
}
if ! applied; then
    # back to the release's sources (target/ and out/ are ignored, so kept)
    git -C "$DIR" checkout -q -- .
    git -C "$DIR" clean -fdq
    for patch in "$SHARED"/patches/anki-*.patch; do
        if ! git -C "$DIR" apply "$patch"; then
            echo "$patch does not apply to $WHAT; see shared/patches/README.md" >&2
            exit 1
        fi
    done
fi
