# redi

redmine CLI tool

## install

Install via [uv](https://github.com/astral-sh/uv)

```shell
uv tool install https://github.com/kawagh/redi.git
```

## install(for development)

In repository root

```sh
uv tool install -e .
```

## setup

### config

To use redi, you need to set remdine url and redmine_api_key in one of below ways.

#### environment variable

```sh
export REDMINE_URL=xxx
export REDMINE_API_KEY=yyy
```

#### ~/.config/redi/config.toml

```toml
default_profile = "main"

["main"]
redmine_url = "xxx"
redmine_api_key = "yyy"
default_project_id = "1"
wiki_project_id = "2"
editor = "nvim"

["sub"]
redmine_url = "vvv"
redmine_api_key = "www"
default_project_id = "2"
wiki_project_id = "3"
editor = "code"
```

### setup completion

```sh
uv tool install argcomplete
echo 'eval "$(register-python-argcomplete redi)"' >> ~/.zshrc
```

## usage(example)

```sh
# config (alias: c)
redi config
redi config create <profile_name> --url <url> --api_key <key> # create new profile
redi config create <profile_name> --url <url> --api_key <key> --set_default
redi config update --default_profile <profile_name> # switch profile
redi config update <profile_name> --editor nvim # update profile
redi --profile <profile_name> issue # 一時的にプロファイルを切り替えて実行

# project (alias: p)
redi project # list projects
redi project view <project_id> # view project
redi project view <project_id> --include trackers,issue_categories
redi project create <name> <identifier>
redi project create <name> <identifier> -d "description" --is_public true
redi project update <project_id> --name renamed_project

# issue (alias: i)
redi issue # list issues
redi issue -p <project_id> -a me -s open
redi issue -q <query_id>
redi issue view <issue_id>
redi issue view <issue_id> --web # view issue with web browser
redi issue view <issue_id> --include journals,attachments,relations
redi issue create # (interactive)
redi issue create "subject" -p <project_id> -t <tracker_id> -a <user_id> -d "description"
redi issue update <issue_id> # (interactive)
redi issue update <issue_id> --status_id <status_id> -n "notes"
redi issue update <issue_id> --relate relates --to <other_issue_id>
redi issue update <issue_id> --attach ./foo.png --attach ./bar.log
redi issue comment <issue_id> "hello~"
redi issue delete <issue_id> # (confirm before delete)
redi issue delete <issue_id> -y # skip confirmation

# version (alias: v)
redi version # list versions(fixed_versions)
redi version -p <project_id>
redi version view <version_id>
redi version create <name> -p <project_id> --due_date 2026-12-31 --status open
redi version update <version_id> --status closed

# wiki (alias: w)
redi wiki
redi wiki -p <project_id>
redi wiki view <page_title>
redi wiki create # (interactive)
redi wiki update # (interactive)

# file (プロジェクトファイル)
redi file -p <project_id> # list
redi file create ./foo.zip -p <project_id> -d "description"

# attachment
redi attachment view <attachment_id>
redi attachment update <attachment_id> -f new_name.png -d "desc"
redi attachment delete <attachment_id> # confirm before delete (-y to skip)

# relation (イシュー関係性詳細)
redi relation view <relation_id>

# time_entry (作業時間)
redi time_entry -p <project_id> -u me
redi time_entry create 1.5 -i <issue_id> -a <activity_id> -c "comment"
redi time_entry update <time_entry_id> --hours 2.0
redi time_entry delete <time_entry_id> # confirm before delete (-y to skip)

# me (自分のアカウント)
redi me
redi me update -f <firstname> -l <lastname> -m <mail>

# membership (alias: m)
redi membership -p <project_id>
redi membership view <membership_id>

# news
redi news -p <project_id>

# issue_category
redi issue_category -p <project_id>
redi issue_category create "category" -p <project_id>

# others
redi user # list users (alias: u)
redi tracker # list trackers
redi issue_status # list issue statuses
redi issue_priority # list priorities
redi time_entry_activity # list activities
redi document_category # list document categories
redi role # list roles
redi group # list groups
redi custom_field # list custom fields
redi query # list custom queries
redi search "keyword"
redi --version
redi --tui
```
