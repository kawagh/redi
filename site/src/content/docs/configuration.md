---
title: Configuration
description: config.toml and profiles.
---

## config.toml

Configuration lives in `~/.config/redi/config.toml` and consists of one or more **profiles**.
A profile is the configuration for one Redmine: its URL and API key, plus the project you
normally work in and the editor to open for long text.

```toml
default_profile = "default"
text_formatting = "markdown"  # default for all profiles

["default"]
redmine_url = "https://redmine.example.com"
redmine_api_key = "<your_api_key>"
default_project_id = "1"
wiki_project_id = "2"
editor = "nvim"
language = "en"

["work"]
redmine_url = "https://redmine.example.com"
redmine_api_key = "<your_api_key>"
default_project_id = "12"
text_formatting = "textile"   # overrides the top-level value for this profile only
```

### Top-level keys

| Key | |
| --- | --- |
| `default_profile` | Profile used when `--profile` is omitted |
| `text_formatting` | Default for every profile. A value inside a profile wins |

**`text_formatting` is the only key that can be set at the top level as a default for every
profile.** `editor` and `language` have no effect there.

### Keys inside a profile

| Key | |
| --- | --- |
| `redmine_url` | Base URL of the Redmine instance |
| `redmine_api_key` | API key of the user |
| `default_project_id` | Project assumed when `--project_id` is omitted |
| `wiki_project_id` | Project used by `redi wiki` |
| `editor` | Editor opened when a long text argument is left empty |
| `language` | `en` (default) or `ja` |
| `text_formatting` | `markdown` (default) or `textile`, matching how the server renders text |

Every command takes `--profile`, so you can read from another Redmine without switching
anything permanently.

```sh
redi issue list --profile work
redi config --full            # default_profile and every profile
```

## Creating and editing

| | |
| --- | --- |
| `redi init` | First-time setup. Asks for the language, then URL and API key, and verifies them |
| `redi config create` | Add another profile. Walks through the same steps |
| `redi config update` | Change one value |

Editing the file by hand works too.

## Environment variables

`REDMINE_URL` and `REDMINE_API_KEY` are read as an alternative to a profile, and take priority
over `config.toml`.

```sh
export REDMINE_URL=https://redmine.example.com
export REDMINE_API_KEY=<your_api_key>
```

## Shell completion

For zsh:

```sh
uv tool install argcomplete
echo 'eval "$(register-python-argcomplete redi)"' >> ~/.zshrc
```
