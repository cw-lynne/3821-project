"""BCTS row transitions over every row (bcts.py) vs only the rows from the
highest filled cell down (as El-Tetris counts them), no preview, no cap.

With the walls counted as filled, every empty row above the stack adds 2
transitions, so counting them gives -9.22 x 2 x (rows - stack height): a
reward of 18.44 per row of stack height.

    python3 experiments/bcts_row_transitions.py [games] [rows ...]
"""
import math, os, statistics, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais import bcts

ALL_ROWS = bcts.count_row_transitions


def row_transitions_stack_only(board):
    """Row transitions, skipping the empty rows above the highest filled cell."""
    rows = list(board)
    while rows and not any(rows[0]):
        rows.pop(0)
    return ALL_ROWS(rows) if rows else 0


def play(job):
    variant, rows, seed = job
    bcts.count_row_transitions = ALL_ROWS if variant == "all rows" else row_transitions_stack_only
    ai = bcts.BctsAi()
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
    heights = [int(r) for r in sys.argv[2:]] or [5, 8]
    print(f"{games} games per height (seeds 0-{games - 1}), no cap, no preview")
    with Pool(11) as pool:
        for rows in heights:
            res = {v: pool.map(play, [(v, rows, s) for s in range(games)], chunksize=1)
                   for v in ("all rows", "stack only")}
            for v, lines in res.items():
                ci = 1.96 * statistics.stdev(lines) / math.sqrt(games)
                print(f"  rows {rows}  {v:<10} mean {statistics.mean(lines):>8.1f} ±{ci:>7.1f}"
                      f"  median {statistics.median(lines):>8.1f}")
            wins = sum(s > a for a, s in zip(res["all rows"], res["stack only"]))
            losses = sum(s < a for a, s in zip(res["all rows"], res["stack only"]))
            print(f"  rows {rows}  stack only better on {wins}/{games}, worse on {losses}, "
                  f"sign test p = {sign_test(wins, losses):.3f}", flush=True)
