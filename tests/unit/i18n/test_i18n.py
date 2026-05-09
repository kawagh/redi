import re
from pathlib import Path

from redi import i18n
from redi.i18n._protocol import MessagesProto
from redi.i18n.en import En
from redi.i18n.ja import Ja


REPO_ROOT = Path(__file__).resolve().parents[3]
SCAN_DIRS = (REPO_ROOT / "src", REPO_ROOT / "tests")


def _scan_sources() -> str:
    parts: list[str] = []
    for base in SCAN_DIRS:
        for p in base.rglob("*.py"):
            parts.append(p.read_text())
    return "\n".join(parts)


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


class TestSelectMessages:
    """select_messages() は config.language に応じて Ja / En を返す"""

    def test_returns_ja_for_ja(self):
        """language='ja' のとき Ja を返す"""
        assert isinstance(i18n.select_messages("ja"), Ja)

    def test_returns_en_for_en(self):
        """language='en' のとき En を返す"""
        assert isinstance(i18n.select_messages("en"), En)

    def test_falls_back_to_en_for_unknown(self):
        """未知の言語コードは default(en) にフォールバックする"""
        assert isinstance(i18n.select_messages("zz"), En)


class TestFormat:
    """メッセージは str.format で引数を埋め込める"""

    def test_profile_created_ja(self):
        """ja: name を埋め込んだ日本語メッセージになる"""
        assert Ja.profile_created.format(name="dev") == "profile 'dev' を作成しました"

    def test_profile_created_en(self):
        """en: name を埋め込んだ英語メッセージになる"""
        assert En.profile_created.format(name="dev") == "Created profile 'dev'"


class TestNoUnusedKeys:
    """_protocol.py に宣言した全 key が src/ または tests/ から参照されている"""

    def test_all_keys_referenced(self):
        """MessagesProto の公開 key が `messages.<key>` として参照されている"""
        searched = _scan_sources()
        unused = [
            k
            for k in MessagesProto.__annotations__
            if not k.startswith("_") and f"messages.{k}" not in searched
        ]
        assert not unused, unused


class TestNoUndefinedKeys:
    """src/ または tests/ で参照される `messages.<key>` は _protocol.py で定義されている"""

    def test_no_undefined_references(self):
        """`messages.<key>` の <key> が MessagesProto に存在する"""
        defined = set(MessagesProto.__annotations__)
        pat = re.compile(r"\bmessages\.([A-Za-z_][A-Za-z0-9_]*)")
        undefined: set[str] = set()
        for base in SCAN_DIRS:
            for p in base.rglob("*.py"):
                for m in pat.finditer(p.read_text()):
                    key = m.group(1)
                    if key not in defined:
                        undefined.add(key)
        assert not undefined, undefined
