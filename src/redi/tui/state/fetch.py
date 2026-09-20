from dataclasses import dataclass, field
from typing import Literal

# 取得結果を書き込む先。領域が違う取得は互いに待たせない。
FetchRegion = Literal["issues"]


@dataclass
class FetchTracker:
    """バックグラウンドで走る API 取得の進行状況を領域ごとに持つ。

    取得中も TUI の操作は続くので、結果が届いた時点で一覧が別の操作で
    書き換わっていることがある。領域ごとの世代番号で、その結果がまだ有効かを
    判定する。
    """

    _generations: dict[FetchRegion, int] = field(default_factory=dict)
    _in_flight: set[FetchRegion] = field(default_factory=set)

    def begin(self, region: FetchRegion) -> int | None:
        """取得を始める。同じ領域が取得中なら None を返し、多重に発行させない。"""
        if region in self._in_flight:
            return None
        self._in_flight.add(region)
        return self._bump(region)

    def finish(self, region: FetchRegion, generation: int) -> bool:
        """取得を終える。結果を反映してよければ True。

        取得中に `invalidate` されていたら、その結果は古いので False を返す。
        """
        self._in_flight.discard(region)
        return self._generations.get(region) == generation

    def invalidate(self, region: FetchRegion) -> None:
        """領域を別の操作で書き換えたときに呼ぶ。進行中の取得結果を捨てさせる。"""
        self._bump(region)

    def is_fetching(self, region: FetchRegion) -> bool:
        return region in self._in_flight

    def _bump(self, region: FetchRegion) -> int:
        generation = self._generations.get(region, 0) + 1
        self._generations[region] = generation
        return generation
