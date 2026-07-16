#!/usr/bin/env bash
set -euo pipefail

herdr="${HERDR_BIN_PATH:-herdr}"
exec "$herdr" plugin pane open --plugin "${HERDR_PLUGIN_ID:-leonho.agent-inbox}" --entrypoint inbox
