# `--debug-tui` 画面ログの YAML スキーマ

`redi --tui --debug-tui` で TUI を起動すると、描画のたびに直前のキーと画面の内容が
YAML ファイルに追記される。TUI の表示を後から追ったり、エージェントに画面を評価させる
用途 (#25 / #149) を想定している。

- 出力先: `~/.config/redi/redi-debug-tui-<起動時刻>.yaml`
    - `<起動時刻>` は `%Y-%m-%dT%H-%M-%S` 形式 (例: `redi-debug-tui-2026-08-23T12-34-56.yaml`)
    - 起動ごとに新しいファイルが作られる
- 実装: `src/redi/tui/screen_log.py`
- 仕様テスト: `tests/unit/tui/test_screen_log.py`
- 機械可読なスキーマ: `doc/redi-debug-tui.schema.yaml` (JSON Schema 2020-12。
  出力がこれに適合することも仕様テストで検証している)

## 構造

トップレベルはエントリのリスト。1 回の描画が 1 エントリになる。

```yaml
- timestamp: "2026-08-23T12:34:56.789012"
  key: "j"
  width: 120
  height: 40
  screen: |2
     Issues    Time entries    Wiki    Projects    News
    ────────────────────────────────────────
    #1 最初のチケット
```

| フィールド | 型 | 内容 |
| --- | --- | --- |
| `timestamp` | str | 描画時刻。`datetime.isoformat(timespec="microseconds")` 形式 |
| `key` | str | 描画の直前に処理されたキーシーケンス。複数キーはスペース区切り (例: `"g g"`)。起動直後など、キー入力を伴わない描画では空文字列 |
| `width` | int | 端末の桁数 |
| `height` | int | 端末の行数 |
| `screen` | str | 画面全体のテキスト。1 行が端末の 1 行に対応し、各行の末尾の空白は除去される。行数は `height` と一致する |

## 読み込み方

`yaml.safe_load` でそのまま読み戻せることを仕様として保証している
(`tests/unit/tui/test_screen_log.py`)。

```python
import glob, os
import yaml

path = sorted(glob.glob(os.path.expanduser("~/.config/redi/redi-debug-tui-*.yaml")))[-1]
entries = yaml.safe_load(open(path, encoding="utf-8"))
print(entries[-1]["key"])
print(entries[-1]["screen"])
```

## 書式上の注意 (#415)

パース可能性を守るため、書き出し側 (`_append_screen_yaml`) は次の 2 点を守っている。

- `screen` はインデント指示子付きのブロックスカラー `|2` で書く
    - YAML はブロックスカラーのインデント幅を最初の非空行から推定するため、
      タブバーのように画面の 1 行目が空白で始まると幅を誤推定してパースに失敗する。
      指示子は親ノードのインデントからの相対値なので、`|2` で 4 スペース固定になり、
      各行の先頭の空白がそのまま保たれる
- `key` は `json.dumps` でクォートして書く
    - 検索モードや削除確認の `<any>` バインドは任意の文字を受けるため、
      `#` `:` `-` などがそのまま書かれると YAML の特殊構文として解釈されて壊れる
- `timestamp` もクォートして書く
    - クォートしないと YAML の timestamp 型として解釈され、`yaml.safe_load` が
      `datetime` オブジェクトを返してしまう。文字列に固定する

ファイルは追記のみで書かれるため、TUI の異常終了時でもそれまでのエントリは
そのまま読める。
