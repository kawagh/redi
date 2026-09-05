---
title: はじめに
description: redi をインストールし、Redmine につないで TUI を開くまで。
---

`redi` は Redmine の TUI/CLI ツールです。REST API をラップし、ターミナルを操作する人向けの
TUI と、人／プログラム (エージェント、スクリプト) のいずれもが実行できる CLI を提供します。

![redi の TUI](https://raw.githubusercontent.com/kawagh/redi/main/doc/demo.gif)

## インストール

PyPI 上の名前は `redi` ではなく `redtile` です。
[uv](https://github.com/astral-sh/uv) でのインストールを勧めます。

```sh
uv tool install redtile
```

入ったか確認します。

```sh
redi --version
```

## 初期セットアップ

```sh
redi init
```

言語 (`en` / `ja`) を尋ねたあと Redmine の URL と API キーを聞き、
**疎通を確認してから** `~/.config/redi/config.toml` にプロファイルを書き込みます。
何も言われずに終われば接続できています。

API キーは Redmine の**個人設定 → API アクセスキー**にあります。見当たらない場合は
REST API が無効なので、管理者が**管理 → 設定 → API** から有効にします。

プロファイルの代わりに環境変数を使うこともできます。[設定](/redi/ja/configuration/) を参照してください。

## TUI を開く

```sh
redi --tui
```

`j` / `k` で移動、`Enter` で開く、`?` でヘルプ、`q` で終了。詳細は [TUI](/redi/ja/tui/) を参照してください。

## コマンドラインのまま使う

```sh
redi issue            # 既定プロジェクトのチケット一覧
redi issue view 160   # 1件の詳細
```

`redi issue` は `redi issue list` の省略形です。その原則は
[コマンド体系](/redi/ja/cli/command-structure/) にあります。

## 次に読むもの

- [TUI](/redi/ja/tui/) — タブとキー操作
- [コマンド体系](/redi/ja/cli/command-structure/) — コマンドの原則
- [エージェントスキル](/redi/ja/cli/agent-skill/) — エージェント向けのスキル
