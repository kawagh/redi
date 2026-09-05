---
title: Agent Skill
description: Let coding agents reach for redi when a task involves Redmine.
sidebar:
  order: 3
---

`redmine-redi` is a skill that tells coding agents (Claude Code, Codex) to use `redi` when a
task involves Redmine, instead of calling the REST API by hand.

Installing at user scope is what I recommend.

## Install

```sh
# curl (Claude Code)
mkdir -p ~/.claude/skills/redmine-redi && \
  curl -sL https://raw.githubusercontent.com/kawagh/redi/main/skills/redmine-redi/SKILL.md \
    -o ~/.claude/skills/redmine-redi/SKILL.md

# curl (Codex)
mkdir -p ~/.agents/skills/redmine-redi && \
  curl -sL https://raw.githubusercontent.com/kawagh/redi/main/skills/redmine-redi/SKILL.md \
    -o ~/.agents/skills/redmine-redi/SKILL.md

# skills
npx skills add kawagh/redi --skill redmine-redi -g

# gh (needs v2.90+ and a GitHub account)
gh skill install kawagh/redi redmine-redi --scope user
```
