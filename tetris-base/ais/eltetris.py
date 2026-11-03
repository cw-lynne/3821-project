from .base import Placement, TetrisAi
from .bitboard import board_to_bits, col_heights, legal_placements

# El-Tetris weights (Islam El-Ashi's tuned values)
W_LANDING = -4.500158825082766
W_ERODED = 3.4181268101392694
W_ROW_TRANS = -3.2178882868487753
W_COL_TRANS = -9.348695305445199
W_HOLES = -7.899265427351652
W_WELLS = -3.3855972247263626

# Set to False if row index 0 is the TOP of the board in your bitboard.
ROW0_IS_BOTTOM = True


def _to_rows(b, width):
    """Return a list of row bitmasks, index 0 = bottom row."""
    rows = []
    for r in b:
        if isinstance(r, int):
            rows.append(r)
        else:
            rows.append(sum(1 << c for c, v in enumerate(r) if v))
    if not ROW0_IS_BOTTOM:
        rows.reverse()
    return rows


def _features(rows, width):
    """Row transitions, column transitions, holes, wells for a board."""
    # Row transitions (walls count as filled), up to the highest filled row
    top = 0
    for i, r in enumerate(rows):
        if r:
            top = i + 1
    row_trans = 0
    for r in rows[:top]:
        last = True
        for c in range(width):
            now = bool((r >> c) & 1)
            if now != last:
                row_trans += 1
            last = now
        if not last:  # right wall
            row_trans += 1

    # Column transitions (floor counts as filled), plus holes
    col_trans = 0
    holes = 0
    for c in range(width):
        last = True
        seen_block = False
        for r in reversed(rows):  # top -> bottom, only for hole counting
            filled = bool((r >> c) & 1)
            if filled:
                seen_block = True
            elif seen_block:
                holes += 1
        for r in rows:  # bottom -> top
            now = bool((r >> c) & 1)
            if now != last:
                col_trans += 1
            last = now

    # Wells: empty cells with filled (or wall) neighbors on both sides,
    # scored as depth*(depth+1)/2 per consecutive run
    wells = 0
    for c in range(width):
        depth = 0
        for r in reversed(rows):
            filled = (r >> c) & 1
            left = True if c == 0 else (r >> (c - 1)) & 1
            right = True if c == width - 1 else (r >> (c + 1)) & 1
            if not filled and left and right:
                depth += 1
            elif filled:
                wells += depth * (depth + 1) // 2
                depth = 0
        wells += depth * (depth + 1) // 2

    return row_trans, col_trans, holes, wells


class ElTetrisAi(TetrisAi):
    name = "el-tetris"  # used with --ai
    description = ("Features: landing height, rows eliminated, row/col "
                   "transitions, number of holes, well sums")  # shown in --help

    def choose(self, board, kind):
        width = len(board[0])
        bits = board_to_bits(board)
        heights = col_heights(bits, width)
        best = None

        for o, x, y, board_after, rows_cleared in legal_placements(bits, heights, kind):
            rows = _to_rows(board_after, width)
            row_trans, col_trans, holes, wells = _features(rows, width)

            landing = y
            eroded = rows_cleared * rows_cleared  # see note below

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