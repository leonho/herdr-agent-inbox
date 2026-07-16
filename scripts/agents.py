#!/usr/bin/env python3
"""Emit NUL-separated two-line fzf entries per agent, triage-sorted.

Entry format (tab separates the hidden pane_id from the display text):
    pane_id \t <status> <workspace>  <terminal title>\n    <recap/summary>

Mirrors the Agents sidebar rows: state + workspace + title, then the
Claude Code "recap" line (or the blocked prompt question) dimmed below.
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
STATUS_LABEL = {
    "blocked": "⛔ blocked",
    "done": "✅ done",
    "idle": "✳ idle",
    "unknown": "? unknown",
    "working": "⚙ working",
}
STATUS_COLOR = {
    "blocked": "\x1b[1;31m",  # bold red
    "done": "\x1b[32m",       # green
    "idle": "\x1b[36m",       # cyan
    "unknown": "\x1b[2m",     # dim
    "working": "\x1b[33m",    # yellow
}
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"

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
        if q:
            return q
    return recap or ""


def clip(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


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
        rows.append({
            "order": STATUS_ORDER.get(status, 3),
            "pane_id": agent["pane_id"],
            "status": status,
            "ws": ws_label.get(agent.get("workspace_id"), "?"),
            "title": agent.get("terminal_title_stripped") or "(untitled)",
            "summary": summarize(agent, text).replace("\t", " "),
        })

    rows.sort(key=lambda r: (r["order"], r["ws"]))
    status_w = max((len(STATUS_LABEL.get(r["status"], r["status"])) for r in rows), default=0)
    ws_w = max((len(r["ws"]) for r in rows), default=0)

    entries = []
    for r in rows:
        label = STATUS_LABEL.get(r["status"], r["status"])
        color = STATUS_COLOR.get(r["status"], "")
        line1 = (
            f"{color}{label:<{status_w}}{RESET}  "
            f"{BOLD}{r['ws']:<{ws_w}}{RESET}  "
            f"{clip(r['title'], 90)}"
        )
        summary = clip(r["summary"], 200) or "(no recap yet)"
        line2 = f"{'':<{status_w}}  {DIM}{summary}{RESET}"
        entries.append(f"{r['pane_id']}\t{line1}\n{line2}")

    sys.stdout.write("\0".join(entries))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"agent-inbox: {e}", file=sys.stderr)
        sys.exit(1)
