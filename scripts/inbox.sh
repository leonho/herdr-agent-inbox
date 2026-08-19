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

# Keep the full screen available for the list on narrow/mobile clients. Use
# tput here because this script runs inside the newly opened popup pane, whose
# width can differ from the pane that launched it.
# A phone terminal can still be wider than Herdr's 64-column mobile-layout
# cutoff (80 columns is common), so use a separate, more generous threshold
# for deciding whether a split preview is useful.
preview_min_width="${AGENT_INBOX_PREVIEW_MIN_WIDTH:-100}"
terminal_width="$(tput cols 2>/dev/null || true)"
if [[ ! "$terminal_width" =~ ^[0-9]+$ ]]; then
  terminal_width="${COLUMNS:-0}"
fi

fzf_args=(
  --read0 --ansi --highlight-line --gap 1
  --delimiter='\t' --with-nth=2.. --no-multi
  --prompt='agent> '
  --bind "ctrl-r:reload($list_cmd)"
)
if [ "$terminal_width" -ge "$preview_min_width" ]; then
  fzf_args+=(
    --header='enter: jump to agent · ctrl-r: refresh · shift-↑/↓: scroll preview · esc: close'
    --bind='shift-up:preview-half-page-up,shift-down:preview-half-page-down'
    --preview "python3 '$plugin_root/scripts/preview.py' {1}"
    --preview-window='down,55%'
  )
else
  fzf_args+=(--header='enter: jump to agent · ctrl-r: refresh · esc: close')
fi

set +e
sel="$(eval "$list_cmd" | fzf "${fzf_args[@]}")"
fzf_status=$?
set -e
[ "$fzf_status" -ne 0 ] && exit 0 # esc / ctrl-c / no match

# multi-line entry: the hidden pane_id field is on the first line only
pane_id="$(head -n1 <<<"$sel" | cut -f1)"
[ -n "$pane_id" ] && exec "$herdr" agent focus "$pane_id"
