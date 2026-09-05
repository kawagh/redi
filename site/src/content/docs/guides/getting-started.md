---
title: Getting Started
description: Install redi and connect it to a Redmine instance.
---

## Install

The name on PyPI is `redtile`, not `redi`.

```sh
uv tool install redtile
```

## Configure

`redi init` asks which language to use (`en` / `ja`), then the Redmine URL and API key.

```sh
redi init
```

The profile is written to `~/.config/redi/config.toml`.

## Run

```sh
redi --tui      # launch the TUI
redi issue      # list issues of the default project
redi issue view 160
```

Every command accepts `--profile <name>` to talk to another Redmine.
