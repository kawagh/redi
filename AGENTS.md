# AGENTS.md

This file provides guidance to Agents when working with code in this repository.

## Project

- `redi` は Redmine REST API を実行する Python 製 CLI/TUI
- Python 3.13+
- uv 管理
- PyPIでは`redtile`として配布されている

## Commands

- `task`(go-task) がタスクランナー
    ```
    $ task
    task: [default] task --list-all --sort none
    task: Available tasks for this project:
    * default:         list
    * check:           format, lint, typecheck, test
    * format:          format
    * lint:            lint
    * typecheck:       typecheck
    * test:            run tests (except E2E)
    * test:e2e:        run E2E tests (all target Redmine versions)
    * test:e2e:6.1:    run E2E tests against Redmine 6.1
    * test:e2e:7.0:    run E2E tests against Redmine 7.0
    * release:         release next version
    * demo:            generate demo
    ```

## CLI 設計方針

- 引数が不足する場合は対話的に入力させる
- ただしエージェントやCIが非TTY環境で実行できるよう、引数だけで完結する形も用意する
- 非TTY環境で引数が不足した場合は、対話に入らず何の入力を求めたかを示して exit 1 する
    - `redi.cli.interactive` の `prompt` / `ensure_interactive` を経由させる
    - `inline_choice` / `inline_checkbox` / `open_editor` は内部で `ensure_interactive` を呼んでいる

## TUI 設計方針

- 操作主体は人(非エージェント)
- 削除操作は誤操作の戻しやすさに応じて操作完了までの手間の大小を変える
    - issue: modal を開き issue_id を打ち直させる(issueに付随する添付ファイルやコメントが削除されるので重く見ている)
    - wiki: modal を開き `delete` と打たせる(版履歴ごと消えるので重く見ている。数値idが無く、タイトルは日本語もあり打ち直させられないため確認語にしている)
    - コメント : ステータスバーの y/N
    - time_entry : ステータスバーの y/N

## 層構造

- ※ コードの現状を示すものではなくあくまで志向
- `tui/`
- `cli/`
- `service/` : CLI や TUI と、 APIの間に入るコード
    - `api/` の役割が大きくなっているものを分割することと、CLI/TUI から呼び出しやすい構造にすることが目的。
    - `wiki_service`などredmineのリソース毎に作る
- `api/` : Redmine のAPI呼び出し、レスポンス型の定義

- 基本的には以下の依存関係を保つ
    - `tui` -> `service`
    - `cli` -> `service`
    - `service` -> `api`

## テスト

- 守りたい仕様をテストとして書く
- 実装やライブラリの都合でそうなっているだけの挙動はテストとして書かない
- HTTP の正しさは CLI の E2E (`task test:e2e`) で担保する
- docstring に守りたい仕様を日本語で書く(`pytest -v` に一覧として表示される)

## i18n

- 英語と日本語の二言語に対応している(デフォルトは英語)
- `src/redi/i18n/`に実装が集約されている
    - `_protocol.py`にキーを定義して`ja.py`と`en.py` で対応する値を実装する
    - `tests/unit/test_i18n.py`

