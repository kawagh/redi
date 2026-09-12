---
title: 設定
description: config.toml とプロファイル。
---

## config.toml

設定は `~/.config/redi/config.toml` に置かれ、複数の**プロファイル**からなります。
プロファイルは接続先の Redmine に対する設定で、URL と API キーに加えて、普段作業する
プロジェクトや、長文を書くときに開くエディタを指定します。

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

["work"]
redmine_url = "https://redmine.example.com"
redmine_api_key = "<your_api_key>"
default_project_id = "12"
text_formatting = "textile"   # このプロファイルに限り最上位の値を上書きする
```

### トップレベルに書くキー

| キー | |
| --- | --- |
| `default_profile` | `--profile` を省略したときに使うプロファイル |
| `text_formatting` | 全プロファイルの既定値。プロファイル内の値が優先される |

**トップレベルに置けて全プロファイルの既定になるのは `text_formatting` だけです。**
`editor` や `language` はここに書いても効きません。

### プロファイルの中に書くキー

| キー | |
| --- | --- |
| `redmine_url` | Redmine の URL |
| `redmine_api_key` | ユーザーの API キー |
| `default_project_id` | `--project_id` を省略したときのプロジェクト |
| `wiki_project_id` | `redi wiki` が対象とするプロジェクト |
| `editor` | 長文の引数を空にしたときに開くエディタ |
| `language` | `en` (既定) または `ja` |
| `text_formatting` | `markdown` (既定) または `textile`。サーバー側のテキスト書式に合わせる |

すべてのコマンドが `--profile` を取るので、恒久的に切り替えずに別の Redmine を見られます。

```sh
redi issue list --profile work
redi config --full            # default_profile と全プロファイル
```

## 作成と編集

| | |
| --- | --- |
| `redi init` | 初回セットアップ。言語を尋ね、URL と API キーを疎通確認してから書き込みます |
| `redi config create` | プロファイルを追加する。同じ手順を辿ります |
| `redi config update` | 値を1つ変更する |

直接ファイルを編集しても構いません。

## 環境変数

`REDMINE_URL` と `REDMINE_API_KEY` はプロファイルの代わりに読まれ、`config.toml` より
優先されます。

```sh
export REDMINE_URL=https://redmine.example.com
export REDMINE_API_KEY=<your_api_key>
```

## シェル補完

zsh の場合:

```sh
uv tool install argcomplete
echo 'eval "$(register-python-argcomplete redi)"' >> ~/.zshrc
```
