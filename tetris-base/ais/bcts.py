
"""BCTS (Building Controllers for Tetris Systems).

Fixed-weight BCTS controller using the published eight-feature
linear evaluation function, with optional beam search.
"""

from typing import NamedTuple

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

SCORE_MODES = ("sum", "final")


class _Path(NamedTuple):
    """A candidate line of play in beam search."""
    score: float
    first: object
    bits: list
    tie: tuple


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

    The floor is treated as filled and the space above the board as empty.
    Treating the top as filled would make a column that reaches the top row
    2 transitions cheaper, rewarding stacks that build up to the ceiling.
    """
    transitions = 0
    rows = len(board)

    for c in range(len(board[0])):
        previous = False

        for r in range(rows):
            if board[r][c] != previous:
                transitions += 1
            previous = board[r][c]

        if not previous:
            transitions += 1

    return transitions


def count_cumulative_wells(board):
    """Calculate the cumulative depth of vertical wells.

    A well cell is empty with filled cells immediately to its left and
    right; the outside walls count as filled. A well of depth d
    contributes 1 + 2 + ... + d.
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

    board must be the board BEFORE placing the piece.
    """
    rows = len(board)
    cols = len(board[0])
    placed_board = [row[:] for row in board]

    for pr, piece_row in enumerate(piece):
        for pc, cell in enumerate(piece_row):
            if cell:
                br = y + pr
                bc = x + pc

                if 0 <= br < rows and 0 <= bc < cols:
                    placed_board[br][bc] = True

    full_rows = [
        r for r in range(rows)
        if all(placed_board[r])
    ]

    piece_cells_in_cleared_rows = 0

    for pr, piece_row in enumerate(piece):
        for pc, cell in enumerate(piece_row):
            if cell and (y + pr) in full_rows:
                piece_cells_in_cleared_rows += 1

    return len(full_rows) * piece_cells_in_cleared_rows


def evaluate(board, piece, x, y, original_board=None):
    """Evaluate a placement using the eight BCTS features.

    board: resulting board AFTER line clearing.
    original_board: board BEFORE the placement, used for
                    calculating eroded piece cells.
    """
    holes, hole_depth, rows_with_holes = count_holes(board)

    if original_board is None:
        original_board = board

    features = {
        "rows_with_holes": rows_with_holes,
        "column_transitions": count_column_transitions(board),
        "holes": holes,
        "landing_height": len(board) - (y + len(piece) / 2),
        "cumulative_wells": count_cumulative_wells(board),
        "row_transitions": count_row_transitions(board),
        "eroded_piece_cells": count_eroded_piece_cells(
            original_board, piece, x, y
        ),
        "hole_depth": hole_depth,
    }

    return sum(
        WEIGHTS[name] * value
        for name, value in features.items()
    )


class BctsAi(TetrisAi):
    name = "bcts"
    beam_search = True
    description = "BCTS fixed-weight heuristic with optional beam search"

    def __init__(
        self,
        preview=0,
        beam_width=8,
        score_mode="final",
    ):
        if preview < 0:
            raise ValueError("preview must be >= 0")

        if beam_width < 1:
            raise ValueError("beam_width must be >= 1")

        if score_mode not in SCORE_MODES:
            raise ValueError(f"score_mode must be one of {SCORE_MODES}")

        self.preview = preview
        self.beam_width = beam_width
        self.score_mode = score_mode

    @classmethod
    def from_args(cls, args):
        return cls(
            preview=args.preview,
            beam_width=args.beam_width,
            score_mode=args.score_mode,
        )

    def _placements(self, bits, heights, kind):
        """Generate all legal placements and evaluate resulting boards."""
        cols = len(heights)
        original_board = board_from_bits(bits, cols)

        for orientation, x, y, board_after, rows_cleared in (
            legal_placements(bits, heights, kind)
        ):
            resulting_board = board_from_bits(board_after, cols)

            score = evaluate(
                resulting_board,
                orientation.matrix,
                x,
                y,
                original_board,
            )

            yield orientation, x, score, board_after

    def _first_moves(self, bits, heights, kind):
        """Generate initial candidate paths for the current piece."""
        paths = []

        for i, (orientation, x, score, sim) in enumerate(
            self._placements(bits, heights, kind)
        ):
            first = Placement(orientation.matrix, x)

            paths.append(
                _Path(
                    score=score,
                    first=first,
                    bits=sim,
                    tie=(i,),
                )
            )

        return paths

    def _select(self, paths, last):
        """Merge duplicate boards and retain the best beam_width paths.

        `last` is True after the final piece of the search.
        """
        merged = {}

        for path in paths:
            key = tuple(path.bits)
            old = merged.get(key)

            if old is None:
                merged[key] = path

            elif self.score_mode == "final" and not last:
                # In final mode, what follows depends only on the board,
                # so keep the first move that would win a tie, with the
                # higher score used for pruning.
                winner = old if old.tie <= path.tie else path
                merged[key] = winner._replace(
                    score=max(old.score, path.score)
                )

            elif (-path.score, path.tie) < (-old.score, old.tie):
                # Otherwise retain the path with the higher score.
                merged[key] = path

        ranked = sorted(
            merged.values(),
            key=lambda p: (-p.score, p.tie),
        )

        return ranked[:self.beam_width]

    def choose(self, board, kind, next_kinds=()):
        """Choose a placement, optionally using beam search."""
        cols = len(board[0])

        bits = board_to_bits(board)
        heights = col_heights(bits, cols)

        # Generate placements for the current piece.
        paths = self._first_moves(bits, heights, kind)

        if not paths:
            return None

        # Get upcoming pieces to search.
        queue = list(next_kinds)[:self.preview]

        # No preview: use the normal one-piece BCTS heuristic.
        if not queue:
            return min(
                paths,
                key=lambda p: (-p.score, p.tie)
            ).first

        # Initialise the beam with the best current placements.
        beam = self._select(paths, last=False)

        # Expand the beam using upcoming pieces.
        for depth, next_kind in enumerate(queue):
            last = depth == len(queue) - 1
            children = []

            for path in beam:
                path_heights = col_heights(path.bits, cols)

                for i, (_, _, step, sim) in enumerate(
                    self._placements(
                        path.bits,
                        path_heights,
                        next_kind,
                    )
                ):
                    if self.score_mode == "sum":
                        score = path.score + step
                    else:
                        score = step

                    children.append(
                        _Path(
                            score=score,
                            first=path.first,
                            bits=sim,
                            tie=path.tie + (i,),
                        )
                    )

            # If every retained path tops out, return the best move
            # from the previous level, judged on the unmerged paths so
            # each score matches its first move.
            if not children:
                return min(
                    paths,
                    key=lambda p: (-p.score, p.tie)
                ).first

            # Retain only the best candidate board states.
            paths = children
            beam = self._select(children, last)

        # Return the first move of the best sequence.
        return beam[0].first
