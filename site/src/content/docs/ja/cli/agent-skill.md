---
title: エージェントスキル
description: Redmine が絡む作業でコーディングエージェントに redi を使わせる。
sidebar:
  order: 3
---

`redmine-redi` は、Redmine が絡む作業のときにコーディングエージェント (Claude Code, Codex) が
REST API を直接叩くのではなく `redi` を使うようにするスキルです。

配布形式は 2 つあります。エージェントに `~/.config/redi/config.toml` を読ませない hook が付く
**プラグイン**と、**スキル単体**です。

ユーザースコープでのインストールを推奨します。

## プラグインとしてインストールする

プラグインにはスキルと `PreToolUse` hook が同梱されています。エージェントが
API キーを含む `~/.config/redi/config.toml` を開こうとすると hook が拒否し、
代わりに `redi config` を使うよう促すため、キーが会話ログに残りません。

```sh
# Claude Code
/plugin marketplace add kawagh/redi
/plugin install redmine-redi@redi

# Codex
codex plugin marketplace add kawagh/redi
codex plugin add redmine-redi@redi
```

## スキル単体でインストールする

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
