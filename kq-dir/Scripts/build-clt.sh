#!/usr/bin/env bash
# Build with the standalone Command Line Tools, without changing xcode-select.
set -euo pipefail
export DEVELOPER_DIR=/Library/Developer/CommandLineTools
if [[ ! -x "$DEVELOPER_DIR/usr/bin/swift" || ! -x "$DEVELOPER_DIR/usr/bin/python3" ]]; then
    echo 'Command Line Tools are required. Run xcode-select --install, then retry.' >&2
    exit 1
fi
exec "$DEVELOPER_DIR/usr/bin/python3" "$(dirname "$0")/build_clt.py" "$@"
