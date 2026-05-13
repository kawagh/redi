from redi.tui import app


class TestBuildUserChoices:
    """_build_user_choices() は time_entry フィルタモーダルのユーザー選択肢を組み立てる"""

    def test_returns_specials_only_when_project_id_is_none(self):
        """project_id が None のとき (指定なし) + (自分) のみ返す"""
        choices = app._build_user_choices(None)
        assert [v for v, _ in choices] == [None, "me"]

    def test_includes_project_users_when_me_id_is_none(self, monkeypatch):
        """me_id 未指定なら project users はそのまま全件並ぶ"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = app._build_user_choices("1")
        assert [v for v, _ in choices] == [None, "me", "5", "9"]

    def test_excludes_self_when_me_id_matches_project_user(self, monkeypatch):
        """me_id と一致する project user は除外して『自分』との重複を防ぐ"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = app._build_user_choices("1", me_id="5")
        assert [v for v, _ in choices] == [None, "me", "9"]

    def test_keeps_all_users_when_me_id_not_in_project_users(self, monkeypatch):
        """me_id が project users に居なければ何も除外しない"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [{"id": 5, "name": "Sandbox Developer"}],
        )
        choices = app._build_user_choices("1", me_id="999")
        assert [v for v, _ in choices] == [None, "me", "5"]
