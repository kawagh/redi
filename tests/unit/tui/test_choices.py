from redi.tui import choices as choices_module


class TestBuildUserChoices:
    """build_user_choices() は time_entry フィルタモーダルのユーザー選択肢を組み立てる"""

    def test_returns_specials_only_when_project_id_is_none(self):
        """project_id が None のとき (指定なし) + (自分) のみ返す"""
        choices = choices_module.build_user_choices(None)
        assert [v for v, _ in choices] == [None, "me"]

    def test_includes_project_users_when_me_id_is_none(self, monkeypatch):
        """me_id 未指定なら project users はそのまま全件並ぶ"""
        monkeypatch.setattr(
            choices_module,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = choices_module.build_user_choices("1")
        assert [v for v, _ in choices] == [None, "me", "5", "9"]

    def test_excludes_self_when_me_id_matches_project_user(self, monkeypatch):
        """me_id と一致する project user は除外して『自分』との重複を防ぐ"""
        monkeypatch.setattr(
            choices_module,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = choices_module.build_user_choices("1", me_id="5")
        assert [v for v, _ in choices] == [None, "me", "9"]

    def test_keeps_all_users_when_me_id_not_in_project_users(self, monkeypatch):
        """me_id が project users に居なければ何も除外しない"""
        monkeypatch.setattr(
            choices_module,
            "fetch_project_users",
            lambda _project_id: [{"id": 5, "name": "Sandbox Developer"}],
        )
        choices = choices_module.build_user_choices("1", me_id="999")
        assert [v for v, _ in choices] == [None, "me", "5"]


class TestBuildAssigneeChoices:
    """build_assignee_choices() は issue フィルタモーダルの担当者選択肢を組み立てる"""

    def test_returns_specials_only_when_project_id_is_none(self):
        """project_id が None のとき (指定なし) + (自分) + (未割当) のみ返す"""
        choices = choices_module.build_assignee_choices(None)
        assert [v for v, _ in choices] == [None, "me", "!*"]

    def test_includes_project_users_when_me_id_is_none(self, monkeypatch):
        """me_id 未指定なら project users はそのまま全件並ぶ"""
        monkeypatch.setattr(
            choices_module,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = choices_module.build_assignee_choices("1")
        assert [v for v, _ in choices] == [None, "me", "!*", "5", "9"]

    def test_excludes_self_when_me_id_matches_project_user(self, monkeypatch):
        """me_id と一致する project user は除外して『自分』との重複を防ぐ"""
        monkeypatch.setattr(
            choices_module,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = choices_module.build_assignee_choices("1", me_id="5")
        assert [v for v, _ in choices] == [None, "me", "!*", "9"]

    def test_keeps_all_users_when_me_id_not_in_project_users(self, monkeypatch):
        """me_id が project users に居なければ何も除外しない"""
        monkeypatch.setattr(
            choices_module,
            "fetch_project_users",
            lambda _project_id: [{"id": 5, "name": "Sandbox Developer"}],
        )
        choices = choices_module.build_assignee_choices("1", me_id="999")
        assert [v for v, _ in choices] == [None, "me", "!*", "5"]


class TestBuildTrackerChoices:
    """build_tracker_choices() は issue フィルタモーダルのトラッカー選択肢を組み立てる"""

    def test_first_choice_is_unspecified(self, monkeypatch):
        """先頭は絞り込み無しを表す特殊指定 (None) で、以降に tracker が並ぶ"""
        monkeypatch.setattr(
            choices_module,
            "fetch_trackers",
            lambda: [{"id": 1, "name": "Bug"}, {"id": 2, "name": "Feature"}],
        )
        choices = choices_module.build_tracker_choices()
        assert [v for v, _ in choices] == [None, "1", "2"]
        assert [label for _, label in choices][1:] == ["Bug", "Feature"]

    def test_returns_special_only_when_no_tracker(self, monkeypatch):
        """tracker が1つも無ければ特殊指定のみ返す"""
        monkeypatch.setattr(choices_module, "fetch_trackers", list)
        assert choices_module.build_tracker_choices() == [
            (None, choices_module.messages.tui_filter_assignee_none)
        ]
