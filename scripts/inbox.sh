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
  --read0 --ansi --highlight-line --gap 1 \
  --delimiter='\t' --with-nth=2.. --no-multi \
  --prompt='agent> ' \
  --header='enter: jump to agent · ctrl-r: refresh · shift-↑/↓: scroll preview · esc: close' \
  --bind "ctrl-r:reload($list_cmd)" \
  --bind 'shift-up:preview-half-page-up,shift-down:preview-half-page-down' \
  --preview "python3 '$plugin_root/scripts/preview.py' {1}" \
  --preview-window='down,55%')"
fzf_status=$?
set -e
[ "$fzf_status" -ne 0 ] && exit 0 # esc / ctrl-c / no match

# multi-line entry: the hidden pane_id field is on the first line only
pane_id="$(head -n1 <<<"$sel" | cut -f1)"
[ -n "$pane_id" ] && exec "$herdr" agent focus "$pane_id"
