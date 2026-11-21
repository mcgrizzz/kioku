#!/bin/bash
# Assemble the site-packages that the iOS and native Android apps bundle:
# Anki's Python packages (from the PyPI wheels: aqt is pure Python with the
# web assets compiled, anki's wheel is only used for its Python files), the
# pure-Python dependencies, and the Python halves of orjson and markupsafe
# (their native parts are built into the app or not needed).
# With ANKI_REF set (a fork, shared/versions.env), aqt and anki are built from
# the Anki checkout next to <sdist dir> (deps/anki) instead of downloaded, or
# taken from $ANKI_WHEELS when set (built elsewhere from the same commit, as
# CI does on Linux: .github/workflows/ios-testflight.yml).
# Usage: prepare_site.sh <python with pip> <sdist dir> <output dir>
set -euo pipefail
SHARED=$(cd "$(dirname "$0")/.." && pwd)
source "$SHARED/versions.env"
PYTHON=$1
SDIST=$2
SITE=$3
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
rm -rf "$SITE" && mkdir -p "$SITE"

grep -vE '^(orjson|rpds-py|markupsafe)==|^ *#' "$SHARED/requirements.txt" > "$TMP/pure.txt"
if [ -n "${ANKI_REF:-}" ]; then
    ANKI_SRC=$(cd "$SDIST/.." && pwd)/anki
    [ "$(git -C "$ANKI_SRC" rev-parse HEAD 2>/dev/null)" = "$ANKI_REF" ] || {
        echo "$ANKI_SRC is not $ANKI_REF; run fetch_deps.sh first" >&2; exit 1; }
    WHEELS=${ANKI_WHEELS:-$("$SHARED/tools/build_anki_wheels.sh" "$ANKI_SRC")}
    mkdir -p "$TMP/wheels" "$TMP/anki"
    cp "$WHEELS"/aqt-*.whl "$TMP/wheels/"
    cp "$WHEELS"/anki-*.whl "$TMP/anki/"
    # rsbridge (build_rust.sh) refuses to load with another build hash than
    # the anki package's: catch that here rather than when the app starts
    HASH=$(git -C "$ANKI_SRC" rev-parse --short=8 HEAD)
    INFO=$(unzip -p "$TMP"/anki/anki-*.whl anki/buildinfo.py)
    case $INFO in *"'$HASH'"*) ;; *)
        echo "the anki wheel in $WHEELS was not built from $ANKI_SRC ($HASH):" >&2
        echo "$INFO" >&2; exit 1;;
    esac
    AQT=()
else
    AQT=("aqt==$ANKI_PY_VERSION")
fi
"$PYTHON" -m pip download -q --no-deps --only-binary :all: \
    --platform any --python-version "$PYTHON_VERSION" --implementation py --abi none \
    -d "$TMP/wheels" -r "$TMP/pure.txt" ${AQT[@]+"${AQT[@]}"}
if [ -z "${ANKI_REF:-}" ]; then
    "$PYTHON" -m pip download -q --no-deps --only-binary :all: \
        --platform manylinux_2_35_x86_64 -d "$TMP/anki" "anki==$ANKI_PY_VERSION"
fi
# -DD: today's time, not the wheel's fixed one (2020-02-02 in Anki's wheels),
# so a file of the same size in a new release isn't skipped by rsync -a
for w in "$TMP"/wheels/*.whl "$TMP"/anki/*.whl; do unzip -qo -DD "$w" -d "$SITE"; done
find "$SITE" -name '*.so' -delete

cp -R "$SDIST/markupsafe-$MARKUPSAFE_VERSION/src/markupsafe" "$SITE/"
rm -f "$SITE/markupsafe/_speedups.c"
cp -R "$SDIST/orjson-$ORJSON_VERSION/pysrc/orjson" "$SITE/"
