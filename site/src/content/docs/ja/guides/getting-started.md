---
title: はじめに
description: redi をインストールして Redmine につなぐ。
---

## インストール

PyPI 上の名前は `redi` ではなく `redtile` です。

```sh
uv tool install redtile
```

## 設定

`redi init` は言語 (`en` / `ja`) を尋ねたあと、Redmine の URL と API キーを聞きます。

```sh
redi init
```

プロファイルは `~/.config/redi/config.toml` に書き込まれます。

## 実行

```sh
redi --tui      # TUI を起動する
redi issue      # 既定プロジェクトのチケット一覧
redi issue view 160
```

すべてのコマンドで `--profile <name>` を指定でき、別の Redmine を参照できます。
