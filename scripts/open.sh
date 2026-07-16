#!/usr/bin/env bash
set -euo pipefail

herdr="${HERDR_BIN_PATH:-herdr}"

# On narrow (mobile) clients the manifest's percentage popup wastes what
# little space there is; go full-screen instead. 64 matches herdr's default
# ui.mobile_width_threshold (single-column mobile layout at width <= 64).
mobile_threshold="${AGENT_INBOX_MOBILE_THRESHOLD:-64}"

client_width=""
if [ -n "${HERDR_PANE_ID:-}" ]; then
  client_width="$("$herdr" pane layout --pane "$HERDR_PANE_ID" 2>/dev/null |
    sed -n 's/.*"area":{[^}]*"width":\([0-9]\{1,\}\).*/\1/p')"
fi
if [ -z "$client_width" ]; then
  client_width="$("$herdr" api snapshot 2>/dev/null |
    sed -n 's/.*"area":{[^}]*"width":\([0-9]\{1,\}\).*/\1/p')"
fi

size_args=()
if [ -n "$client_width" ] && [ "$client_width" -le "$mobile_threshold" ]; then
  size_args=(--width 100% --height 100%)
fi

exec "$herdr" plugin pane open --plugin "${HERDR_PLUGIN_ID:-leonho.agent-inbox}" --entrypoint inbox ${size_args[@]+"${size_args[@]}"}
