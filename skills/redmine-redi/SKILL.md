---
name: redmine-redi
description: Read and write Redmine issues, wiki pages, time entries, news and attachments through the `redi` CLI. Use whenever a task involves Redmine — creating or updating a ticket, searching issues, logging hours, or editing a wiki page — instead of calling the REST API directly. Redmine のチケット・Wiki・作業時間をコマンドラインで操作する (redmine, redi, redtile, ticket, issue, 課題, チケット, 工数, wiki, 作業時間).
compatibility: Requires the `redi` CLI (PyPI package `redtile`, verified with 0.0.58), a profile configured in `~/.config/redi/config.toml`, and network access to a Redmine instance with the REST API enabled.
allowed-tools: "Bash(redi:*)"
---

# Working with Redmine via redi

Use the `redi` command for anything that goes through the Redmine REST API,
instead of calling the API directly.

```sh
redi -h              # available resources
redi <resource> -h   # actions and options for one resource
```

Most resources support `list` / `view` / `create` / `update` / `delete`, and each
has a short alias (`redi i` = `redi issue`, `redi p` = `redi project`,
`redi cf` = `redi custom_field`).

If the operation you need does not seem to exist, check `redi <resource> <action> -h`
for **every** action of that resource (including `update`) before falling back to
the REST API. Options often live on a different action than you expect — e.g.
attaching a file to an issue is `issue update --attach`, not `issue create`.

## Before you start: check which Redmine you are talking to

`redi` supports multiple **profiles** — each is a Redmine URL plus an API key.
Commands use `default_profile` unless you pass `--profile`, so the same command
can hit a different server than you expect.

```sh
redi config --full   # default_profile + every profile (URL, default project, language)
```

Every command accepts `--profile <name>`:

```sh
redi issue list --profile work
```

If a project you know exists does not show up, or a create fails with
`Project cannot be blank`, you are almost certainly on the wrong profile.

Note: there is no `redi config list`. Use `redi config --full`.

A profile may define `default_project_id`, in which case `--project_id` can be omitted.

## Before you write: check the text formatting

Check `text_formatting` and write body text in that syntax (`markdown` or
`textile`). If it is not set, assume `markdown`:

```sh
redi config   # ... text_formatting = "markdown" (or "textile")
```

Do not read `~/.config/redi/config.toml` directly — it contains API keys.

## Resolve IDs before writing

Redmine takes numeric IDs for project, tracker, status and priority. Look them up first:

```sh
redi project list          # "15 agent"
redi tracker list          # "2 機能"
redi issue_status list
redi issue_priority list
```

Add `--full` to any `list` to get JSON instead of the plain listing — use this
when you need to pick a value programmatically:

```sh
redi project list --full
```

## Reading issues

```sh
redi issue list                              # default project
redi issue list --project_id 15              # one project
redi issue list --status_id 1 --limit 10
redi issue list --limit 100                  # default is 25; the range and total go to stderr
redi issue list --offset 25 --limit 25       # next page
redi issue view 160                          # one issue
redi issue view 160 --full                   # JSON
redi issue view 160 --include watchers       # + watchers (see -h for the list)
redi search "keyword"                        # cross-resource search
redi search "keyword" --titles_only --open_issues
```

`--full` prints the issue object itself at the top level — there is no `{"issue": ...}`
wrapper, so use `.attachments`, not `.issue.attachments`. `attachments`, `journals`
(comments) and `relations` are always included; other associations such as
`children`, `changesets` or `watchers` need `--include`.

```sh
redi issue view 160 --full | jq '.attachments[] | {id, filename}'
redi issue view 160 --full | jq '.journals[].notes'
```

## Creating and updating issues

```sh
redi issue create "件名" --project_id 15 --tracker_id 2
redi issue create "件名" --description "本文" --tracker_id 1
redi issue update 160 --status_id 3 --done_ratio 50
redi issue comment 160 "コメント本文"
```

### Attaching files to an issue

Files are attached with `issue update --attach` (repeat it for several files;
`--notes` adds a comment in the same update):

```sh
redi issue update 160 --attach ./report.zip
redi issue update 160 --attach a.csv --attach b.csv --notes "添付しました"
```

`issue create` and `issue comment` have no attach option — create the issue first,
then attach with `issue update`. Do not reach for the other upload-like commands:

- `redi attachment` only operates on **existing** attachments (view / download / update / delete)
- `redi file create` uploads to the project's **Files** tab, not to an issue

### Required custom fields

Custom fields are set with `--custom_fields <id>=<value>` (comma separated for
several: `--custom_fields "1=0.0.58,5=foo"`).

A tracker may make some of them **required**, and the failure message names the
field but not its ID:

```text
- ユーザーcf cannot be blank
- Barcf cannot be blank
```

Look the IDs up before creating, checking `is_required` and which `trackers`
the field applies to:

```sh
redi custom_field list --full
```

Picking a tracker with no required custom fields is often the simpler fix.

## Passing long text

Pass file contents directly:

```sh
redi issue create "件名" --description "$(cat body.md)" --project_id 15
redi issue comment 160 "$(cat comment.md)"
```

Leaving `--description` with **no value** opens `$EDITOR`, so only do that in an
interactive terminal:

```sh
redi issue create "件名" --description   # opens an editor — interactive only
```

If a create or update is rejected, the body is written to a temp file rather than
being lost, so you can fix the arguments and resend it:

```text
送信に失敗したため、本文を一時ファイルに保存しました: /tmp/redi-xxxx.md
```

## Non-interactive use

`redi` never blocks waiting for input when there is no TTY. If a required value
is missing it names what it wanted and exits 1:

```text
非対話環境のため入力を受け付けられません: トラッカーを選択
引数・オプションで指定して再実行してください
```

So supply everything as flags, and treat exit 1 as "add the argument it named".

## Other resources

```sh
redi wiki list
redi wiki view "ページ名"
redi wiki create "ページ名" --description "$(cat page.md)"

redi time_entry create 1.5 --issue_id 160 --activity_id 9
redi time_entry list --project_id 15

redi news list
redi attachment download 42 --output ./file.pdf
redi file list --project_id 15
```
