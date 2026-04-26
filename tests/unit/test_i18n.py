import re

from redi import i18n
from redi.i18n.en import En
from redi.i18n.ja import Ja


class TestKeysParity:
    """ja と en は同じ key 集合を持つ"""

    def test_attribute_sets_match(self):
        """ja と en で公開 attribute(_ で始まらないもの) が完全一致する"""
        ja_keys = {a for a in dir(Ja) if not a.startswith("_")}
        en_keys = {a for a in dir(En) if not a.startswith("_")}
        assert ja_keys == en_keys


class TestPlaceholdersParity:
    """ja と en は同じ format placeholder 集合を持つ"""

    def test_placeholders_match_per_key(self):
        """各 key について ja と en の {placeholder} 集合が一致する"""
        pat = re.compile(r"{(\w+)}")
        mismatched = []
        for k in vars(Ja):
            if k.startswith("_"):
                continue
            ja_holders = sorted(pat.findall(getattr(Ja, k)))
            en_holders = sorted(pat.findall(getattr(En, k)))
            if ja_holders != en_holders:
                mismatched.append((k, ja_holders, en_holders))
        assert not mismatched, mismatched


class TestSelect:
    """_select() は config.language に応じて Ja / En を返す"""

    def test_returns_ja_for_ja(self):
        """language='ja' のとき Ja を返す"""
        assert isinstance(i18n._select("ja"), Ja)

    def test_returns_en_for_en(self):
        """language='en' のとき En を返す"""
        assert isinstance(i18n._select("en"), En)

    def test_falls_back_to_en_for_unknown(self):
        """未知の言語コードは default(en) にフォールバックする"""
        assert isinstance(i18n._select("zz"), En)


class TestFormat:
    """メッセージは str.format で引数を埋め込める"""

    def test_profile_created_ja(self):
        """ja: name を埋め込んだ日本語メッセージになる"""
        assert Ja.profile_created.format(name="dev") == "profile 'dev' を作成しました"

    def test_profile_created_en(self):
        """en: name を埋め込んだ英語メッセージになる"""
        assert En.profile_created.format(name="dev") == "Created profile 'dev'"
