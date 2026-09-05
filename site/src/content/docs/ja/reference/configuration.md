---
title: 設定
description: config.toml の項目。
---

プロファイルは `~/.config/redi/config.toml` に置かれます。`redi init` か
`redi config create` で作成し、`redi config update` または直接編集で変更します。

```toml
default_profile = "default"
text_formatting = "markdown"  # 全プロファイルの既定値

["default"]
redmine_url = "https://redmine.example.com"
redmine_api_key = "<your_api_key>"
default_project_id = "1"
wiki_project_id = "2"
editor = "nvim"
language = "ja"
```

| キー | 説明 |
| --- | --- |
| `default_profile` | `--profile` を省略したときに使うプロファイル |
| `redmine_url` | Redmine の URL |
| `redmine_api_key` | ユーザーの API キー |
| `default_project_id` | `--project_id` を省略したときのプロジェクト |
| `wiki_project_id` | `redi wiki` が対象とするプロジェクト |
| `editor` | 長文の引数を空にしたときに開くエディタ |
| `language` | `en` (既定) または `ja` |
| `text_formatting` | `markdown` (既定) または `textile`。Redmine がどちらの記法で描画するかを AI エージェントに伝える |

プロファイル内のキーは、そのプロファイルに限り最上位の値を上書きします。

`redi config --full` で全プロファイルの解決済みの値を確認できます。
