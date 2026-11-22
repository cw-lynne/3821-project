"""BCTS with column transitions counting the top of the board as filled (as on
main up to 5da69ee) vs as empty (the usual definition, and bcts.py since the
bug-fix branch), on the same seeds.

With the top counted as filled, a column whose stack reaches the top row has 2
fewer transitions than one that doesn't, so BCTS is rewarded (2 x 19.77) for
building to the ceiling. This tests whether that explains BCTS's weak results.

    python3 experiments/bcts_column_transitions.py
"""
import os, statistics, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais import bcts
from ais.eltetris import ElTetrisAi
from ais.misakamm import MisakammAi

CURRENT = bcts.count_column_transitions


def column_transitions_top_filled(board):
    """Column transitions as on main up to 5da69ee: floor and the space above
    the board both treated as filled."""
    transitions = 0
    for c in range(len(board[0])):
        previous = True
        for r in range(len(board)):
            if board[r][c] != previous:
                transitions += 1
            previous = board[r][c]
        if not previous:
            transitions += 1
    return transitions


def play(job):
    variant, rows, seed, cap = job
    if variant == "el-tetris":
        ai = ElTetrisAi()
    elif variant == "misakamm":
        ai = MisakammAi()
    else:
        bcts.count_column_transitions = (column_transitions_top_filled if variant == "bcts (top filled)"
                                         else CURRENT)
        ai = bcts.BctsAi()
    g = Tetris(rows, 10, seed)
    while not g.game_over and g.pieces_placed < cap:
        play_turn(g, ai)
    return g.lines_cleared, not g.game_over


if __name__ == "__main__":
    variants = ["bcts (top filled)", "bcts (current)", "el-tetris", "misakamm"]
    with Pool(11) as pool:
        for rows, games, cap in [(5, 100, 5000), (10, 20, 5000)]:
            print(f"rows {rows}, {games} games (seeds 0-{games - 1}), cap {cap}, no preview")
            for v in variants:
                res = pool.map(play, [(v, rows, s, cap) for s in range(games)], chunksize=1)
                lines = [r[0] for r in res]
                print(f"  {v:<18} mean {statistics.mean(lines):>8.1f}  median {statistics.median(lines):>7.1f}"
                      f"  capped {sum(r[1] for r in res)}/{games}", flush=True)
