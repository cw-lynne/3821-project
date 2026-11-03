
"""BCTS (Building Controllers for Tetris Systems).

Fixed-weight BCTS controller using the published eight-feature
linear evaluation function.
"""

from .base import Placement, TetrisAi
from .bitboard import board_to_bits, col_heights, legal_placements


# Published BCTS feature weights (Thiery & Scherrer, 2009).
WEIGHTS = {
    "rows_with_holes": -24.04,
    "column_transitions": -19.77,
    "holes": -13.08,
    "landing_height": -12.63,
    "cumulative_wells": -10.49,
    "row_transitions": -9.22,
    "eroded_piece_cells": 6.60,
    "hole_depth": -1.61,
}


def board_from_bits(bits, cols):
    """Convert row bitmasks into a boolean board."""
    return [
        [bool(row & (1 << c)) for c in range(cols)]
        for row in bits
    ]


def count_holes(board):
    """Count empty cells with at least one filled cell above them."""
    rows = len(board)
    cols = len(board[0])

    holes = 0
    hole_depth = 0
    rows_with_holes = 0

    for c in range(cols):
        filled_above = 0

        for r in range(rows):
            if board[r][c]:
                filled_above += 1
            elif filled_above > 0:
                holes += 1
                hole_depth += filled_above

    # Count rows containing at least one hole.
    for r in range(rows):
        has_hole = False
        for c in range(cols):
            if not board[r][c]:
                if any(board[above][c] for above in range(r)):
                    has_hole = True
                    break

        if has_hole:
            rows_with_holes += 1

    return holes, hole_depth, rows_with_holes


def count_row_transitions(board):
    """Count filled/empty transitions across rows.

    The left and right walls are treated as filled.
    """
    transitions = 0
    cols = len(board[0])

    for row in board:
        previous = True

        for c in range(cols):
            if row[c] != previous:
                transitions += 1
            previous = row[c]

        if not previous:
            transitions += 1

    return transitions


def count_column_transitions(board):
    """Count filled/empty transitions down columns.

    The top and bottom boundaries are treated as filled.
    """
    transitions = 0
    rows = len(board)

    for c in range(len(board[0])):
        previous = True

        for r in range(rows):
            if board[r][c] != previous:
                transitions += 1
            previous = board[r][c]

        if not previous:
            transitions += 1

    return transitions


def count_cumulative_wells(board):
    """Calculate the cumulative depth of vertical wells.

    A well cell is empty with filled cells immediately to its
    left and right. The outside walls count as filled.
    A well of depth d contributes 1 + 2 + ... + d.
    """
    rows = len(board)
    cols = len(board[0])
    total = 0

    for c in range(cols):
        depth = 0

        for r in range(rows):
            left_filled = c == 0 or board[r][c - 1]
            right_filled = c == cols - 1 or board[r][c + 1]

            if (
                not board[r][c]
                and left_filled
                and right_filled
            ):
                depth += 1
            else:
                total += depth * (depth + 1) // 2
                depth = 0

        total += depth * (depth + 1) // 2

    return total


def count_eroded_piece_cells(board, piece, x, y):
    """Count piece cells in rows completed by the placement.

    Returns:
        Number of piece cells in completed rows, multiplied by
        the number of completed rows.
    """
    rows = len(board)
    cols = len(board[0])
    full_rows = []

    # Reconstruct the board before line clearing.
    placed_board = [row[:] for row in board]

    # 'board' here is the original board, before placement.
    for pr, piece_row in enumerate(piece):
        for pc, cell in enumerate(piece_row):
            if cell:
                br = y + pr
                bc = x + pc

                if 0 <= br < rows and 0 <= bc < cols:
                    placed_board[br][bc] = True

    for r in range(rows):
        if all(placed_board[r]):
            full_rows.append(r)

    piece_cells_in_cleared_rows = 0

    for pr, piece_row in enumerate(piece):
        for pc, cell in enumerate(piece_row):
            if cell and (y + pr) in full_rows:
                piece_cells_in_cleared_rows += 1

    return len(full_rows) * piece_cells_in_cleared_rows


def evaluate(board, piece, x, y):
    """Evaluate a placement using the eight BCTS features."""
    holes, hole_depth, rows_with_holes = count_holes(board)

    features = {
        "rows_with_holes": rows_with_holes,
        "column_transitions": count_column_transitions(board),
        "holes": holes,
        "landing_height": len(board) - (y + len(piece) / 2),
        "cumulative_wells": count_cumulative_wells(board),
        "row_transitions": count_row_transitions(board),
        "eroded_piece_cells": count_eroded_piece_cells(
            board, piece, x, y
        ),
        "hole_depth": hole_depth,
    }

    return sum(
        WEIGHTS[name] * value
        for name, value in features.items()
    )


class BctsAi(TetrisAi):
    name = "bcts"
    description = "BCTS fixed-weight heuristic"

    def choose(self, board, kind):
        bits = board_to_bits(board)
        cols = len(board[0])
        heights = col_heights(bits, cols)

        best_score = float("-inf")
        best_placement = None

        for orientation, x, y, board_after, rows_cleared in (
            legal_placements(bits, heights, kind)
        ):
            # Features are evaluated on the resulting board.
            resulting_board = board_from_bits(board_after, cols)

            score = evaluate(
                resulting_board,
                orientation.matrix,
                x,
                y,
            )

            if score > best_score:
                best_score = score
                best_placement = Placement(
                    orientation.matrix,
                    x,
                )

        return best_placement
