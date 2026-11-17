"""Misakamm --preview 1 --beam-width 8 on seeds 0-59 of a 6-row board (cap 20000).

Comparison point for the cw/future-piece branch (see future_piece_branch.py).
"""
import statistics, sys
from multiprocessing import Pool
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.misakamm import MisakammAi

def play(seed):
    g, ai = Tetris(6, 10, seed), MisakammAi(preview=1, beam_width=8, score_mode="sum")
    while not g.game_over and g.pieces_placed < 20000:
        play_turn(g, ai)
    return g.lines_cleared

if __name__ == "__main__":
    with Pool(11) as p:
        r = p.map(play, range(60), chunksize=1)
    print(f"--preview 1 --beam-width 8: mean {statistics.mean(r):.1f}  median {statistics.median(r):.1f}")
