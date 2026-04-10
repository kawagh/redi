# redi

redmine を操作するコマンドラインツール

## インストール

[uv](https://github.com/astral-sh/uv)を使ってインストールする

```shell
uv tool install https://github.com/kawagh/redi.git
```

## インストール(開発用)

In repository root

```sh
ov tool install -e .
```

## 設定

### config

redmineのURLとAPIキーを以下のいずれか(環境変数、toml)で設定する必要がある
To use redi, you need to set remdine url and redmine_api_key in one of below ways.

#### 環境変数

```sh
export REDMINE_URL=xxx
export REDMINE_API_KEY=yyy
```

#### ~/.config/redi/config.toml

```toml
redmine_url = "xxx"
redmine_api_key = "yyy"
default_project_id = "1"
wiki_project_id = "2"
editor = "nvim"
```

- `redi config --project_id 1` としてプロジェクトIDを1に指定できる

### 補完の設定

```sh
uv tool install argcomplete
echo 'eval "$(register-python-argcomplete redi)"' >> ~/.zshrc
```

## 使用方法例

- プロジェクトを一覧する
    ```sh
    redi project # or `redi p`
    ```

- イシュー(チケット)を列挙する
    ```sh
    redi issue # or `redi i`
    ```

- イシュー詳細を確認する
    ```sh
    redi issue view <issue_id>
    ```
- イシューにコメントする
    ```sh
    redi issue comment <issue_id> # then editor open
    ```

- wikiを作成する(更新する)
    ```sh
    redi wiki create <page_title> --parent_title <parent_title>
    ```

- wikiを一覧する
    ```sh
    redi wiki -p <project_id> # project_idは`redi p`で取得できる
    ```

- ...
