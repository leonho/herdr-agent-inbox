#!/usr/bin/env python3
"""Emit one TSV line per agent for the inbox picker, triage-sorted.

Columns: pane_id, status icon+word, workspace label, summary.
Summary is the agent's Claude Code "recap" line when present, else the
blocked prompt question, else the terminal title.
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
SELF_PANE = os.environ.get("HERDR_PANE_ID", "")

STATUS_ORDER = {"blocked": 0, "done": 1, "idle": 2, "unknown": 3, "working": 4}
STATUS_ICON = {
    "blocked": "⛔ blocked",
    "done": "✅ done",
    "idle": "✳ idle",
    "unknown": "? unknown",
    "working": "⚙ working",
}

RECAP_RE = re.compile(r"※ recap:")
DISABLE_HINT_RE = re.compile(r"\s*\(disable recaps in /config\)\s*$")


def herdr_json(*args):
    out = subprocess.run(
        [HERDR, *args], capture_output=True, text=True, timeout=10
    )
    if out.returncode != 0:
        raise RuntimeError(f"herdr {' '.join(args)}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def read_recent(pane_id, lines=150):
    try:
        d = herdr_json("agent", "read", pane_id, "--source", "recent", "--lines", str(lines))
        return d["result"]["read"]["text"]
    except Exception:
        return ""


def extract_recap(text):
    """Return the last '※ recap: ...' block joined to one line, or None."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if RECAP_RE.search(line):
            start = i
    if start is None:
        return None
    block = [RECAP_RE.split(lines[start], 1)[1].strip()]
    for line in lines[start + 1:]:
        if not line.strip():
            break
        # continuation lines are indented; a fresh prompt/rule ends the block
        if line.startswith(("❯", "⏺", "─", "═")):
            break
        block.append(line.strip())
    recap = " ".join(block)
    recap = DISABLE_HINT_RE.sub("", recap)
    return re.sub(r"\s+", " ", recap).strip() or None


def extract_blocked_prompt(text):
    """Best-effort question the agent is waiting on, from the bottom of the screen."""
    tail = [l.strip() for l in text.splitlines()[-40:] if l.strip()]
    question = None
    for line in tail:
        if line.endswith("?") or re.search(r"(?i)do you want|allow this|waiting for", line):
            question = line
    return question


def summarize(agent, text):
    status = agent.get("agent_status", "unknown")
    recap = extract_recap(text)
    if status == "blocked":
        q = extract_blocked_prompt(text)
        if q and recap:
            return f"{q} · last recap: {recap}"
        if q:
            return q
    if recap:
        return recap
    return agent.get("terminal_title_stripped") or "(no summary)"


def main():
    agents = herdr_json("agent", "list")["result"]["agents"]
    agents = [a for a in agents if a.get("pane_id") != SELF_PANE]
    workspaces = herdr_json("workspace", "list")["result"]["workspaces"]
    ws_label = {w["workspace_id"]: (w.get("label") or w["workspace_id"]) for w in workspaces}

    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(lambda a: read_recent(a["pane_id"]), agents))

    rows = []
    for agent, text in zip(agents, texts):
        status = agent.get("agent_status", "unknown")
        ws = ws_label.get(agent.get("workspace_id"), "?")
        summary = summarize(agent, text).replace("\t", " ")
        if len(summary) > 240:
            summary = summary[:239] + "…"
        rows.append((
            STATUS_ORDER.get(status, 3),
            agent["pane_id"],
            STATUS_ICON.get(status, status),
            ws,
            summary,
        ))

    rows.sort(key=lambda r: (r[0], r[3]))
    for _, pane_id, icon, ws, summary in rows:
        print(f"{pane_id}\t{icon}\t{ws}\t{summary}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"agent-inbox: {e}", file=sys.stderr)
        sys.exit(1)
