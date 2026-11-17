"""How often does merging remove duplicate boards, and would the beam fill with copies without it?"""
import sys
from multiprocessing import Pool
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.misakamm import MisakammAi

def play(job):
    preview, seed = job
    stats = {"children": 0, "distinct": 0, "levels": 0, "top8_distinct": 0, "same_kind": 0, "same_kind_dups": 0, "diff_kind_dups": 0}
    ai = MisakammAi(preview=preview, beam_width=8, score_mode="final")
    orig = ai._select
    def select(paths, last):
        level[0] += 1
        if level[0] == 1:
            return orig(paths, last)
        keys = [tuple(p.bits) for p in paths]
        stats["children"] += len(paths); stats["distinct"] += len(set(keys)); stats["levels"] += 1
        ranked = sorted(paths, key=lambda p: (-p.score, p.tie))[:8]   # what an unmerged beam would keep
        stats["top8_distinct"] += len({tuple(p.bits) for p in ranked})
        stats["same_kind"] += len(ranked) < 8
        stats["same_kind_dups"] += len({tuple(p.bits) for p in ranked}) < len(ranked)
        return orig(paths, last)
    ai._select = select
    level = [0]
    orig_choose = ai.choose
    def choose(*a):
        level[0] = 0
        return orig_choose(*a)
    ai.choose = choose
    g = Tetris(5, 10, seed)
    while not g.game_over and g.pieces_placed < 1500:
        play_turn(g, ai)
    return stats

if __name__ == "__main__":
    for preview in (1, 2):
        with Pool(11) as p:
            res = p.map(play, [(preview, s) for s in range(40)])
        tot = {k: sum(r[k] for r in res) for k in res[0]}
        print(f"preview {preview}: {tot['children']} lines -> {tot['distinct']} distinct boards "
              f"({100 * (1 - tot['distinct'] / tot['children']):.1f}% duplicates); "
              f"an unmerged top-8 would hold {tot['top8_distinct'] / tot['levels']:.2f} distinct boards on average; "
              f"{100 * tot['same_kind_dups'] / tot['levels']:.1f}% of levels have a duplicate in the top 8")
