---
title: Agent Skill
description: Let coding agents reach for redi when a task involves Redmine.
sidebar:
  order: 3
---

`redmine-redi` is a skill that tells coding agents (Claude Code, Codex) to use `redi` when a
task involves Redmine, instead of calling the REST API by hand.

It ships two ways: as a **plugin**, which adds a hook that keeps agents out of
`~/.config/redi/config.toml`, or as the **skill on its own**.

Installing at user scope is what I recommend.

## Install as a plugin

The plugin bundles the skill with a `PreToolUse` hook. When an agent tries to open
`~/.config/redi/config.toml` — which holds your API keys — the hook denies the call and
points it at `redi config` instead, so the keys stay out of the conversation log.

```sh
# Claude Code
/plugin marketplace add kawagh/redi
/plugin install redmine-redi@redi

# Codex
codex plugin marketplace add kawagh/redi
codex plugin add redmine-redi@redi
```

## Install the skill on its own

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
