"""Print every no-preview AI's lines cleared per seed, for diffing two versions.

Run against the current tree and against another checkout's tetris-base (for
example a temporary worktree of main); identical output means the AIs' no-preview
play is unchanged.

    python3 experiments/no_preview_games.py [path/to/tetris-base]
"""
import os, sys
from multiprocessing import Pool
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "tetris-base"))
from tetris_base import Tetris
from ais import AIS, play_turn

NAMES = ["misakamm", "bcts", "el-tetris"]
JOBS = [(n, rows, s) for n in NAMES for rows, seeds in [(5, 200), (8, 30)] for s in range(seeds)]


def play(job):
    name, rows, seed = job
    ai = AIS[name]()
    g = Tetris(rows, 10, seed)
    while not g.game_over:
        play_turn(g, ai)
    return g.lines_cleared, g.pieces_placed


if __name__ == "__main__":
    with Pool(11) as pool:
        for (name, rows, seed), (lines, pieces) in zip(JOBS, pool.map(play, JOBS, chunksize=4)):
            print(name, rows, seed, lines, pieces)
