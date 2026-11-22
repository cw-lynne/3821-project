"""Plain BCTS vs plain Misakamm on 10 rows with no piece cap, paired by seed.

The capped 10-row run (entries 18-19) had most games hit the cap, so its means
were lower bounds. This plays every game to game over.

    python3 experiments/bcts_vs_misakamm_uncapped.py [games]
"""
import math, os, statistics, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.bcts import BctsAi
from ais.misakamm import MisakammAi

ROWS = 10


def play(job):
    name, seed = job
    ai = BctsAi() if name == "bcts" else MisakammAi()
    g = Tetris(ROWS, 10, seed)
    while not g.game_over:
        play_turn(g, ai)
    return g.lines_cleared


def sign_test(wins, losses):
    """Two-sided sign test p-value (ties dropped)."""
    n = wins + losses
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    seeds = range(games)
    with Pool(11) as pool:
        res = {n: pool.map(play, [(n, s) for s in seeds], chunksize=1) for n in ("bcts", "misakamm")}
    print(f"rows {ROWS}, {games} games (seeds 0-{games - 1}), no cap, no preview")
    for n, lines in res.items():
        ci = 1.96 * statistics.stdev(lines) / math.sqrt(len(lines))
        print(f"  {n:<9} mean {statistics.mean(lines):>8.1f} ±{ci:>7.1f}  median {statistics.median(lines):>8.1f}"
              f"  min {min(lines):>6}  max {max(lines):>6}")
    wins = sum(b > m for b, m in zip(res["bcts"], res["misakamm"]))
    losses = sum(b < m for b, m in zip(res["bcts"], res["misakamm"]))
    print(f"  BCTS better on {wins}/{games} seeds, worse on {losses}, sign test p = {sign_test(wins, losses):.3f}")
