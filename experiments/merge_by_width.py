"""Merging duplicate boards vs not merging, across beam widths (Misakamm, final scoring).

Entry 11 found merging helps at width 2 and makes no significant difference at
width 8. This repeats the comparison at preview 2 for widths 2-32 on the same
seeds, and also measures how many of the K lines kept without merging are
distinct boards (the duplicates are what merging removes).

    python3 experiments/merge_by_width.py [games] [width ...]
"""
import math, os, statistics, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.misakamm import MisakammAi

ROWS, CAP, PREVIEW = 5, 5000, 2


class NoMergeAi(MisakammAi):
    """Keeps the top K lines with duplicates included, counting distinct boards kept."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kept = self.distinct = 0

    def _select(self, paths, last):
        kept = sorted(paths, key=lambda p: (-p.score, p.tie))[:self.beam_width]
        if not last:
            self.kept += len(kept)
            self.distinct += len({tuple(p.bits) for p in kept})
        return kept


def play(job):
    merge, width, seed = job
    cls = MisakammAi if merge else NoMergeAi
    g, ai = Tetris(ROWS, 10, seed), cls(preview=PREVIEW, beam_width=width, score_mode="final")
    t = time.perf_counter()
    while not g.game_over and g.pieces_placed < CAP:
        play_turn(g, ai)
    distinct = (ai.distinct, ai.kept) if not merge else (0, 0)
    return g.lines_cleared, g.pieces_placed, time.perf_counter() - t, not g.game_over, distinct


def sign_test(wins, losses):
    """Two-sided sign test p-value (ties dropped)."""
    n = wins + losses
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    widths = [int(w) for w in sys.argv[2:]] or [2, 4, 8, 16, 32]
    print(f"rows {ROWS}, {games} games (seeds 0-{games - 1}), cap {CAP}, preview {PREVIEW}, final scoring")
    print(f"{'width':>5} {'merge mean':>11} {'no-merge mean':>14} {'merge med':>10} {'no-merge med':>13}"
          f" {'merge better':>13} {'worse':>6} {'p':>6} {'distinct kept':>14} {'ms/move':>8} {'capped':>9}")
    with Pool(11) as pool:
        for w in widths:
            out = {m: pool.map(play, [(m, w, s) for s in range(games)], chunksize=1) for m in (True, False)}
            m, n = ([r[0] for r in out[k]] for k in (True, False))
            wins = sum(a > b for a, b in zip(m, n))
            losses = sum(a < b for a, b in zip(m, n))
            distinct = sum(r[4][0] for r in out[False]) / max(sum(r[4][1] for r in out[False]), 1)
            ms = 1000 * sum(r[2] for r in out[True]) / sum(r[1] for r in out[True])
            capped = f"{sum(r[3] for r in out[True])}/{sum(r[3] for r in out[False])}"
            print(f"{w:>5} {statistics.mean(m):>11.1f} {statistics.mean(n):>14.1f} {statistics.median(m):>10.1f}"
                  f" {statistics.median(n):>13.1f} {wins:>13} {losses:>6} {sign_test(wins, losses):>6.3f}"
                  f" {100 * distinct:>13.1f}% {ms:>8.2f} {capped:>9}", flush=True)
