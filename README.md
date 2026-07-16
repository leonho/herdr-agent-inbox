# Agent Inbox (herdr plugin)

A popup triage list of every agent in your herdr session, so you stop cycling
through panes to figure out who needs you.

Each row shows the agent's status, workspace, and its latest Claude Code
`※ recap:` line (or the question it's blocked on). Rows are sorted by
what needs a decision first: **blocked → done → idle → working**. The preview
shows the full recap plus recent output. Press **Enter** to jump straight to
that agent's pane.

## Install

```sh
herdr plugin install leonho/herdr-agent-inbox
```

Or from a local checkout:

```sh
herdr plugin link /path/to/herdr-agent-inbox
```

Keybinding (config.toml):

```toml
[[keys.command]]
key = "alt+a"
type = "plugin_action"
command = "leonho.agent-inbox.open"
```

## Keys

| Key | Action |
|---|---|
| Enter | Focus the selected agent's pane (closes the popup) |
| ctrl-r | Refresh the list |
| Esc | Close |

## Requirements

- herdr ≥ 0.7.4 (popup plugin panes)
- `fzf`, `python3`

## How it works

`scripts/agents.py` calls `herdr agent list` and `herdr agent read --source
recent` per agent, extracts the last `※ recap:` block (Claude Code prints
one when a turn ends) or the blocked prompt question, and emits triage-sorted
TSV. `scripts/inbox.sh` renders it with fzf in a herdr popup pane and calls
`herdr agent focus` on selection.
