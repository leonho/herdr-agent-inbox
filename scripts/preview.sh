#!/usr/bin/env bash
# fzf preview: full recap + recent output for one agent pane.
set -euo pipefail

herdr="${HERDR_BIN_PATH:-herdr}"
pane_id="$1"

"$herdr" agent read "$pane_id" --source recent --lines 60 |
  python3 -c '
import json, re, sys

d = json.load(sys.stdin)
text = d["result"]["read"]["text"]
lines = text.splitlines()

start = None
for i, l in enumerate(lines):
    if "※ recap:" in l:
        start = i
if start is not None:
    block = [lines[start].split("※ recap:", 1)[1].strip()]
    for l in lines[start + 1:]:
        if not l.strip() or l.startswith(("❯", "⏺", "─", "═")):
            break
        block.append(l.strip())
    recap = re.sub(r"\s+", " ", " ".join(block))
    recap = re.sub(r"\s*\(disable recaps in /config\)\s*$", "", recap)
    print("── recap ──────────────────────────────")
    print(recap)
    print()

print("── recent output ──────────────────────")
tail = [l for l in lines if l.strip()][-35:]
print("\n".join(tail))
'
