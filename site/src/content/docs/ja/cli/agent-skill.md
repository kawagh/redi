---
title: エージェントスキル
description: Redmine が絡む作業でコーディングエージェントに redi を使わせる。
sidebar:
  order: 3
---

`redmine-redi` は、Redmine が絡む作業のときにコーディングエージェント (Claude Code, Codex) が
REST API を直接叩くのではなく `redi` を使うようにするスキルです。

ユーザースコープでのインストールを推奨します。

## インストール

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

# gh (v2.90+ と GitHub アカウントが必要)
gh skill install kawagh/redi redmine-redi --scope user
```
