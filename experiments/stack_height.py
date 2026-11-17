"""Average stack height per setting, measured after every placement (same seeds)."""
import statistics, sys
from multiprocessing import Pool
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais.misakamm import MisakammAi
from ais.bitboard import board_to_bits, col_heights

ROWS, GAMES, CAP = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
SETTINGS = [(0, 8, "sum"), (1, 8, "sum"), (2, 8, "sum"), (2, 8, "final"), (3, 8, "sum"), (3, 8, "final")]

def play(job):
    (p, w, m), seed = job
    g, ai = Tetris(ROWS, 10, seed), MisakammAi(preview=p, beam_width=w, score_mode=m)
    maxh, avgh, danger = [], [], 0
    while not g.game_over and g.pieces_placed < CAP:
        play_turn(g, ai)
        if g.game_over:
            break
        h = col_heights(board_to_bits(g.board), 10)
        maxh.append(max(h)); avgh.append(sum(h) / 10)
        danger += max(h) >= ROWS - 1
    n = max(len(maxh), 1)
    return g.lines_cleared, sum(maxh) / n, sum(avgh) / n, danger / n, not g.game_over

if __name__ == "__main__":
    print(f"rows={ROWS}, {GAMES} games, cap {CAP}")
    print(f"{'setting':<12}{'mean lines':>11}{'avg max h':>10}{'avg mean h':>11}{'% moves near top':>17}{'capped':>7}")
    with Pool(11) as pool:
        for s in SETTINGS:
            r = pool.map(play, [(s, seed) for seed in range(GAMES)], chunksize=1)
            name = f"{s[0]}x{s[1]}:{s[2]}" if s[0] else "control"
            print(f"{name:<12}{statistics.mean(x[0] for x in r):>11.1f}{statistics.mean(x[1] for x in r):>10.2f}"
                  f"{statistics.mean(x[2] for x in r):>11.2f}{100*statistics.mean(x[3] for x in r):>16.1f}%"
                  f"{sum(x[4] for x in r):>7}", flush=True)
