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

## テスト

- 守りたい仕様をテストとして書く
- 実装やライブラリの都合でそうなっているだけの挙動はテストとして書かない
- docstring に守りたい仕様を日本語で書く(`pytest -v` に一覧として表示される)

## i18n

- 英語と日本語の二言語に対応している(デフォルトは英語)
- `src/redi/i18n/`に実装が集約されている
    - `_protocol.py`にキーを定義して`ja.py`と`en.py` で対応する値を実装する
    - `tests/unit/test_i18n.py`

