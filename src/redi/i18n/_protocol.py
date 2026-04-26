from typing import Protocol


class MessagesProto(Protocol):
    """全言語が満たすべきメッセージ集合の輪郭。

    新しいメッセージを追加するときはまずここに key を宣言し、
    ja.py / en.py に実装を追加する。実装側に欠けがあれば ty が検出する。
    """

    # ---- profile / config ----
    profile_created: str
    """プロファイル作成成功。{name} を埋め込む。"""
    profile_already_exists: str
    """profile が既に存在する。{name} を埋め込む。"""
    default_profile_set: str
    """default_profile を設定。{name}"""
    default_project_id_set: str
    """default_project_id を設定。{value}, {suffix}"""
    editor_set: str
    """editor を設定。{value}, {suffix}"""
    redmine_api_key_set: str
    """redmine_api_key を設定。{suffix}"""
    redmine_url_set: str
    """redmine_url を設定。{value}, {suffix}"""
    wiki_project_id_set: str
    """wiki_project_id を設定。{value}, {suffix}"""

    # ---- common cancellation / mismatch ----
    canceled: str
    """汎用キャンセル"""
    update_canceled: str
    """更新をキャンセル"""
    update_canceled_no_changes: str
    """更新内容がないので更新をキャンセル"""
    canceled_empty_text: str
    """テキストが空のためキャンセル"""
    canceled_empty_subject: str
    """題名が空のためキャンセル"""
    canceled_empty_comment: str
    """コメントが空のためキャンセル"""
    canceled_empty_title: str
    """ページタイトルが空のためキャンセル"""
    canceled_no_items_selected: str
    """更新する項目が選択されていないためキャンセル"""
    canceled_no_project: str
    """プロジェクトが特定できないためキャンセル"""
    canceled_field_mismatch: str
    """{field} が一致しないのでキャンセル"""

    # ---- common indicators ----
    project_id_required: str
    """project_id を指定するか default_project_id を設定"""
    wiki_project_id_required: str
    """project_id を指定するか wiki_project_id/default_project_id を設定"""
    user_or_group_id_required: str
    """user_id または group_id を指定"""
    user_or_group_flag_required: str
    """--user_id または --group_id を指定"""
    issue_or_project_id_required: str
    """issue_id または project_id を指定"""
    delete_relation_requires_to: str
    """--delete-relation には --to が必要"""
    relate_and_to_required: str
    """--relate と --to は両方指定する"""

    # ---- not found ----
    role_not_found: str
    """ロールが見つからない。{id}"""
    membership_not_found: str
    """メンバーシップが見つからない。{id}"""
    relation_not_found: str
    """関係性が見つからない。{id}"""
    relation_between_not_found: str
    """{from_id} と {to_id} の間に関係性が見つからない"""
    issue_not_found: str
    """イシューが見つからない。{id}"""
    issue_or_user_not_found: str
    """イシューまたはユーザーが見つからない。{issue_id} / {user_id}"""
    user_not_found: str
    """ユーザーが見つからない。{id}"""
    project_not_found: str
    """プロジェクトが見つからない。{id}"""
    wiki_page_not_found: str
    """Wikiページが見つからない。{title}"""
    wiki_page_with_version_not_found: str
    """バージョン指定の Wikiページが見つからない。{title}, {version}"""
    wiki_page_does_not_exist: str
    """Wikiページが存在しない"""
    parent_page_not_found: str
    """親ページが見つからない。{title}"""
    file_not_found: str
    """ファイルが見つからない。{path}"""
    attachment_not_found: str
    """添付ファイルが見つからない。{id}"""
    time_entry_not_found: str
    """作業時間が見つからない。{id}"""
    version_not_found: str
    """バージョンが見つからない。{id}"""
    group_not_found: str
    """グループが見つからない。{id}"""
    group_or_user_not_found: str
    """グループまたはユーザーが見つからない。{group_id} / {user_id}"""
    category_not_found: str
    """カテゴリが見つからない。{id}"""
    no_search_results: str
    """検索結果が見つからない"""
    issue_not_found_simple: str
    """TUI 等で短く「イシューが見つかりません」"""
    no_versions_available: str
    """選択可能なバージョンがない"""
    no_issues_available: str
    """選択可能なイシューがない"""
    no_project_skip_project_id: str
    """プロジェクトが存在しないため設定スキップ"""

    # ---- admin / permission required ----
    user_create_admin_required: str
    user_list_admin_required: str
    user_detail_permission_required: str
    user_update_admin_required: str
    user_delete_admin_required: str
    custom_field_admin_required: str
    group_get_admin_required: str
    group_create_admin_required: str
    group_update_admin_required: str
    group_delete_admin_required: str
    group_add_user_admin_required: str
    group_remove_user_admin_required: str

    # ---- create / update / delete success ----
    user_updated: str
    """{id}"""
    user_created: str
    """{id}, {login}, {url}"""
    user_deleted: str
    """{id}"""
    user_list_member_hint: str
    """ユーザー一覧が取れない場合のヒント"""
    project_updated: str
    project_archived: str
    project_unarchived: str
    project_deleted: str
    issue_created: str
    """{url}"""
    issue_updated: str
    """{url}"""
    issue_deleted: str
    """{id}"""
    comment_added: str
    """{url}"""
    watcher_added: str
    """{issue_id}, {user_id}"""
    watcher_removed: str
    """{issue_id}, {user_id}"""
    wiki_page_updated: str
    """{url}"""
    wiki_page_created: str
    """{url}"""
    wiki_page_deleted: str
    """{title}"""
    membership_created: str
    """{line}"""
    membership_updated: str
    """{id}"""
    membership_deleted: str
    """{id}"""
    relation_created: str
    """{from_id}, {type}, {to_id}"""
    relation_deleted: str
    """{from_id}, {type}, {to_id}"""
    file_uploaded: str
    """{filename}"""
    account_updated: str
    version_created: str
    """{id}, {name}, {url}"""
    version_updated: str
    """{id}, {url}"""
    version_deleted: str
    """{id}"""
    time_entry_updated: str
    """{id}"""
    time_entry_deleted: str
    """{id}"""
    attachment_deleted: str
    """{id}"""
    attachment_updated: str
    """{url}"""
    group_updated: str
    """{id}"""
    group_deleted: str
    """{id}"""
    group_user_added: str
    """{group_id}, {user_id}"""
    group_user_removed: str
    """{group_id}, {user_id}"""
    group_created: str
    """{id}, {name}, {url}"""
    time_entry_created: str
    """{id}, {hours}, {spent_on}"""
    category_created: str
    """{id}, {name}"""
    category_updated: str
    """{id}"""
    category_deleted: str
    """{id}"""

    # ---- failures ----
    user_create_failed: str
    user_update_failed: str
    user_delete_failed: str
    project_update_failed: str
    project_archive_failed: str
    project_unarchive_failed: str
    project_delete_failed: str
    issue_create_failed: str
    issue_update_failed: str
    issue_delete_failed: str
    watcher_add_failed: str
    watcher_remove_failed: str
    wiki_page_delete_failed: str
    membership_create_failed: str
    membership_update_failed: str
    membership_delete_failed: str
    relation_create_failed: str
    relation_delete_failed: str
    file_upload_failed: str
    """汎用版 (詳細なし)"""
    file_upload_failed_with_path: str
    """{path}"""
    account_update_failed: str
    version_create_failed: str
    version_update_failed: str
    version_delete_failed: str
    time_entry_create_failed: str
    time_entry_update_failed: str
    time_entry_delete_failed: str
    attachment_delete_failed: str
    attachment_update_failed: str
    group_create_failed: str
    group_update_failed: str
    group_delete_failed: str
    group_add_user_failed: str
    group_remove_user_failed: str
    category_create_failed: str
    category_update_failed: str
    category_delete_failed: str
    project_list_fetch_failed: str
    """{error}"""
    connection_failed_http: str
    """{status}, {reason}"""
    connection_failed_other: str
    """{error}"""

    # ---- selection / preview labels ----
    parent_page_label: str
    """{label}"""
    edit_target_page: str
    """{label}"""
    update_target_version: str
    """{label}"""
    update_target_issue: str
    """{label}"""
    update_items: str
    """{items}"""
    status_label: str
    """{value}"""
    sharing_label: str
    """{value}"""
    issue_label: str
    """{id}, {subject}"""
    activity_label: str
    """{value}"""
    tracker_label: str
    """{value}"""
    priority_label: str
    """{value}"""
    assignee_label: str
    """{value}"""
    fixed_version_label: str
    """{value}"""
    done_ratio_label: str
    """{value}"""
    estimated_hours_label: str
    """{value}"""

    # ---- init flow ----
    api_key_url_hint: str
    """{url}"""
    checking_connection: str
    connection_success: str
    """{login}, {name}"""
    default_project_label: str
    """{name}"""
    wiki_project_label: str
    """{name}"""
    config_created: str
    """{path}"""
    init_profile_already_exists: str
    """既存プロファイルあり。{path}"""
