---
title: Command Structure
description: The rule that every redi command follows.
sidebar:
  order: 1
---

Almost every command has the same shape:

```text
redi <resource> <action> [<resource_id>] [options]
```

- `<resource>` — a Redmine resource: `issue`, `project`, `wiki`, `time_entry`, `news`, …
- `<action>` — `list`, `view`, `create`, `update`, `delete`, `comment`
- `<resource_id>` — the issue number or similar ID, for actions that target one item

## Resource and action

```sh
redi issue list         # list issues
redi issue view 160     # one issue
redi issue update 160 --status_id 3
```

`<resource_id>` is required for the actions that target one item: `view`, `update`, `delete`
and `comment`.

**`redi <resource>` on its own means `redi <resource> list`.**

```sh
redi issue              # same as: redi issue list
```

## Aliases

Both halves have short forms, so the commands stay short in daily use.

| | |
| --- | --- |
| Resources | `i` = `issue`, `p` = `project`, `te` = `time_entry`, `w` = `wiki`, `ij` = `issue_journal`, … |
| Actions | `l` = `list`, `v` = `view`, `c` = `create`, `u` = `update`, `d` = `delete`, `co` = `comment` |

```sh
redi i l                # redi issue list
```

`init`, `me` and `relation` have no alias.

## Global options

| Option | |
| --- | --- |
| `--profile <name>` | Use another Redmine for this one command. Works at every level |
| `--format <plain\|tsv\|json>` | Output format. `plain` (default) is the human-readable output, `tsv` is a header row plus tab-separated columns (`list` only), `json` is the raw JSON |
| `--full` | Alias of `--format json` |

`list` actions also take `--limit` / `--offset` for paging, plus filters that vary per resource.

### TSV output

`--format tsv` is meant for pipes and spreadsheets. `view` actions accept only `plain` / `json`.

```sh
redi query list --format tsv
redi query list --format tsv | column -t -s $'\t'   # aligned, wide characters included
redi issue list --format tsv | tail -n +2 | cut -f1    # ids only, skipping the header
```

- Header names are fixed in English regardless of `language` in your profile, so scripts keep working
- Tabs and newlines inside a value are collapsed to a single space, so one record is always one line
- `null` is an empty cell, booleans are `true` / `false`
- Columns are only ever appended at the end. Reordering or removing a column counts as a breaking change, so refer to columns by position or by header name with that in mind
