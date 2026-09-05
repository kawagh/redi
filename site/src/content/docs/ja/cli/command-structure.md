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
| `--format <plain\|json>` | 出力形式。`plain` (既定) は人が読む整形出力、`json` は生の JSON |
| `--full` | `--format json` の別名 |

`list` にはさらに `--limit` / `--offset` があり、リソースごとのフィルタも付きます。
