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

![TUI tour](/redi/img/tui-tour-en.gif)

## Tabs

Three tabs, switched with `Tab` / `Shift-Tab`. The header shows the current tab, the profile
and the project you are looking at.

### Issues

![Issue list](/redi/img/tui-issues-en.png)

The list is on the left and the selected issue on the right — status, priority, tracker,
assignee, progress, spent hours and the description. Moving with `j` / `k` updates the right
pane as you go, so you can skim a list without opening anything.

The status bar shows the page you are on and how many issues matched.

### Time entries

![Time entries](/redi/img/tui-time-entries-en.png)

Hours logged in the project, newest first. The right pane shows which issue an entry belongs
to, so you can tell what the time was spent on without leaving the tab.

### Wiki

![Wiki tab](/redi/img/tui-wiki-en.png)

Pages are shown as a tree. To keep the tab responsive, **the body is not fetched until you
press `Enter`** — until then the right pane shows only the metadata.

![Wiki page body](/redi/img/tui-wiki-body-en.png)

## Search

Press `/` and type. Matches are highlighted in the list as you type, and `n` / `N` move
between them.

![Search](/redi/img/tui-search-en.png)

`/` searches the issues that are already loaded. To search the whole project on the server,
use `F` instead.

## Filter

Press `f`. Four columns — status, assignee, tracker and saved queries — moved between with
`Tab` / `h` / `l`.

![Filter](/redi/img/tui-filter-en.png)

`Enter` applies the filter and `c` clears every column at once. The filter that is in effect
stays visible in the status bar.

## Keys

**The keys follow vim.** `j` / `k` to move, `gg` / `G` for top and bottom, `/` to search.

Whatever is available in the current tab is always shown in the status bar at the bottom:

```text
jk:move /:search f:filter p:project c:create u:update v:web ?:help q:quit
```

Press `?` for the help of the current tab.

![Help](/redi/img/tui-help-en.png)

Only the keys used most often are listed here.

| Key | |
| --- | --- |
| `j` / `k` | Move down / up |
| `gg` / `G` | Jump to top / bottom |
| `Ctrl-d` / `Ctrl-u` | Half page down / up |
| `Enter` | Open the selected item |
| `/` | Search within the list |
| `n` / `N` | Next / previous match |
| `F` | Search issues on the server |
| `f` | Filter |
| `p` | Switch project |
| `P` | Switch profile |
| `c` | Create |
| `u` | Update |
| `D` | Delete |
| `v` | Open the item in a browser |
| `?` | Help for the current tab |
| `q` | Quit |
