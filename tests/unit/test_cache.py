import json
import time

from redi import cache, config
import pytest


class TestSave:
    """save()はキャッシュディレクトリにJSONファイルを保存する"""

    def test_creates_nested_directories(self, tmp_path, monkeypatch):
        """存在しないディレクトリでも自動作成して保存できる"""
        cache_dir = tmp_path / "nested" / "cache"
        monkeypatch.setattr(cache, "CACHE_DIR", cache_dir)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
        cache.save("statuses", [{"id": 1}])
        assert (cache_dir / "localhost_3000" / "statuses.json").exists()

    def test_overwrites_with_latest_data(self, tmp_path, monkeypatch):
        """同じキーで上書き保存すると最新のデータに更新される"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "https://localhost:3000")
        cache.save("statuses", [{"id": 1, "name": "旧データ"}])
        cache.save("statuses", [{"id": 1, "name": "新データ"}])
        assert cache.load("statuses") == [{"id": 1, "name": "新データ"}]


class TestLoad:
    """load()はキャッシュファイルからデータを読み込む"""

    def test_returns_saved_data(self, tmp_path, monkeypatch):
        """保存したデータがそのまま返る"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
        data = [{"id": 1, "name": "新規"}]
        cache.save("statuses", data)

        assert cache.load("statuses") == data

    def test_returns_none_for_missing_key(self, tmp_path, monkeypatch):
        """存在しないキーを指定するとNoneが返る"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")

        assert cache.load("nonexistent") is None

    def test_returns_none_when_expired(self, tmp_path, monkeypatch):
        """保存時刻からTTLを過ぎるとNoneが返る"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
        data = [{"id": 1, "name": "新規"}]
        monkeypatch.setattr(time, "time", lambda: 1000.0)
        cache.save("statuses", data)
        monkeypatch.setattr(time, "time", lambda: 1100.0)  # 保存してから100秒経過

        assert cache.load("statuses", ttl=50) is None

    def test_returns_data_within_ttl(self, tmp_path, monkeypatch):
        """TTL以内であればデータが返る"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
        data = [{"id": 1, "name": "新規"}]
        monkeypatch.setattr(time, "time", lambda: 1000.0)
        cache.save("statuses", data)
        monkeypatch.setattr(time, "time", lambda: 1030.0)  # 保存してから30秒経過
        assert cache.load("statuses", ttl=50) == data

    def test_returns_none_for_invalid_json(self, tmp_path, monkeypatch):
        """不正なJSONの場合Noneが返る"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
        path = tmp_path / "localhost_3000" / "statuses.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("invalid json")
        assert cache.load("statuses") is None

    def test_returns_none_for_missing_value_key(self, tmp_path, monkeypatch):
        """valueキーが欠落したJSONの場合Noneが返る"""
        monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
        path = tmp_path / "localhost_3000" / "statuses.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"timestamp": time.time()}))
        assert cache.load("statuses") is None


class TestSlugifyUrl:
    """_slugify_url() は URL をディレクトリ名に変換する"""

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("http://redmine.example.com", "redmine.example.com"),
            ("https://redmine.example.com", "redmine.example.com"),
            ("https://redmine.example.com/", "redmine.example.com"),
            ("https://redmine.example.com/main", "redmine.example.com_main"),
            ("https://redmine.example.com/main/", "redmine.example.com_main"),
            ("http://localhost:3000", "localhost_3000"),
            ("http://localhost:3001", "localhost_3001"),
        ],
    )
    def test_slugify(self, url, expected):
        assert cache._slugify_url(url) == expected
