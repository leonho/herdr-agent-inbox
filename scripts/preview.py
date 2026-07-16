#!/usr/bin/env python3
"""fzf preview: word-wrapped recap + de-noised recent output for one agent pane."""
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import extract_recap, herdr_json  # noqa: E402

DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"

# TUI chrome that adds nothing to a summary view
CHROME_RE = re.compile(
    r"░|⏵⏵|shift\+tab to cycle|esc to interrupt|\(disable recaps in /config\)"
)


def rule(label, width):
    return f"{DIM}── {label} {'─' * max(0, width - len(label) - 4)}{RESET}"


def main():
    pane_id = sys.argv[1]
    width = int(os.environ.get("FZF_PREVIEW_COLUMNS") or 100)

    d = herdr_json("agent", "read", pane_id, "--source", "recent", "--lines", "80")
    text = d["result"]["read"]["text"]
    lines = text.splitlines()

    recap = extract_recap(text)
    if recap:
        print(rule("recap", width))
        print(textwrap.fill(recap, width=width))
        print()

    # De-noise the tail: drop rules/borders without words, chrome, prompt box.
    kept = []
    for line in lines:
        line = line.rstrip()
        if CHROME_RE.search(line):
            continue
        if line.strip() and not re.search(r"[A-Za-z0-9]", line):
            continue  # pure box-drawing / horizontal rules
        if line.strip() == "❯":
            continue
        if kept and not line.strip() and not kept[-1].strip():
            continue  # collapse blank runs
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()

    print(rule("recent output", width))
    for line in kept[-30:]:
        # truncate instead of wrapping: keeps tables and indents readable
        print(line if len(line) <= width else line[: width - 1] + "…")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"preview error: {e}", file=sys.stderr)
        sys.exit(1)
