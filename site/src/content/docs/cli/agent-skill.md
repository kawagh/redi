---
title: Plugin (Agent Skill + Hook)
description: Let coding agents reach for redi when a task involves Redmine.
sidebar:
  order: 3
---

`redmine-redi` makes coding agents (Claude Code, Codex) use `redi` for Redmine work.

It bundles an **Agent Skill** that teaches agents how to use `redi`, and a **`PreToolUse`
hook** that denies direct reads of the config file.

## Install Plugin (Recommended)

```sh
# Claude Code
/plugin marketplace add kawagh/redi
/plugin install redmine-redi@redi

# Codex
codex plugin marketplace add kawagh/redi
codex plugin add redmine-redi@redi
```

## Install Skill

The hook does not come along, so the skill only asks the agent not to read the config file.

```sh
# curl (Claude Code)
mkdir -p ~/.claude/skills/redmine-redi && \
  curl -sL https://raw.githubusercontent.com/kawagh/redi/main/plugins/redmine-redi/skills/redmine-redi/SKILL.md \
    -o ~/.claude/skills/redmine-redi/SKILL.md

# curl (Codex)
mkdir -p ~/.agents/skills/redmine-redi && \
  curl -sL https://raw.githubusercontent.com/kawagh/redi/main/plugins/redmine-redi/skills/redmine-redi/SKILL.md \
    -o ~/.agents/skills/redmine-redi/SKILL.md

# skills
npx skills add kawagh/redi --skill redmine-redi -g

# gh (needs v2.90+ and a GitHub account)
gh skill install kawagh/redi redmine-redi --scope user
```
