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
    language_set: str
    """language を設定。{value}, {suffix}"""
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

    # ---- prompts (interactive input messages) ----
    prompt_confirm_delete: str
    prompt_confirm_delete_with_identifier: str
    """{label}, {expected}"""
    prompt_subject: str
    prompt_comment: str
    prompt_page_title: str
    prompt_parent_page: str
    prompt_edit_page: str
    prompt_select_tracker: str
    prompt_select_status: str
    prompt_select_priority: str
    prompt_select_assignee: str
    prompt_select_assignee_none: str
    prompt_select_fixed_version: str
    prompt_select_activity: str
    prompt_select_done_ratio: str
    prompt_select_sharing: str
    prompt_select_version_to_update: str
    prompt_select_issue_to_update: str
    prompt_start_date: str
    prompt_due_date: str
    prompt_estimated_hours: str
    prompt_hours: str
    prompt_spent_on: str
    prompt_update_spent_on: str
    prompt_issue_id_update: str
    prompt_time_comments: str
    prompt_select_update_items: str
    prompt_version_name: str
    prompt_description_optional: str
    prompt_due_date_optional: str
    prompt_issue_id_or_project: str
    prompt_project_id_or_name: str
    prompt_redmine_url: str
    prompt_redmine_api_key: str
    prompt_select_default_project: str
    prompt_select_wiki_project: str
    prompt_required_field: str
    """{name}"""
    prompt_field_value: str
    """{name}, {value}"""
    prompt_custom_field_label: str
    """{name}"""

    # ---- prompt validators ----
    error_input_required: str
    error_url_format: str
    error_date_format: str
    error_date_after_start: str
    """{date}"""
    error_numeric_required: str
    error_page_title_required: str
    error_page_title_duplicate: str
    error_no_matching_project: str

    # ---- field labels (interactive selection items) ----
    field_tracker: str
    field_subject: str
    field_description: str
    field_status: str
    field_priority: str
    field_assignee: str
    field_fixed_version: str
    field_start_date: str
    field_due_date: str
    field_done_ratio: str
    field_estimated_hours: str
    field_notes: str
    field_time_entry: str
    field_version_name: str
    field_sharing: str
    field_hours: str
    field_activity: str
    field_spent_on: str
    field_comments: str
    field_issue_id: str

    # ---- sharing options ----
    sharing_none: str
    sharing_descendants: str
    sharing_hierarchy: str
    sharing_tree: str
    sharing_system: str

    # ---- delete confirmations ----
    delete_target_issue: str
    """{id}, {subject}"""
    delete_target_version: str
    """{id}, {name}"""
    delete_target_user: str
    """{summary}"""
    delete_target_project: str
    """{id}, {name}, {identifier}"""
    delete_project_warning: str
    delete_target_wiki_page: str
    """{title}"""
    delete_target_membership: str
    """{id}, {kind}, {principal_id}, {principal_name}, {roles}"""
    delete_target_attachment: str
    """{id}, {filename}"""
    delete_target_category: str
    """{id}, {name}"""
    delete_target_group: str
    """{id}, {name}"""
    delete_target_time_entry: str
    """{id}, {hours}, {activity}, {spent_on}"""
    delete_confirm_tui: str
    """{summary}"""

    # ---- detail/output labels ----
    label_assignable: str
    """{value}"""
    label_issues_visibility: str
    """{value}"""
    label_time_entries_visibility: str
    """{value}"""
    label_users_visibility: str
    """{value}"""
    label_permissions_header: str
    label_name: str
    """{value}"""
    label_mail: str
    """{value}"""
    label_admin: str
    """{value}"""
    label_admin_yes: str
    label_created_on: str
    """{value}"""
    label_last_login_on: str
    """{value}"""
    label_custom_fields_header: str
    label_membership_header: str
    label_groups_header: str
    label_users_header: str
    label_project_field: str
    """{id}, {name}"""
    label_default_assignee: str
    """{id}, {name}"""
    label_size: str
    """{value}"""
    label_kind: str
    """{value}"""
    label_author: str
    """{value}"""
    label_description_field: str
    """{value}"""
    label_url_field: str
    """{value}"""
    label_roles_header: str
    label_inherited_suffix: str
    label_relations_header: str
    label_attachments_header: str
    label_children_header: str
    label_watchers_header: str
    label_allowed_statuses_header: str
    label_revisions_header: str
    label_journals_header: str
    label_comments_header: str
    label_due_date_field: str
    """{value}"""
    label_sharing_field: str
    """{value}"""
    label_parent_project: str
    """{id}, {name}"""
    label_trackers_header: str
    label_issue_categories_header: str
    label_enabled_modules_header: str
    label_user_field: str
    """{name}, {id}"""
    label_issue_field: str
    """{id}"""
    label_comments_field: str
    """{value}"""
    label_user_in_te: str
    """{name}, {id}"""
    label_project_in_te: str
    """{name}, {id}"""

    # ---- relation labels ----
    relation_label_relates: str
    relation_label_duplicates: str
    relation_label_duplicated: str
    relation_label_blocks: str
    relation_label_blocked: str
    relation_label_precedes: str
    relation_label_follows: str
    relation_label_copied_to: str
    relation_label_copied_from: str

    # ---- TUI ----
    tui_tab_label_issues: str
    tui_tab_label_wiki: str
    tui_tab_label_time_entries: str
    tui_tab_switch_hint: str
    tui_filter_status: str
    tui_filter_assignee: str
    tui_filter_hint: str
    tui_filter_title: str
    tui_help_title: str
    """{label}"""
    tui_status_hint_issues: str
    """{page_label}"""
    tui_status_hint_wiki: str
    tui_status_hint_time_entries: str
    tui_filter_status_open_default: str
    tui_filter_status_all: str
    tui_filter_status_closed_only: str
    tui_filter_assignee_none: str
    tui_filter_assignee_me: str
    tui_filter_assignee_unassigned: str
    tui_meta_status: str
    tui_meta_priority: str
    tui_meta_tracker: str
    tui_meta_assignee: str
    tui_meta_author: str
    tui_meta_start_date: str
    tui_meta_due_date: str
    tui_meta_progress: str
    tui_meta_estimated_hours: str
    tui_meta_spent_hours: str
    tui_meta_created: str
    tui_meta_updated: str
    tui_meta_parent: str
    tui_meta_version: str
    tui_meta_project: str
    tui_meta_user: str
    tui_meta_activity: str
    tui_meta_issue: str
    tui_preview_comments_header: str
    tui_wiki_no_pages: str
    tui_wiki_loading: str
    tui_wiki_load_failed: str
    """{error}"""
    tui_wiki_load_text_failed: str
    """{error}"""
    tui_wiki_page_missing: str
    tui_wiki_press_enter_to_load: str
    tui_wiki_project_required: str
    tui_time_entry_no_entries: str
    tui_time_entry_loading: str
    tui_time_entry_load_failed: str
    """{error}"""
    tui_time_entry_delete_failed: str
    """{error}"""
    tui_time_entry_delete_prompt: str
    """{summary}"""

    # ---- argparse helps (root) ----
    arg_help_root_description: str
    arg_help_tui: str
    arg_help_debug: str
    arg_help_debug_tui: str
    arg_help_profile: str

    # ---- argparse helps (common) ----
    arg_help_full_json: str
    arg_help_skip_confirm: str
    arg_help_open_web: str
    arg_help_project_id: str
    arg_help_project_id_filter: str
    arg_help_user_id: str
    arg_help_full_profiles: str

    # ---- argparse helps (subcommand summary) ----
    arg_help_crud_subcommands: str
    arg_help_role_subcommands: str
    arg_help_file_subcommands: str

    # ---- argparse helps (project) ----
    arg_help_project_command: str
    arg_help_project_list: str
    arg_help_project_view: str
    arg_help_project_view_id: str
    arg_help_project_include: str
    arg_help_project_create: str
    arg_help_project_name: str
    arg_help_project_identifier: str
    label_project_identifier: str
    arg_help_description: str
    arg_help_project_is_public: str
    arg_help_parent_id: str
    arg_help_tracker_ids: str
    arg_help_project_delete: str
    arg_help_project_delete_id: str
    arg_help_project_update: str
    arg_help_project_update_id: str
    arg_help_project_archive: str

    # ---- argparse helps (issue) ----
    arg_help_issue_command: str
    arg_help_issue_filter_project: str
    arg_help_issue_filter_version: str
    arg_help_issue_filter_assigned_to: str
    arg_help_issue_filter_status: str
    arg_help_issue_filter_tracker: str
    arg_help_issue_filter_priority: str
    arg_help_issue_filter_query: str
    arg_help_limit: str
    arg_help_offset: str
    arg_help_issue_list: str
    arg_help_issue_view: str
    arg_help_issue_view_id: str
    arg_help_issue_include: str
    arg_help_issue_create: str
    arg_help_issue_subject_arg: str
    arg_help_issue_tracker_id: str
    arg_help_issue_priority_id: str
    arg_help_issue_assigned_to_id: str
    arg_help_issue_description: str
    arg_help_custom_fields: str
    arg_help_issue_update: str
    arg_help_issue_update_id: str
    arg_help_issue_subject_opt: str
    arg_help_issue_update_description: str
    arg_help_issue_update_tracker_id: str
    arg_help_issue_status_id: str
    arg_help_issue_fixed_version_id: str
    arg_help_issue_parent: str
    arg_help_issue_start_date: str
    arg_help_issue_due_date: str
    arg_help_issue_done_ratio: str
    arg_help_issue_estimated_hours: str
    arg_help_issue_notes: str
    arg_help_issue_relate: str
    arg_help_issue_relate_to: str
    arg_help_issue_delete_relation: str
    arg_help_issue_attach: str
    arg_help_issue_hours: str
    arg_help_issue_activity_id: str
    arg_help_issue_spent_on: str
    arg_help_issue_time_comments: str
    arg_help_issue_add_watcher: str
    arg_help_issue_remove_watcher: str
    arg_help_issue_comment: str
    arg_help_issue_comment_notes: str
    arg_help_issue_delete: str

    # ---- argparse helps (version) ----
    arg_help_version_command: str
    arg_help_version_list: str
    arg_help_version_view: str
    arg_help_version_view_id: str
    arg_help_version_create: str
    arg_help_version_name_arg: str
    arg_help_version_status: str
    arg_help_version_due_date: str
    arg_help_version_description: str
    arg_help_version_sharing: str
    arg_help_version_delete: str
    arg_help_version_delete_id: str
    arg_help_version_update: str
    arg_help_version_update_id: str
    arg_help_version_name_opt: str

    # ---- argparse helps (wiki) ----
    arg_help_wiki_command: str
    arg_help_wiki_list: str
    arg_help_wiki_view: str
    arg_help_wiki_page_title: str
    arg_help_wiki_version: str
    arg_help_wiki_create: str
    arg_help_wiki_create_title: str
    arg_help_wiki_parent_title: str
    arg_help_wiki_description: str
    arg_help_wiki_delete: str
    arg_help_wiki_update: str
    arg_help_wiki_update_title: str

    # ---- argparse helps (config) ----
    arg_help_config_command: str
    arg_help_config_update: str
    arg_help_config_profile_name_optional: str
    arg_help_config_set_default_project_id: str
    arg_help_config_set_wiki_project_id: str
    arg_help_config_set_editor: str
    arg_help_config_set_language: str
    arg_help_config_set_api_key: str
    arg_help_config_set_url: str
    arg_help_config_set_default_profile: str
    arg_help_config_create: str
    arg_help_config_create_profile_name: str
    arg_help_config_url: str
    arg_help_config_api_key: str
    arg_help_config_default_project_id: str
    arg_help_config_wiki_project_id: str
    arg_help_config_editor: str
    arg_help_config_language: str
    arg_help_config_set_default_flag: str

    # ---- argparse helps (init) ----
    arg_help_init_command: str

    # ---- argparse helps (user) ----
    arg_help_user_command: str
    arg_help_user_list: str
    arg_help_user_create: str
    arg_help_user_login: str
    arg_help_user_firstname: str
    arg_help_user_lastname: str
    arg_help_user_mail: str
    arg_help_user_password: str
    arg_help_user_generate_password: str
    arg_help_user_auth_source_id: str
    arg_help_user_mail_notification: str
    arg_help_user_must_change_passwd: str
    arg_help_user_admin: str
    arg_help_user_view: str
    arg_help_user_view_id: str
    arg_help_user_update: str
    arg_help_user_update_id: str
    arg_help_user_must_change_passwd_update: str
    arg_help_user_admin_update: str
    arg_help_user_delete: str
    arg_help_user_delete_id: str

    # ---- argparse helps (me) ----
    arg_help_me_command: str
    arg_help_me_update: str

    # ---- argparse helps (membership) ----
    arg_help_membership_command: str
    arg_help_membership_list: str
    arg_help_membership_view: str
    arg_help_membership_view_id: str
    arg_help_membership_create: str
    arg_help_membership_user_id: str
    arg_help_membership_group_id: str
    arg_help_membership_role_ids: str
    arg_help_membership_update: str
    arg_help_membership_update_id: str
    arg_help_membership_delete: str
    arg_help_membership_delete_id: str

    # ---- argparse helps (group) ----
    arg_help_group_command: str
    arg_help_group_list: str
    arg_help_group_view: str
    arg_help_group_view_id: str
    arg_help_group_create: str
    arg_help_group_name: str
    arg_help_group_user_id: str
    arg_help_group_update: str
    arg_help_group_update_id: str
    arg_help_group_name_opt: str
    arg_help_group_user_id_replace: str
    arg_help_group_add_user: str
    arg_help_group_remove_user: str
    arg_help_group_delete: str
    arg_help_group_delete_id: str

    # ---- argparse helps (issue category) ----
    arg_help_issue_category_command: str
    arg_help_issue_category_list: str
    arg_help_issue_category_view: str
    arg_help_issue_category_view_id: str
    arg_help_issue_category_create: str
    arg_help_issue_category_name: str
    arg_help_issue_category_assigned_to_id: str
    arg_help_issue_category_update: str
    arg_help_issue_category_update_id: str
    arg_help_issue_category_name_opt: str
    arg_help_issue_category_delete: str
    arg_help_issue_category_delete_id: str
    arg_help_issue_category_reassign_to_id: str

    # ---- argparse helps (relation) ----
    arg_help_relation_command: str
    arg_help_relation_view: str
    arg_help_relation_view_id: str

    # ---- argparse helps (attachment) ----
    arg_help_attachment_command: str
    arg_help_attachment_view: str
    arg_help_attachment_view_id: str
    arg_help_attachment_update: str
    arg_help_attachment_update_id: str
    arg_help_attachment_filename: str
    arg_help_attachment_description: str
    arg_help_attachment_delete: str
    arg_help_attachment_delete_id: str

    # ---- argparse helps (time entry) ----
    arg_help_time_entry_command: str
    arg_help_time_entry_user_id: str
    arg_help_time_entry_list: str
    arg_help_time_entry_create: str
    arg_help_time_entry_hours: str
    arg_help_time_entry_issue_id: str
    arg_help_time_entry_activity_id: str
    arg_help_time_entry_spent_on: str
    arg_help_time_entry_comments: str
    arg_help_time_entry_view: str
    arg_help_time_entry_view_id: str
    arg_help_time_entry_update: str
    arg_help_time_entry_update_id: str
    arg_help_time_entry_update_hours: str
    arg_help_time_entry_update_spent_on: str
    arg_help_time_entry_delete: str
    arg_help_time_entry_delete_id: str

    # ---- argparse helps (file) ----
    arg_help_file_command: str
    arg_help_file_list: str
    arg_help_file_create: str
    arg_help_file_path: str
    arg_help_file_version_id: str
    arg_help_file_description: str

    # ---- argparse helps (role) ----
    arg_help_role_command: str
    arg_help_role_list: str
    arg_help_role_view: str
    arg_help_role_view_id: str

    # ---- argparse helps (search) ----
    arg_help_search_command: str
    arg_help_search_query: str

    # ---- argparse helps (news) ----
    arg_help_news_command: str

    # ---- argparse helps (enumerations) ----
    arg_help_tracker_command: str
    arg_help_issue_status_command: str
    arg_help_issue_priority_command: str
    arg_help_time_entry_activity_command: str
    arg_help_document_category_command: str
    arg_help_query_command: str
    arg_help_custom_field_command: str

    # ---- config_command suffix ----
    config_profile_suffix: str
    """{name}"""

    # ---- TUI help labels (sections / common) ----
    tui_help_section_navigation: str
    tui_help_section_search: str
    tui_help_section_filter: str
    tui_help_section_actions: str
    tui_help_section_other: str
    tui_help_move_up: str
    tui_help_move_down: str
    tui_help_goto_top_bottom: str
    tui_help_jump_to_issue_n: str
    tui_help_prev_next_page: str
    tui_help_switch_tab: str
    tui_help_preview_scroll_line: str
    tui_help_preview_scroll_half_page: str
    tui_help_start_search: str
    tui_help_next_prev_match: str
    tui_help_filter_status_assignee: str
    tui_help_show_or_close: str
    tui_help_quit: str

    # ---- TUI help labels (issue tab) ----
    tui_help_issue_load_comments: str
    tui_help_issue_create_or_update: str
    tui_help_issue_add_comment: str
    tui_help_issue_create_time_entry: str
    tui_help_issue_open_web_or_n: str

    # ---- TUI help labels (wiki tab) ----
    tui_help_wiki_load_text: str
    tui_help_wiki_create_child: str
    tui_help_wiki_update_page: str
    tui_help_wiki_open_web: str

    # ---- TUI help labels (time entry tab) ----
    tui_help_time_entry_create: str
    tui_help_time_entry_update: str
    tui_help_time_entry_delete: str
    tui_help_time_entry_open_web: str
