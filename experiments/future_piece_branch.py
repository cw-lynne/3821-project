"""Lookahead modes on the cw/future-piece branch, seeds 0-59 of a 6-row board (cap 20000).

Only runs against that branch (it uses MisakammAi(lookahead=...) and the
three-argument play_turn). Check it out in a separate worktree and run from
there, e.g.
    git worktree add ../fp origin/cw/future-piece
    python3 experiments/future_piece_branch.py ../fp/tetris-base
"""
import statistics, sys
from multiprocessing import Pool
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from tetris_base import Tetris
from ais import play_turn
from ais.misakamm import MisakammAi

def play(job):
    lookahead, future, seed = job
    g, ai = Tetris(6, 10, seed), MisakammAi(lookahead=lookahead)
    while not g.game_over and g.pieces_placed < 20000:
        play_turn(g, ai, future)
    return g.lines_cleared

if __name__ == "__main__":
    with Pool(11) as p:
        for la, fut, name in [(False, 0, "plain"), (True, 0, "--lookahead (averaged guess)"), (True, 3, "--lookahead + known next piece")]:
            r = p.map(play, [(la, fut, s) for s in range(60)], chunksize=1)
            print(f"{name:<32} mean {statistics.mean(r):7.1f}  median {statistics.median(r):6.1f}")
