# redi

`redi` is a Redmine CLI/TUI tool that wraps the Redmine REST API.

## Quickstart

```sh
redi init                # interactive: enter Redmine URL and API key
redi --tui               # launch the TUI
redi issue               # or list issues
```

See [Setup](#setup) for profile / environment variable details and [Usage (examples)](#usage-examples) for the full command reference.

## Install

I recommend installation via [uv](https://github.com/astral-sh/uv).

```sh
uv tool install redtile  # name on PyPI is redtile, NOT redi
```

## Setup

### Config

To use redi, you need to set the Redmine URL and API key in one of the ways below.

#### redi init (interactive, recommended for first time)

```sh
redi init
```

Then, profile will be created in `~/.config/redi/config.toml` like below format.
You can also create profile by `redi config create`, and update profile by `redi config update` (and also by manual edit).

```toml
default_profile = "default"

["default"]
redmine_url = "https://redmine.example.com"
redmine_api_key = "<your_api_key>"
default_project_id = "1"
wiki_project_id = "2"
editor = "nvim"

["sub"]
redmine_url = "https://redmine.example.com"
redmine_api_key = "<your_api_key>"
default_project_id = "2"
wiki_project_id = "3"
editor = "code"
```

#### environment variable

```sh
export REDMINE_URL=https://redmine.example.com
export REDMINE_API_KEY=<your_api_key>
```


### Shell completion

```sh
uv tool install argcomplete
echo 'eval "$(register-python-argcomplete redi)"' >> ~/.zshrc
```

## Usage (examples)

Most commands follow the form:

```text
redi <resource> <action> [<resource_id>] [options]
```

- `<resource>` — `issue`, `project`, `wiki`, ... (most have a short alias such as `i` / `p` / `w`)
- `<action>` — `list` / `view` / `create` / `update` / `delete` / `comment` (also has aliases: `v` / `c` / `u` / `d` / `co`)
    - `redi <resource>` alone is shorthand for `redi <resource> list`
- `<resource_id>` — required for actions that target a specific item (`view`, `update`, `delete`, `comment`)

```sh
# init
redi init # interactive

# run TUI
redi --tui

# config (alias: c)
redi config
redi config create <profile_name> --url <url> --api_key <key> # create new profile
redi config create <profile_name> --url <url> --api_key <key> --set_default
redi config update --default_profile <profile_name> # switch profile
redi config update <profile_name> --editor nvim # update profile
redi --profile <profile_name> issue # temporarily switch profile for this command

# project (alias: p)
redi project # list projects
redi project list # same as above (`redi project l` / `redi p list` / `redi p l` / `redi p` also work)
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
redi issue update <issue_id> --start_date 2026-04-26 --due_date 2026-05-31 --estimated_hours 1.5
redi issue update <issue_id> --done_ratio 70
redi issue update <issue_id> --assigned_to_id <user_id>
redi issue update <issue_id> --assigned_to_id "" # unset assignee
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

# file (project files)
redi file -p <project_id> # list
redi file create ./foo.zip -p <project_id> -d "description"

# attachment
redi attachment view <attachment_id>
redi attachment update <attachment_id> -f new_name.png -d "desc"
redi attachment delete <attachment_id> # confirm before delete (-y to skip)

# relation (issue relation details)
redi relation view <relation_id>

# time_entry
redi time_entry -p <project_id> -u me
redi time_entry create 1.5 -i <issue_id> -a <activity_id> -c "comment"
redi time_entry update <time_entry_id> --hours 2.0
redi time_entry delete <time_entry_id> # confirm before delete (-y to skip)

# me (own account)
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
```

## Development

### install

```sh
uv tool install -e .
```

### task

Common tasks (managed by task runner [Task](https://taskfile.dev)):

```sh
task check       # format → lint → typecheck → test (run before opening a PR)
task format      # uv run ruff format
task lint        # uv run ruff check
task typecheck   # uv run ty check
task test        # uv run pytest -v
```

### Debug

```sh
redi --debug <command> # log request URLs and response status codes to ~/.config/redi/redi-debug.log
redi --debug-tui   # dump rendered TUI screens as YAML to log
```
