# テスト用のredmineの起動と接続方法

- リポジトリルートで実行
    ```sh
    docker compose up -d
    ```
- (初期ログインID,初期パスワード)=(admin,admin)
- パスワードの変更を実施
- 個人設定を保存
- ヘッダーの「管理」を押下
- デフォルト設定をロード
- ヘッダーの「管理」>「設定」>「API」を押下
- 「RESTによるWebサービスを有効にする」にチェックして保存
- ヘッダーの「個人設定」>「APIアクセスキー」>「表示」してコピー
- `~/.config/redi/config.toml`を以下のように設定する

```toml
redmine_api_key="<paste_api_key>"
redmine_url = "http://localhost:3000"
default_project_id = "1"
wiki_project_id = "1"
editor = "nvim"
```
