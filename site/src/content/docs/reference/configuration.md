---
title: Configuration
description: Fields of config.toml.
---

Profiles live in `~/.config/redi/config.toml`. Create them with `redi init` or
`redi config create`, and edit them with `redi config update` or by hand.

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
```

| Key | Description |
| --- | --- |
| `default_profile` | Profile used when `--profile` is omitted |
| `redmine_url` | Base URL of the Redmine instance |
| `redmine_api_key` | API key of the user |
| `default_project_id` | Project assumed when `--project_id` is omitted |
| `wiki_project_id` | Project used by `redi wiki` |
| `editor` | Editor opened when a long text argument is left empty |
| `language` | `en` (default) or `ja` |
| `text_formatting` | `markdown` (default) or `textile`. Tells AI agents which markup Redmine renders |

A key inside a profile overrides the top-level value for that profile only.

Run `redi config --full` to see the resolved values of every profile.
