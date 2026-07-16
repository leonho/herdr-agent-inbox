#!/usr/bin/env bash
# Agent Inbox popup: triage-sorted agent list with recaps; Enter jumps to the agent.
set -euo pipefail

herdr="${HERDR_BIN_PATH:-herdr}"

# Pane commands are argv launches, not login shells; make sure fzf resolves.
PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export HERDR_BIN_PATH="${HERDR_BIN_PATH:-herdr}"

plugin_root="${HERDR_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
list_cmd="python3 '$plugin_root/scripts/agents.py'"

if ! command -v fzf >/dev/null 2>&1; then
  echo "agent-inbox: fzf is required (brew install fzf). Press any key to close." >&2
  read -rsn1
  exit 1
fi

set +e
sel="$(eval "$list_cmd" | fzf \
  --delimiter='\t' --with-nth=2,3,4 --nth=2,3,4 --tabstop=4 --no-multi \
  --prompt='agent> ' \
  --header='enter: jump to agent · ctrl-r: refresh · esc: close' \
  --bind "ctrl-r:reload($list_cmd)" \
  --preview "bash '$plugin_root/scripts/preview.sh' {1}" \
  --preview-window='down,55%,wrap')"
fzf_status=$?
set -e
[ "$fzf_status" -ne 0 ] && exit 0 # esc / ctrl-c / no match

pane_id="$(cut -f1 <<<"$sel")"
[ -n "$pane_id" ] && exec "$herdr" agent focus "$pane_id"
