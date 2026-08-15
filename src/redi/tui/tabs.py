from redi.tui.issue.issue_tab import ISSUE_TAB
from redi.tui.state import TuiTab
from redi.tui.tab import TabView
from redi.tui.time_entry.time_entry_tab import TIME_ENTRY_TAB
from redi.tui.wiki.wiki_tab import WIKI_TAB

TABS: dict[TuiTab, TabView] = {
    "issues": ISSUE_TAB,
    "time_entries": TIME_ENTRY_TAB,
    "wiki": WIKI_TAB,
}
