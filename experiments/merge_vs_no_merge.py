"""Beam search with and without merging duplicate boards, on the same seeds as benchmark.py."""
import math, statistics, sys, time
from multiprocessing import Pool
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.misakamm import MisakammAi

SETTINGS = [(1, 8), (2, 2), (2, 8), (3, 8)]
GAMES, ROWS, CAP = 100, 5, 5000

class NoMergeAi(MisakammAi):
    def _select(self, paths, last):
        return sorted(paths, key=lambda p: (-p.score, p.tie))[:self.beam_width]

def play(job):
    merge, (preview, width), seed = job
    cls = MisakammAi if merge else NoMergeAi
    g, ai = Tetris(ROWS, 10, seed), cls(preview=preview, beam_width=width, score_mode="final")
    t = time.perf_counter()
    while not g.game_over and g.pieces_placed < CAP:
        play_turn(g, ai)
    return g.lines_cleared, g.pieces_placed, time.perf_counter() - t, not g.game_over

def row(name, res):
    lines = [r[0] for r in res]
    ci = 1.96 * statistics.stdev(lines) / math.sqrt(len(lines))
    ms = 1000 * sum(r[2] for r in res) / sum(r[1] for r in res)
    print(f"  {name:<10}{statistics.mean(lines):>9.1f} {'±%.1f' % ci:>8} {statistics.median(lines):>8.1f}"
          f" {ms:>8.2f} {sum(r[3] for r in res):>4}/{len(res)}", flush=True)
    return lines

if __name__ == "__main__":
    print(f"rows {ROWS}, {GAMES} games (seeds 0-{GAMES - 1}), cap {CAP}, final scoring")
    print(f"  {'':<10}{'mean':>9} {'95% CI':>8} {'median':>8} {'ms/move':>8} capped")
    with Pool(11) as pool:
        for s in SETTINGS:
            print(f"{s[0]}x{s[1]}:")
            out = {}
            for merge in (True, False):
                res = pool.map(play, [(merge, s, seed) for seed in range(GAMES)], chunksize=1)
                out[merge] = row("merge" if merge else "no merge", res)
            m, n = out[True], out[False]
            print(f"  merging clears more on {sum(a > b for a, b in zip(m, n))} seeds, fewer on "
                  f"{sum(a < b for a, b in zip(m, n))}, same on {sum(a == b for a, b in zip(m, n))}", flush=True)
