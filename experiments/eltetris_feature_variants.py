"""El-Tetris (main) feature definitions vs alternatives, no preview, no cap.

  main:          eltetris.py as on main (landing height = the piece's bottom row,
                 row transitions only from the highest filled cell down).
  landing mid:   landing height = bottom row + piece height / 2, as El-Ashi
                 defines it ("height of the column + height of the piece / 2").
  all rows:      row transitions over every row, including empty rows above.
  mid+all rows:  both changes.

    python3 experiments/eltetris_feature_variants.py [games] [rows ...]
"""
import math, os, statistics, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais import eltetris as et
from ais.base import Placement
from ais.bitboard import board_to_bits, col_heights, legal_placements

VARIANTS = ["main", "landing mid", "all rows", "mid+all rows"]


class VariantAi(et.ElTetrisAi):
    def __init__(self, variant):
        self.mid = "mid" in variant
        self.all_rows = "all rows" in variant

    def choose(self, board, kind):
        width = len(board[0])
        n_rows = len(board)
        full = (1 << width) - 1
        bits = board_to_bits(board)
        heights = col_heights(bits, width)
        best = None
        for o, x, y, board_after, rows_cleared in legal_placements(bits, heights, kind):
            landing = n_rows - (y + len(o.matrix))
            if self.mid:
                landing += len(o.matrix) / 2
            piece_cells_cleared = 0
            for r, piece_row in enumerate(o.rows):
                if (bits[y + r] | (piece_row << x)) == full:
                    piece_cells_cleared += et._popcount(piece_row)
            eroded = rows_cleared * piece_cells_cleared
            row_trans, col_trans, holes, wells = et._features(board_after, width)
            if self.all_rows:
                # Each empty row above the stack has 2 transitions (wall -> empty -> wall).
                row_trans += 2 * next((i for i, r in enumerate(board_after) if r), n_rows)
            score = (et.W_LANDING * landing + et.W_ERODED * eroded + et.W_ROW_TRANS * row_trans
                     + et.W_COL_TRANS * col_trans + et.W_HOLES * holes + et.W_WELLS * wells)
            if best is None or score > best[0]:
                best = (score, o, x)
        return None if best is None else Placement(best[1].matrix, best[2])


def play(job):
    variant, rows, seed = job
    ai = VariantAi(variant)
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
    print(f"{games} games per height (seeds 0-{games - 1}), no cap, no preview; sign test vs main")
    with Pool(11) as pool:
        for rows in heights:
            res = {v: pool.map(play, [(v, rows, s) for s in range(games)], chunksize=1) for v in VARIANTS}
            for v, lines in res.items():
                ci = 1.96 * statistics.stdev(lines) / math.sqrt(games)
                wins = sum(a > b for a, b in zip(lines, res["main"]))
                losses = sum(a < b for a, b in zip(lines, res["main"]))
                print(f"  rows {rows}  {v:<13} mean {statistics.mean(lines):>8.1f} ±{ci:>7.1f}"
                      f"  median {statistics.median(lines):>7.1f}  better {wins:>3}/{games}"
                      f"  p {sign_test(wins, losses):.3f}", flush=True)
