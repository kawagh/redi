---
title: プラグイン (Agent Skill + Hook)
description: Redmine が絡む作業でコーディングエージェントに redi を使わせる。
sidebar:
  order: 3
---

`redmine-redi` は、コーディングエージェント (Claude Code, Codex) に Redmine 操作を
`redi` で行わせるプラグインです。

`redi` の使用方法をエージェントに読み込ませる **Agent Skill** と、
設定ファイルの直接の読み取りを拒否する **`PreToolUse` hook** が同梱されています。

## プラグインをインストールする (推奨)

```sh
# Claude Code
/plugin marketplace add kawagh/redi
/plugin install redmine-redi@redi

# Codex
codex plugin marketplace add kawagh/redi
codex plugin add redmine-redi@redi
```

## スキルをインストールする

hook は付かないため、設定ファイルを読まないようスキルで促すだけになります。

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

# gh (v2.90+ と GitHub アカウントが必要)
gh skill install kawagh/redi redmine-redi --scope user
```
