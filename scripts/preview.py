#!/usr/bin/env python3
"""fzf preview: word-wrapped recap + the agent's last output block.

The "last block" is the final `⏺` assistant block — or, for a blocked agent,
everything from the last `⏺` through the approval box awaiting an answer.
"""
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import extract_recap, read_agent_output  # noqa: E402

DIM = "\x1b[2m"
RESET = "\x1b[0m"

# TUI chrome that adds nothing to a summary view
CHROME_RE = re.compile(
    r"░|⏵⏵|shift\+tab to cycle|esc to interrupt|\(disable recaps in /config\)"
)
SPINNER_RE = re.compile(r"^\s*[✻✽✢✳·∗] \S.*(…|\bfor \d+s\b)")
APPROVAL_RE = re.compile(r"(?i)do you want|esc to cancel|enter to select|allow this")
MAX_BLOCK_LINES = 60


def rule(label, width):
    return f"{DIM}── {label} {'─' * max(0, width - len(label) - 4)}{RESET}"


def denoise(lines):
    kept = []
    for line in lines:
        line = line.rstrip()
        if CHROME_RE.search(line) or SPINNER_RE.match(line):
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
    return kept


def last_block(kept):
    """The final ⏺ block to end-of-screen, and a label for it."""
    waiting = any(APPROVAL_RE.search(l) for l in kept[-40:])
    starts = [i for i, l in enumerate(kept) if l.lstrip().startswith("⏺")]
    if not starts:
        return kept[-30:], "recent output"
    block = kept[starts[-1]:]
    if waiting:
        # the approval box sits at the bottom; keep the tail
        return block[-MAX_BLOCK_LINES:], "waiting for approval"
    if len(block) > MAX_BLOCK_LINES:
        block = block[:MAX_BLOCK_LINES] + [f"{DIM}… (+{len(block) - MAX_BLOCK_LINES} more lines){RESET}"]
    return block, "last response"


def main():
    pane_id = sys.argv[1]
    width = int(os.environ.get("FZF_PREVIEW_COLUMNS") or 100)

    text = read_agent_output(pane_id)

    recap = extract_recap(text)
    if recap:
        print(rule("recap", width))
        print(textwrap.fill(recap, width=width))
        print()

    block, label = last_block(denoise(text.splitlines()))
    print(rule(label, width))
    for line in block:
        # truncate instead of wrapping: keeps tables and indents readable
        print(line if len(line) <= width else line[: width - 1] + "…")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"preview error: {e}", file=sys.stderr)
        sys.exit(1)
