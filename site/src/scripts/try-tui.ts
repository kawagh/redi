/**
 * redi の TUI の画面とキー操作をブラウザ上で再現する。
 *
 * データは script/init-redmine-demo.sh が投入するデモデータと同じ内容。
 * 実物と揃えているのは画面構成とキーバインドで、サーバとの通信や編集は含まない。
 */

type Lang = "en" | "ja";

type Issue = {
  id: number;
  subject: string;
  status: string;
  priority: string;
  tracker: string;
  progress: number;
  spent: number;
  description: string;
  closed?: boolean;
};

type TimeEntry = {
  id: number;
  hours: number;
  activity: string;
  issueId: number;
  issueSubject: string;
  comment: string;
};

type WikiPage = { title: string; body: string[] };

const COLS = 92;
const ROWS = 24;
const LEFT = 50; // 左ペインの幅。区切り線の位置

// ---------------------------------------------------------------- ANSI

const ESC = "\x1b[";
const reset = `${ESC}0m`;
const bold = (s: string) => `${ESC}1m${s}${reset}`;
const dim = (s: string) => `${ESC}2m${s}${reset}`;
// reverse video (SGR 7) は wterm がグリッド全体の背景に反映してしまうため、
// 背景色と前景色を明示して同じ見た目を作る
const invert = (s: string) => `${ESC}1m${ESC}4m${s}${reset}`;
const cyan = (s: string) => `${ESC}36m${s}${reset}`;
const magenta = (s: string) => `${ESC}35m${s}${reset}`;
const green = (s: string) => `${ESC}32m${s}${reset}`;

/** 表示幅。全角を 2 桁として数える */
function width(s: string): number {
  let w = 0;
  for (const ch of s) {
    const c = ch.codePointAt(0) ?? 0;
    w += c >= 0x1100 && (c <= 0x115f || (c >= 0x2e80 && c <= 0xa4cf) || (c >= 0xac00 && c <= 0xd7a3) || (c >= 0xf900 && c <= 0xfaff) || (c >= 0xff00 && c <= 0xff60)) ? 2 : 1;
  }
  return w;
}

/** 表示幅で切り詰める */
function clip(s: string, max: number): string {
  let out = "";
  let w = 0;
  for (const ch of s) {
    const cw = width(ch);
    if (w + cw > max) break;
    out += ch;
    w += cw;
  }
  return out;
}

function pad(s: string, max: number): string {
  return s + " ".repeat(Math.max(0, max - width(s)));
}

// ---------------------------------------------------------------- データ

const ISSUES_EN: Issue[] = [
  { id: 1, subject: "Login times out on slow networks", status: "In Progress", priority: "Urgent", tracker: "Bug", progress: 60, spent: 3.5, description: "Reported from a mobile network. The request gives up before the server responds." },
  { id: 2, subject: "Add CSV export to the issue list", status: "New", priority: "Normal", tracker: "Feature", progress: 0, spent: 0, description: "Needed for the monthly report. The same columns as the list view are enough." },
  { id: 3, subject: "Search results are not sorted by updated date", status: "New", priority: "Normal", tracker: "Bug", progress: 0, spent: 0, description: "The order looks random. It should follow the sort given on the command line." },
  { id: 4, subject: "Support multiple profiles in one config file", status: "Resolved", priority: "Normal", tracker: "Feature", progress: 100, spent: 3.0, description: "One file should hold several servers so that switching does not need an edit." },
  { id: 5, subject: "Document the non-interactive mode", status: "New", priority: "Low", tracker: "Support", progress: 0, spent: 0, description: "Explain what happens when a required argument is missing and there is no TTY." },
  { id: 6, subject: "Crash when the API key is empty", status: "In Progress", priority: "Urgent", tracker: "Bug", progress: 30, spent: 0.5, description: "A traceback is printed instead of a message telling the user what to fix." },
  { id: 7, subject: "Add a keyboard shortcut for filtering", status: "New", priority: "Normal", tracker: "Feature", progress: 0, spent: 0, description: "Opening the filter takes too many keys when going through a long list." },
  { id: 8, subject: "Update dependencies for the next release", status: "Closed", priority: "Normal", tracker: "Support", progress: 100, spent: 0, description: "Bump the pinned versions and run the whole test suite once.", closed: true },
  { id: 9, subject: "Wiki links break with non-ASCII titles", status: "New", priority: "High", tracker: "Bug", progress: 0, spent: 0, description: "Titles are not escaped, so a link to a Japanese page ends up pointing nowhere." },
  { id: 10, subject: "Improve the error message for an invalid tracker", status: "New", priority: "Low", tracker: "Feature", progress: 0, spent: 0, description: "Show the valid values instead of only saying that the value is wrong." },
  { id: 11, subject: "Add pagination to the time entry list", status: "New", priority: "Normal", tracker: "Feature", progress: 0, spent: 0, description: "Only the first page is shown and there is no sign that more entries exist." },
  { id: 12, subject: "Review how the API rate limit is handled", status: "Feedback", priority: "Normal", tracker: "Support", progress: 0, spent: 0, description: "Decide whether to retry, and how to tell the user that we are waiting." },
  { id: 13, subject: "Cache the project list between runs", status: "New", priority: "Low", tracker: "Feature", progress: 0, spent: 0, description: "The list rarely changes but is fetched on every command." },
  { id: 14, subject: "Attachments are not saved to the given path", status: "In Progress", priority: "High", tracker: "Bug", progress: 20, spent: 0, description: "The file always lands in the current directory, ignoring the option." },
  { id: 15, subject: "Ask for confirmation before deleting an issue", status: "Resolved", priority: "Normal", tracker: "Feature", progress: 100, spent: 0, description: "A single key press deletes the issue together with its comments." },
  { id: 16, subject: "Write an end-to-end test for the wiki commands", status: "New", priority: "Normal", tracker: "Support", progress: 0, spent: 0, description: "Wiki is the only resource without coverage in the e2e suite." },
  { id: 17, subject: "Time entries show the wrong date in some timezones", status: "Feedback", priority: "High", tracker: "Bug", progress: 0, spent: 0, description: "The date shifts by a day for users east of UTC." },
  { id: 18, subject: "Allow filtering issues by assignee", status: "New", priority: "Normal", tracker: "Feature", progress: 0, spent: 0, description: "Useful when several people share one project." },
];

const ISSUES_JA: Issue[] = [
  { id: 1, subject: "低速な回線でログインがタイムアウトする", status: "進行中", priority: "急いで", tracker: "バグ", progress: 60, spent: 3.5, description: "モバイル回線から報告あり。サーバの応答を待たずに諦めてしまう。" },
  { id: 2, subject: "チケット一覧に CSV エクスポートを追加する", status: "新規", priority: "通常", tracker: "機能", progress: 0, spent: 0, description: "月次レポートで必要。一覧と同じ項目が出れば十分。" },
  { id: 3, subject: "検索結果が更新日順に並ばない", status: "新規", priority: "通常", tracker: "バグ", progress: 0, spent: 0, description: "順序がばらばらに見える。コマンドラインで指定した並び順に従うべき。" },
  { id: 4, subject: "1 つの設定ファイルで複数プロファイルを扱えるようにする", status: "解決", priority: "通常", tracker: "機能", progress: 100, spent: 3.0, description: "複数のサーバを 1 ファイルに持てれば、切り替えるたびに編集せずに済む。" },
  { id: 5, subject: "非対話モードの使い方をドキュメントに書く", status: "新規", priority: "低め", tracker: "サポート", progress: 0, spent: 0, description: "必須の引数が無く TTY も無いときに何が起きるかを説明する。" },
  { id: 6, subject: "API キーが空のときにクラッシュする", status: "進行中", priority: "急いで", tracker: "バグ", progress: 30, spent: 0.5, description: "何を直せばよいか示すメッセージではなく、トレースバックが出てしまう。" },
  { id: 7, subject: "絞り込みのキーボードショートカットを追加する", status: "新規", priority: "通常", tracker: "機能", progress: 0, spent: 0, description: "長い一覧を見ているとき、絞り込みを開くまでのキー操作が多い。" },
  { id: 8, subject: "次のリリースに向けて依存関係を更新する", status: "終了", priority: "通常", tracker: "サポート", progress: 100, spent: 0, description: "固定しているバージョンを上げ、テストを一通り流す。", closed: true },
  { id: 9, subject: "日本語のタイトルだと Wiki のリンクが壊れる", status: "新規", priority: "高め", tracker: "バグ", progress: 0, spent: 0, description: "タイトルがエスケープされておらず、日本語ページへのリンクがどこにも繋がらない。" },
  { id: 10, subject: "不正なトラッカーを指定したときのエラーメッセージを改善する", status: "新規", priority: "低め", tracker: "機能", progress: 0, spent: 0, description: "値が不正だと言うだけでなく、有効な値を示す。" },
  { id: 11, subject: "作業時間の一覧にページングを追加する", status: "新規", priority: "通常", tracker: "機能", progress: 0, spent: 0, description: "1 ページ目しか出ず、続きがあることも分からない。" },
  { id: 12, subject: "API のレート制限の扱いを見直す", status: "フィードバック", priority: "通常", tracker: "サポート", progress: 0, spent: 0, description: "再試行するかどうかと、待っていることをどう伝えるかを決める。" },
  { id: 13, subject: "プロジェクト一覧を実行間でキャッシュする", status: "新規", priority: "低め", tracker: "機能", progress: 0, spent: 0, description: "めったに変わらないのに、コマンドごとに取得している。" },
  { id: 14, subject: "添付ファイルが指定したパスに保存されない", status: "進行中", priority: "高め", tracker: "バグ", progress: 20, spent: 0, description: "オプションを無視して、常にカレントディレクトリに置かれる。" },
  { id: 15, subject: "チケットを削除する前に確認する", status: "解決", priority: "通常", tracker: "機能", progress: 100, spent: 0, description: "キー 1 つでコメントごと消えてしまう。" },
  { id: 16, subject: "Wiki コマンドの E2E テストを書く", status: "新規", priority: "通常", tracker: "サポート", progress: 0, spent: 0, description: "E2E で覆われていないリソースは Wiki だけ。" },
  { id: 17, subject: "タイムゾーンによって作業時間の日付がずれる", status: "フィードバック", priority: "高め", tracker: "バグ", progress: 0, spent: 0, description: "UTC より東の利用者で日付が 1 日ずれる。" },
  { id: 18, subject: "担当者でチケットを絞り込めるようにする", status: "新規", priority: "通常", tracker: "機能", progress: 0, spent: 0, description: "複数人で 1 つのプロジェクトを使うときに要る。" },
];

const TIME_ENTRIES_EN: TimeEntry[] = [
  { id: 4, hours: 0.5, activity: "Design", issueId: 6, issueSubject: "Crash when the API key is empty", comment: "Reviewed the patch" },
  { id: 3, hours: 3.0, activity: "Design", issueId: 4, issueSubject: "Support multiple profiles in one config file", comment: "Implemented profile switching" },
  { id: 2, hours: 1.0, activity: "Design", issueId: 1, issueSubject: "Login times out on slow networks", comment: "Wrote a regression test" },
  { id: 1, hours: 2.5, activity: "Design", issueId: 1, issueSubject: "Login times out on slow networks", comment: "Investigated the timeout" },
];

const TIME_ENTRIES_JA: TimeEntry[] = [
  { id: 4, hours: 0.5, activity: "Design", issueId: 6, issueSubject: "API キーが空のときにクラッシュする", comment: "パッチのレビュー" },
  { id: 3, hours: 3.0, activity: "Design", issueId: 4, issueSubject: "1 つの設定ファイルで複数プロファイルを扱えるようにする", comment: "プロファイル切り替えの実装" },
  { id: 2, hours: 1.0, activity: "Design", issueId: 1, issueSubject: "低速な回線でログインがタイムアウトする", comment: "回帰テストの作成" },
  { id: 1, hours: 2.5, activity: "Design", issueId: 1, issueSubject: "低速な回線でログインがタイムアウトする", comment: "タイムアウトの調査" },
];

const WIKI_EN: WikiPage[] = [
  { title: "Coding_guidelines", body: ["# Coding guidelines", "", "- Keep the CLI usable without a TTY", "- Report failures on stderr", "- Write the specification you want to keep as a test"] },
  { title: "Release_notes", body: ["# Release notes", "", "## 0.2.0", "", "- Added CSV export", "- Fixed the login timeout on slow networks"] },
  { title: "Wiki", body: ["# Welcome", "", "This is the wiki of the demo project.", "", "- [Release notes](Release_notes)", "- [Coding guidelines](Coding_guidelines)"] },
];

const WIKI_JA: WikiPage[] = [
  { title: "Wiki", body: ["# ようこそ", "", "デモ用プロジェクトの Wiki です。", "", "- [リリースノート](リリースノート)", "- [コーディング規約](コーディング規約)"] },
  { title: "コーディング規約", body: ["# コーディング規約", "", "- TTY が無くても CLI が使える状態を保つ", "- 失敗は標準エラー出力に出す", "- 守りたい仕様はテストとして書く"] },
  { title: "リリースノート", body: ["# リリースノート", "", "## 0.2.0", "", "- CSV エクスポートを追加", "- 低速な回線でのログインタイムアウトを修正"] },
];

// ---------------------------------------------------------------- 文言

const L = {
  en: {
    tabs: ["Issues", "Time entries", "Wiki"],
    switch: "(Tab:switch)",
    fields: { status: "Status", priority: "Priority", tracker: "Tracker", parent: "Parent", assignee: "Assignee", author: "Author", start: "Start", due: "Due", progress: "Progress", est: "Est. hours", spent: "Spent hours", created: "Created", updated: "Updated" },
    teFields: { project: "Project", user: "User", activity: "Activity", issue: "Issue", created: "Created", updated: "Updated" },
    wikiFields: { parent: "Parent", version: "Version", created: "Created", updated: "Updated" },
    wikiHint: "(press Enter to load body)",
    statusIssues: "jk:move /:search f:filter p:project c:create u:update v:web ?:help q:quit",
    statusWiki: "jk:move /:search p:project c:create u:update D:delete v:web ?:help q:quit",
    page: (a: number, b: number, n: number) => `Page 1/1 (${a}-${b} / ${n})`,
    userFilter: "[user=me]",
    helpTitle: "Help - Issues tab (any key to close)",
    filterTitle: "Filter (Esc/f to close)",
    filterCols: ["Status", "Assignee", "Tracker", "Query"],
    filterHelp: "Tab/h/l:column jk:move Enter:apply c:clear all Esc/f:close",
    filterStatus: ["* open (default)", "all (open + closed)", "closed only", "New", "In Progress", "Resolved", "Feedback", "Closed", "Rejected"],
    filterAssignee: ["* (unspecified)", "me", "unassigned"],
    filterTracker: ["* (unspecified)", "Bug", "Feature", "Support"],
    filterQuery: ["* (unspecified)", "Issues assigned to me", "Reported issues", "Updated issues", "Watched issues"],
    quit: "Thanks for trying it. Press r or click Reset to start over.",
    help: [
      ["Navigation", ""],
      ["  up/k/Ctrl+P", "Move up"],
      ["  down/j/Ctrl+N", "Move down"],
      ["  gg / G", "First / last"],
      ["  Tab / Shift+Tab", "Switch tab (next / prev)"],
      ["Search", ""],
      ["  /", "Start search"],
      ["  n / N", "Next / previous match"],
      ["  Esc", "Clear search"],
      ["Filter", ""],
      ["  f", "Filter by status/assignee/tracker/query"],
      ["Other", ""],
      ["  ?", "Show / close help"],
      ["  q", "Quit"],
    ] as [string, string][],
  },
  ja: {
    tabs: ["イシュー", "作業時間", "Wiki"],
    switch: "(Tab:切替)",
    fields: { status: "ステータス", priority: "優先度", tracker: "トラッカー", parent: "親", assignee: "担当者", author: "作成者", start: "開始日", due: "期日", progress: "進捗", est: "予定工数", spent: "作業時間", created: "作成", updated: "更新" },
    teFields: { project: "プロジェクト", user: "ユーザー", activity: "作業分類", issue: "イシュー", created: "作成", updated: "更新" },
    wikiFields: { parent: "親", version: "バージョン", created: "作成", updated: "更新" },
    wikiHint: "(Enter で本文を読み込む)",
    statusIssues: "jk:移動 /:検索 f:フィルタ p:プロジェクト c:作成 u:更新 v:web ?:ヘルプ q:終了",
    statusWiki: "jk:移動 /:検索 p:プロジェクト c:作成 u:更新 D:削除 v:web ?:ヘルプ q:終了",
    page: (a: number, b: number, n: number) => `Page 1/1 (${a}-${b} / ${n})`,
    userFilter: "[user=me]",
    helpTitle: "ヘルプ - イシュータブ (任意のキーで閉じる)",
    filterTitle: "フィルタ (Esc/f で閉じる)",
    filterCols: ["ステータス", "担当者", "トラッカー", "クエリ"],
    filterHelp: "Tab/h/l:列切替 jk:移動 Enter:適用 c:全クリア Esc/f:閉じる",
    filterStatus: ["* open (デフォルト)", "全て (open + closed)", "closed のみ", "新規", "進行中", "解決", "フィードバック", "終了", "却下"],
    filterAssignee: ["* (指定なし)", "自分", "未割当"],
    filterTracker: ["* (指定なし)", "バグ", "機能", "サポート"],
    filterQuery: ["* (指定なし)", "ウォッチしているチケット", "報告したチケット", "担当しているチケット", "更新したチケット"],
    quit: "お試しありがとうございます。r かリセットでやり直せます。",
    help: [
      ["Navigation", ""],
      ["  up/k/Ctrl+P", "上に移動"],
      ["  down/j/Ctrl+N", "下に移動"],
      ["  gg / G", "先頭 / 末尾"],
      ["  Tab / Shift+Tab", "タブ切替 (次 / 前)"],
      ["Search", ""],
      ["  /", "検索を開始"],
      ["  n / N", "次 / 前の一致"],
      ["  Esc", "検索を解除"],
      ["Filter", ""],
      ["  f", "ステータス/担当者/トラッカー/クエリで絞り込む"],
      ["Other", ""],
      ["  ?", "ヘルプの表示 / 終了"],
      ["  q", "終了"],
    ] as [string, string][],
  },
};

// ---------------------------------------------------------------- 本体

export function createTui(lang: Lang, write: (s: string) => void) {
  const issues = lang === "ja" ? ISSUES_JA : ISSUES_EN;
  const entries = lang === "ja" ? TIME_ENTRIES_JA : TIME_ENTRIES_EN;
  const wiki = lang === "ja" ? WIKI_JA : WIKI_EN;
  const m = L[lang];

  const initial = () => ({
    tab: 0,
    cursor: [0, 0, 0],
    modal: null as null | "help" | "filter",
    filterCol: 0,
    search: null as null | string,
    searching: false,
    wikiLoaded: false,
    quit: false,
    pendingG: false,
  });
  let s = initial();

  const visibleIssues = () => {
    const open = issues.filter((i) => !i.closed);
    if (!s.search) return open;
    const q = s.search.toLowerCase();
    return open.filter((i) => i.subject.toLowerCase().includes(q));
  };

  function highlight(text: string): string {
    if (!s.search) return text;
    const q = s.search;
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx < 0) return text;
    return text.slice(0, idx) + invert(text.slice(idx, idx + q.length)) + text.slice(idx + q.length);
  }

  /** 画面を組み立てる。行の配列で返す */
  function build(): string[] {
    const lines: string[] = [];

    // ヘッダー
    const tabs = m.tabs.map((label, i) => (i === s.tab ? invert(` ${label} `) : ` ${label} `)).join("  ");
    lines.push(` ${tabs}   ${dim(m.switch)}  ${bold(magenta("[profile: demo_" + lang + "]"))}  ${bold(cyan("[project: redidemo]"))}`);
    lines.push("─".repeat(COLS));

    const body = s.tab === 0 ? buildIssues() : s.tab === 1 ? buildTimeEntries() : buildWiki();
    lines.push(...body);

    // 残りを埋め、区切り線の下にステータスバーを置く
    while (lines.length < ROWS - 2) lines.push("");
    lines.length = ROWS - 2;
    lines.push("─".repeat(COLS));
    lines.push(statusBar());
    return lines;
  }

  function twoPane(left: string[], right: string[]): string[] {
    const out: string[] = [];
    const rows = ROWS - 4;
    for (let i = 0; i < rows; i++) {
      const l = pad(left[i] ?? "", LEFT);
      const r = right[i] ?? "";
      out.push(`${l}│${r}`);
    }
    return out;
  }

  function buildIssues(): string[] {
    const list = visibleIssues();
    if (s.cursor[0] >= list.length) s.cursor[0] = Math.max(0, list.length - 1);
    const cur = list[s.cursor[0]];

    const left = list.map((it, i) => {
      const mark = i === s.cursor[0] ? green(">") : " ";
      const label = clip(`#${it.id} ${it.subject}`, LEFT - 3);
      return `${mark} ${highlight(label)}`;
    });

    const right: string[] = [];
    if (cur) {
      const f = m.fields;
      const w = Math.max(...Object.values(f).map(width));
      const row = (k: string, v: string) => `[${pad(k, w)}] ${v}`;
      right.push(clip(`#${cur.id} ${cur.subject}`, COLS - LEFT - 2));
      right.push("");
      right.push(row(f.status, cur.status));
      right.push(row(f.priority, cur.priority));
      right.push(row(f.tracker, cur.tracker));
      right.push(row(f.parent, "-"));
      right.push(row(f.assignee, "-"));
      right.push(row(f.author, "Redmine Admin"));
      right.push(row(f.start, "2026-09-07"));
      right.push(row(f.due, "-"));
      right.push(row(f.progress, `${cur.progress}%`));
      right.push(row(f.est, "-"));
      right.push(row(f.spent, `${cur.spent.toFixed(1)} h`));
      right.push(row(f.created, "2026-09-07T06:00:56Z"));
      right.push(row(f.updated, "2026-09-07T06:00:56Z"));
      right.push("");
      right.push("----");
      for (const line of wrap(cur.description, COLS - LEFT - 2)) right.push(line);
    }
    return twoPane(left, right);
  }

  function buildTimeEntries(): string[] {
    const cur = entries[s.cursor[1]];
    const left = entries.map((e, i) => {
      const mark = i === s.cursor[1] ? green(">") : " ";
      const label = clip(`${e.id}  (2026-09-07)  Redmine Admin  ${e.hours.toFixed(1)}h  ${e.activity}  #${e.issueId}`, LEFT - 3);
      return `${mark} ${label}`;
    });
    const right: string[] = [];
    if (cur) {
      const f = m.teFields;
      const w = Math.max(...Object.values(f).map(width));
      const row = (k: string, v: string) => `[${pad(k, w)}] ${v}`;
      right.push(`#${cur.id} ${cur.hours.toFixed(1)}h (2026-09-07)`);
      right.push("");
      right.push(row(f.project, "redi demo (id=1)"));
      right.push(row(f.user, "Redmine Admin (id=1)"));
      right.push(row(f.activity, cur.activity));
      right.push(row(f.issue, clip(`#${cur.issueId} ${cur.issueSubject}`, COLS - LEFT - 14)));
      right.push(row(f.created, "2026-09-07T06:00:46Z"));
      right.push(row(f.updated, "2026-09-07T06:00:46Z"));
      right.push("");
      right.push("----");
      right.push(cur.comment);
    }
    return twoPane(left, right);
  }

  function buildWiki(): string[] {
    const cur = wiki[s.cursor[2]];
    const left = wiki.map((p, i) => {
      const mark = i === s.cursor[2] ? green(">") : " ";
      const branch = i === wiki.length - 1 ? "└──" : "├──";
      return `${mark} ${branch} ${clip(p.title, LEFT - 8)}`;
    });
    const right: string[] = [];
    if (cur) {
      const f = m.wikiFields;
      const w = Math.max(...Object.values(f).map(width));
      const row = (k: string, v: string) => `[${pad(k, w)}] ${v}`;
      right.push(cur.title);
      right.push("");
      right.push(row(f.parent, "-"));
      right.push(row(f.version, "1"));
      right.push(row(f.created, "2026-09-07T06:01:12Z"));
      right.push(row(f.updated, "2026-09-07T06:01:12Z"));
      right.push("");
      right.push("----");
      if (s.wikiLoaded) {
        for (const line of cur.body) right.push(clip(line, COLS - LEFT - 2));
      } else {
        right.push(dim(m.wikiHint));
      }
    }
    return twoPane(left, right);
  }

  function statusBar(): string {
    if (s.searching) return bold(clip(`/${s.search ?? ""}`, COLS));
    if (s.tab === 0) {
      const list = visibleIssues();
      const page = list.length ? m.page(1, list.length, list.length) : m.page(0, 0, 0);
      return dim(clip(` ${page}  ${m.statusIssues}`, COLS));
    }
    if (s.tab === 1) {
      return dim(clip(` ${m.userFilter} ${m.page(1, entries.length, entries.length)}  ${m.statusIssues}`, COLS));
    }
    return dim(clip(` ${m.statusWiki}`, COLS));
  }

  function wrap(text: string, max: number): string[] {
    const out: string[] = [];
    let line = "";
    for (const ch of text) {
      if (width(line) + width(ch) > max) {
        out.push(line);
        line = "";
      }
      line += ch;
    }
    if (line) out.push(line);
    return out;
  }

  /** モーダルを画面の上に重ねる */
  function overlay(lines: string[], box: string[], title: string, top: number, left: number): string[] {
    const inner = Math.max(...box.map(width), width(title) + 4);
    const w = Math.min(inner + 2, COLS - left - 1);
    const head = `┌─${title}${"─".repeat(Math.max(0, w - width(title) - 3))}┐`;
    const framed = [head, ...box.map((b) => `│${pad(clip(b, w - 2), w - 2)}│`), `└${"─".repeat(w - 2)}┘`];
    const out = [...lines];
    framed.forEach((row, i) => {
      const y = top + i;
      if (y < 0 || y >= out.length) return;
      const base = out[y] ?? "";
      // ANSI を含む行に重ねると崩れるので、モーダル行は素の文字で作り直す
      const plain = stripAnsi(base);
      const before = pad(clip(plain, left), left);
      const after = plain.length > left + width(row) ? clip(plain.slice(left + row.length), COLS - left - width(row)) : "";
      out[y] = before + row + after;
    });
    return out;
  }

  function stripAnsi(s: string): string {
    return s.replace(/\x1b\[[0-9;]*m/g, "");
  }

  function render() {
    let lines = build();
    if (s.quit) {
      lines = Array(ROWS).fill("");
      lines[1] = ` ${green(m.quit)}`;
    } else if (s.modal === "help") {
      const w = Math.max(...m.help.map(([k]) => width(k))) + 2;
      const box = m.help.map(([k, v]) => (v ? `${pad(k, w)}  ${v}` : k ? bold(k) : ""));
      lines = overlay(lines, box, ` ${m.helpTitle} `, 2, 8);
    } else if (s.modal === "filter") {
      const cols = [m.filterStatus, m.filterAssignee, m.filterTracker, m.filterQuery];
      const widths = cols.map((c) => Math.max(...c.map(width)) + 2);
      const rows = Math.max(...cols.map((c) => c.length));
      const box: string[] = [];
      box.push(m.filterCols.map((c, i) => pad(i === s.filterCol ? bold(`[${c}]`) : `[${c}]`, widths[i] + (i === s.filterCol ? 8 : 0))).join(""));
      for (let r = 0; r < rows; r++) {
        box.push(cols.map((c, i) => pad(c[r] ? (r === 0 ? `> ${c[r]}` : `  ${c[r]}`) : "", widths[i] + 2)).join(""));
      }
      box.push("");
      box.push(m.filterHelp);
      lines = overlay(lines, box, ` ${m.filterTitle} `, 3, 4);
    }
    // 2J だけだと消した内容がスクロールバックに積まれてグリッドが伸び続けるため、
    // 3J (Erase Saved Lines) でスクロールバックごと消してから描き直す
    write(`${reset}${ESC}2J${ESC}3J${ESC}H` + lines.join("\r\n") + reset);
  }

  function move(delta: number) {
    const len = s.tab === 0 ? visibleIssues().length : s.tab === 1 ? entries.length : wiki.length;
    if (!len) return;
    s.cursor[s.tab] = Math.min(len - 1, Math.max(0, s.cursor[s.tab] + delta));
    if (s.tab === 2) s.wikiLoaded = false;
  }

  function handleInput(data: string) {
    if (s.quit) {
      if (data === "r") { s = initial(); render(); }
      return;
    }

    // 検索入力中
    if (s.searching) {
      if (data === "\r" || data === "\n") { s.searching = false; }
      else if (data === "\x1b") { s.searching = false; s.search = null; }
      else if (data === "\x7f") { s.search = (s.search ?? "").slice(0, -1); }
      else if (data >= " ") { s.search = (s.search ?? "") + data; s.cursor[0] = 0; }
      render();
      return;
    }

    if (s.modal === "help") { s.modal = null; render(); return; }
    if (s.modal === "filter") {
      if (data === "\x1b" || data === "f" || data === "\r") s.modal = null;
      else if (data === "\t" || data === "l") s.filterCol = (s.filterCol + 1) % 4;
      else if (data === "h") s.filterCol = (s.filterCol + 3) % 4;
      render();
      return;
    }

    switch (data) {
      case "j": case "\x1b[B": case "\x0e": move(1); break;
      case "k": case "\x1b[A": case "\x10": move(-1); break;
      case "G": s.cursor[s.tab] = 999; move(0); break;
      case "g":
        if (s.pendingG) { s.cursor[s.tab] = 0; s.pendingG = false; }
        else { s.pendingG = true; return; }
        break;
      case "\t": s.tab = (s.tab + 1) % 3; s.wikiLoaded = false; break;
      case "\x1b[Z": s.tab = (s.tab + 2) % 3; s.wikiLoaded = false; break;
      case "?": s.modal = "help"; break;
      case "f": if (s.tab !== 2) s.modal = "filter"; break;
      case "/": s.searching = true; s.search = ""; break;
      case "\x1b": s.search = null; break;
      case "\r": case "\n": if (s.tab === 2) s.wikiLoaded = true; break;
      case "q": s.quit = true; break;
    }
    if (data !== "g") s.pendingG = false;
    render();
  }

  return {
    render,
    handleInput,
    reset() { s = initial(); render(); },
  };
}
