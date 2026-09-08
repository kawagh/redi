---
title: コマンド体系
description: redi のコマンドが従っている原則。
sidebar:
  order: 1
---

ほぼすべてのコマンドが同じ形をしています。

```text
redi <resource> <action> [<resource_id>] [options]
```

- `<resource>` — `issue` `project` `wiki` `time_entry` `news` など、Redmine 側のリソース
- `<action>` — `list` `view` `create` `update` `delete` `comment`
- `<resource_id>` — 1件を対象にするアクションで指定するチケット番号などの ID

## リソースとアクション

```sh
redi issue list         # チケット一覧
redi issue view 160     # 1件の詳細
redi issue update 160 --status_id 3
```

`<resource_id>` は特定の1件を対象にするアクション (`view` / `update` / `delete` / `comment`)
で必要です。

**`redi <resource>` だけを打つと `redi <resource> list` の意味になります。**

```sh
redi issue              # redi issue list と同じ
```

## エイリアス

リソースにもアクションにも短縮形があり、日常的に打つコマンドが短く保たれます。

| | |
| --- | --- |
| リソース | `i` = `issue`, `p` = `project`, `te` = `time_entry`, `w` = `wiki`, `ij` = `issue_journal`, … |
| アクション | `l` = `list`, `v` = `view`, `c` = `create`, `u` = `update`, `d` = `delete`, `co` = `comment` |

```sh
redi i l                # redi issue list
```

`init` / `me` / `relation` にエイリアスはありません。

## グローバルオプション

| オプション | |
| --- | --- |
| `--profile <name>` | そのコマンドだけ別の Redmine を見る。どの階層でも指定できます |
| `--format <plain\|tsv\|json>` | 出力形式。`plain` (既定) は人が読む整形出力、`tsv` はヘッダー行 + タブ区切り (`list` のみ)、`json` は生の JSON |
| `--full` | `--format json` の別名 |
| `--no-header` | `tsv` 出力のヘッダー行を省く (`list` のみ) |

`list` にはさらに `--limit` / `--offset` があり、リソースごとのフィルタも付きます。

### TSV 出力

`--format tsv` はパイプや表計算ソフト向けです。`view` は `plain` / `json` のみ受け付けます。

```sh
redi query list --format tsv
redi query list --format tsv | column -t -s $'\t'   # 全角込みで列が揃う
redi issue list --format tsv --no-header | cut -f1     # id だけ取り出す
```

- ヘッダー名はプロファイルの `language` によらず英語固定です (i18n の対象外)。スクリプトが壊れないようにするためです
- 値の中のタブと改行は空白 1 つに潰し、1 レコード 1 行を守ります
- `null` は空セル、真偽値は `true` / `false` です
- 列は末尾に足すことしかしません。並べ替えや削除は破壊的変更として扱います
