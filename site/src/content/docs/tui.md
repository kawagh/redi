---
title: TUI
description: The terminal UI for browsing and editing issues, wiki pages and time entries.
---

```sh
redi --tui
```

The command line is fine for a single lookup, but when you want to read, create and update in
one sitting, the TUI is the more convenient way in. It lets you move between an issue, its
comments and the time logged against it while editing them.

![TUI demo](https://raw.githubusercontent.com/kawagh/redi/main/doc/demo.gif)

## Tabs

Three tabs, switched with `Tab` / `Shift-Tab`:

- **Issues**
- **Wiki**
- **Time entries**

## Keys

**The keys follow vim.** `j` / `k` to move, `gg` / `G` for top and bottom, `/` to search.

Whatever is available in the current tab is always shown in the status bar at the bottom:

```text
jk:move /:search f:filter p:project c:create u:update v:web ?:help q:quit
```

Press `?` for the help of the current tab. Only the keys used most often are listed here.

| Key | |
| --- | --- |
| `j` / `k` | Move down / up |
| `gg` / `G` | Jump to top / bottom |
| `Ctrl-d` / `Ctrl-u` | Half page down / up |
| `Enter` | Open the selected item |
| `/` | Search within the list |
| `n` / `N` | Next / previous match |
| `f` | Filter |
| `p` | Switch project |
| `c` | Create |
| `u` | Update |
| `D` | Delete |
| `v` | Open the item in a browser |
| `?` | Help for the current tab |
| `q` | Quit |
