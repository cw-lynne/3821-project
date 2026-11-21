"""Plain BCTS vs plain Misakamm across board heights, no piece cap, paired by seed.

Published records (20 rows) put Misakamm about 7.7x ahead of BCTS (270M vs 35M
lines). This checks whether the gap grows with board height.

    python3 experiments/bcts_vs_misakamm_heights.py [games] [rows ...]
"""
import math, os, statistics, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.bcts import BctsAi
from ais.misakamm import MisakammAi


def play(job):
    name, rows, seed = job
    ai = BctsAi() if name == "bcts" else MisakammAi()
    g = Tetris(rows, 10, seed)
    while not g.game_over:
        play_turn(g, ai)
    return g.lines_cleared


def sign_test(wins, losses):
    """Two-sided sign test p-value (ties dropped)."""
    n = wins + losses
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    heights = [int(r) for r in sys.argv[2:]] or [5, 6, 7, 8, 9]
    print(f"{games} games per height (seeds 0-{games - 1}), no cap, no preview")
    print(f"{'rows':>4} {'bcts mean':>10} {'misakamm mean':>14} {'mean ratio':>11} "
          f"{'bcts median':>12} {'misakamm median':>16} {'median ratio':>13} {'m wins':>7} {'p':>7}")
    with Pool(11) as pool:
        for rows in heights:
            b, m = (pool.map(play, [(n, rows, s) for s in range(games)], chunksize=1)
                    for n in ("bcts", "misakamm"))
            wins = sum(y > x for x, y in zip(b, m))
            losses = sum(y < x for x, y in zip(b, m))
            print(f"{rows:>4} {statistics.mean(b):>10.1f} {statistics.mean(m):>14.1f} "
                  f"{statistics.mean(m) / statistics.mean(b):>10.2f}x {statistics.median(b):>12.1f} "
                  f"{statistics.median(m):>16.1f} {statistics.median(m) / statistics.median(b):>12.2f}x "
                  f"{wins:>3}/{games} {sign_test(wins, losses):>7.3f}", flush=True)
