from dataclasses import dataclass


@dataclass
class FetchTracker:
    """バックグラウンドで走る API 取得のうち、どれが最新かを持つ。

    取得中も TUI の操作は続くので、結果が届いた時点で後の操作に追い越されて
    いることがある。世代番号は TUI 全体で 1 つで、結果を反映できるのは最後に
    始めた取得だけ (最後の操作が勝つ)。
    """

    _generation: int = 0
    _fetching: bool = False

    def begin(self) -> int:
        """取得を始める。進行中の取得があれば、その結果は捨てさせる。"""
        self._generation += 1
        self._fetching = True
        return self._generation

    def finish(self, generation: int) -> bool:
        """取得を終える。結果を反映してよければ True。

        後の操作に追い越されていたら、その結果は古いので False を返す。
        """
        if generation != self._generation:
            return False
        self._fetching = False
        return True

    def invalidate(self) -> None:
        """取得を介さずに一覧を書き換えたときに呼ぶ。進行中の取得結果を捨てさせる。"""
        self._generation += 1
        self._fetching = False

    def is_fetching(self) -> bool:
        """最新の取得がまだ終わっていなければ True。"""
        return self._fetching
