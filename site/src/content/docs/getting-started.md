---
title: Getting Started
description: Install redi, connect it to a Redmine instance, and open the TUI.
---

`redi` is a TUI/CLI tool for Redmine. It wraps the REST API and offers a TUI for people
working at a terminal, and a CLI that people and programs (agents, scripts) can both run.

![redi TUI](/redi/img/demo.gif)

## Install

The name on PyPI is `redtile`, not `redi`. Installing with
[uv](https://github.com/astral-sh/uv) is what I recommend.

```sh
uv tool install redtile
```

Check that it is there:

```sh
redi --version
```

## Initial setup

```sh
redi init
```

![redi init](/redi/img/init-en.gif)

It asks for the language (`en` / `ja`), then the Redmine URL and API key. The key is not
echoed. It then **checks that the connection works**, lists the projects it found so you can
pick the default one, and writes a profile to `~/.config/redi/config.toml`.

The API key is under **My account → API access key** in Redmine. If it is not there, an
administrator has to enable the REST API under **Administration → Settings → API**.

Environment variables work as an alternative to a profile — see
[Configuration](/redi/configuration/).

## Open the TUI

```sh
redi --tui
```

`j` / `k` to move, `Enter` to open, `?` for help, `q` to quit. See [TUI](/redi/tui/) for details.

## Or stay on the command line

```sh
redi issue            # list issues of the default project
redi issue view 160   # one issue
```

`redi issue` is shorthand for `redi issue list` — see
[Command Structure](/redi/cli/command-structure/) for the rule behind it.

## Where to go next

- [TUI](/redi/tui/) — tabs and keys
- [Command Structure](/redi/cli/command-structure/) — the rule every command follows
- [Plugin (Agent Skill + Hook)](/redi/cli/agent-skill/) — the plugin for coding agents
