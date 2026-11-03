from .base import Placement, TetrisAi
from .bitboard import board_to_bits, col_heights, legal_placements

# El-Tetris weights (Islam El-Ashi's tuned values)
W_LANDING = -4.500158825082766
W_ERODED = 3.4181268101392694
W_ROW_TRANS = -3.2178882868487753
W_COL_TRANS = -9.348695305445199
W_HOLES = -7.899265427351652
W_WELLS = -3.3855972247263626


def _popcount(n):
    return bin(n).count("1")


def _features(rows, width):
    """rows: row bitmasks, index 0 = top. Returns (row_trans, col_trans, holes, wells)."""
    full = (1 << width) - 1

    # Row transitions: walls count as filled; only rows from the highest block down.
    row_trans = 0
    started = False
    for r in rows:
        if r:
            started = True
        if not started:
            continue
        padded = (1 << (width + 1)) | (r << 1) | 1       # left and right walls
        row_trans += _popcount((padded ^ (padded >> 1)) & ((1 << (width + 1)) - 1))

    # Column transitions: floor counts as filled, empty space above the top doesn't count.
    col_trans = _popcount(rows[-1] ^ full)               # bottom row vs floor
    for i in range(len(rows) - 1):
        col_trans += _popcount(rows[i] ^ rows[i + 1])

    # Holes: empty cells that have a filled cell somewhere above them.
    holes = 0
    covered = 0
    for r in rows:
        holes += _popcount(covered & ~r & full)
        covered |= r

    # Wells: empty cells with filled neighbors (or walls) on both sides,
    # scored depth*(depth+1)/2 per consecutive run, scanning top -> bottom.
    wells = 0
    for c in range(width):
        depth = 0
        for r in rows:
            filled = (r >> c) & 1
            left = 1 if c == 0 else (r >> (c - 1)) & 1
            right = 1 if c == width - 1 else (r >> (c + 1)) & 1
            if filled:
                wells += depth * (depth + 1) // 2
                depth = 0
            elif left and right:
                depth += 1
        wells += depth * (depth + 1) // 2

    return row_trans, col_trans, holes, wells


class ElTetrisAi(TetrisAi):
    name = "el-tetris"  # used with --ai
    description = ("Features: landing height, rows eliminated, row/col "
                   "transitions, number of holes, well sums")  # shown in --help

    def choose(self, board, kind):
        width = len(board[0])
        n_rows = len(board)
        full = (1 << width) - 1
        bits = board_to_bits(board)
        heights = col_heights(bits, width)
        best = None

        for o, x, y, board_after, rows_cleared in legal_placements(bits, heights, kind):
            # Landing height: height of the piece's lowest row (0 = floor)
            landing = n_rows - (y + len(o.matrix))

            # Eroded cells: rows cleared * piece cells that were in cleared rows
            piece_cells_cleared = 0
            for r, piece_row in enumerate(o.rows):
                if (bits[y + r] | (piece_row << x)) == full:
                    piece_cells_cleared += _popcount(piece_row)
            eroded = rows_cleared * piece_cells_cleared

            row_trans, col_trans, holes, wells = _features(board_after, width)

            score = (W_LANDING * landing
                     + W_ERODED * eroded
                     + W_ROW_TRANS * row_trans
                     + W_COL_TRANS * col_trans
                     + W_HOLES * holes
                     + W_WELLS * wells)

            if best is None or score > best[0]:
                best = (score, o, x)

        if best is None:
            return None  # nothing fits: the game ends
        return Placement(best[1].matrix, best[2])