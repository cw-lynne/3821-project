from typing import NamedTuple

from .base import Placement, TetrisAi
from .bitboard import board_to_bits, col_heights, legal_placements

# El-Tetris weights (Islam El-Ashi's tuned values)
W_LANDING = -4.500158825082766
W_ERODED = 3.4181268101392694
W_ROW_TRANS = -3.2178882868487753
W_COL_TRANS = -9.348695305445199
W_HOLES = -7.899265427351652
W_WELLS = -3.3855972247263626

SCORE_MODES = ("sum", "final")
DEFAULT_SCORE_MODE = "final"


def _popcount(n):
    return bin(n).count("1")


def _features(rows, width):
    """Return (row_trans, col_trans, holes, wells)."""
    full = (1 << width) - 1

    row_trans = 0
    started = False
    for r in rows:
        if r:
            started = True
        if not started:
            continue
        padded = (1 << (width + 1)) | (r << 1) | 1
        row_trans += _popcount(
            (padded ^ (padded >> 1)) & ((1 << (width + 1)) - 1)
        )

    col_trans = _popcount(rows[-1] ^ full)
    for i in range(len(rows) - 1):
        col_trans += _popcount(rows[i] ^ rows[i + 1])

    holes = 0
    covered = 0
    for r in rows:
        holes += _popcount(covered & ~r & full)
        covered |= r

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


class _Path(NamedTuple):
    """A line of play in the beam search."""

    score: float
    tie: tuple
    first: object
    bits: list


class ElTetrisAi(TetrisAi):
    name = "el-tetris"
    beam_search = True
    description = (
        "El-Tetris with optional beam search over a piece preview "
        "(landing height, eroded cells, transitions, holes, wells)"
    )

    def __init__(
        self,
        preview=0,
        beam_width=8,
        score_mode=DEFAULT_SCORE_MODE,
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

    def _evaluate(self, bits, kind, placement, board_after,
                  rows_cleared, width, n_rows):
        """Evaluate one placement using the original El-Tetris function."""
        full = (1 << width) - 1
        o, x, y = placement

        # Landing height: height of the piece's lowest row (0 = floor).
        landing = n_rows - (y + len(o.matrix))

        # Eroded cells: cleared rows * piece cells in cleared rows.
        piece_cells_cleared = 0
        for r, piece_row in enumerate(o.rows):
            if (bits[y + r] | (piece_row << x)) == full:
                piece_cells_cleared += _popcount(piece_row)

        eroded = rows_cleared * piece_cells_cleared

        row_trans, col_trans, holes, wells = _features(
            board_after, width
        )

        return (
            W_LANDING * landing
            + W_ERODED * eroded
            + W_ROW_TRANS * row_trans
            + W_COL_TRANS * col_trans
            + W_HOLES * holes
            + W_WELLS * wells
        )

    def _placements(self, bits, heights, kind, width, n_rows):
        """Yield (orientation, x, score, board_after) for legal placements."""
        for o, x, y, board_after, rows_cleared in legal_placements(
            bits, heights, kind
        ):
            score = self._evaluate(
                bits,
                kind,
                (o, x, y),
                board_after,
                rows_cleared,
                width,
                n_rows,
            )
            yield o, x, score, board_after

    def _first_moves(self, bits, heights, kind, width, n_rows):
        """Generate every legal first move."""
        paths = []

        for i, (o, x, score, sim) in enumerate(
            self._placements(bits, heights, kind, width, n_rows)
        ):
            # Ties go to the first placement in search order, as in the
            # original El-Tetris.
            paths.append(
                _Path(
                    score,
                    (i,),
                    Placement(o.matrix, x),
                    sim,
                )
            )

        return paths

    def _select(self, paths, last):
        """Merge identical boards and retain the best beam_width paths."""
        merged = {}

        for p in paths:
            key = tuple(p.bits)
            old = merged.get(key)

            if old is None:
                merged[key] = p

            elif self.score_mode == "final" and not last:
                # In final mode, only the last placement's score matters.
                # Preserve the best first-move tie-break while retaining
                # the maximum score for beam pruning.
                winner = old if old.tie <= p.tie else p
                merged[key] = winner._replace(
                    score=max(old.score, p.score)
                )

            elif (-p.score, p.tie) < (-old.score, old.tie):
                merged[key] = p

        ranked = sorted(
            merged.values(),
            key=lambda p: (-p.score, p.tie),
        )

        return ranked[:self.beam_width]

    def choose(self, board, kind, next_kinds=()):
        width = len(board[0])
        n_rows = len(board)

        bits = board_to_bits(board)
        heights = col_heights(bits, width)

        paths = self._first_moves(
            bits, heights, kind, width, n_rows
        )

        if not paths:
            return None

        queue = list(next_kinds)[:self.preview]

        if not queue:
            # Exact original El-Tetris behavior without preview.
            best = min(paths, key=lambda p: (-p.score, p.tie))
            return best.first

        # Initialize beam with all legal first moves.
        beam = self._select(paths, last=False)

        # Search upcoming pieces one at a time.
        for depth, next_kind in enumerate(queue):
            last = depth == len(queue) - 1
            children = []

            for path in beam:
                next_heights = col_heights(path.bits, width)

                for _, _, step, sim in self._placements(
                    path.bits,
                    next_heights,
                    next_kind,
                    width,
                    n_rows,
                ):
                    if self.score_mode == "sum":
                        score = path.score + step
                    else:
                        score = step

                    children.append(
                        path._replace(score=score, bits=sim)
                    )

            if not children:
                # All retained paths top out. Fall back to the best
                # legal first move, as in the Misakamm implementation.
                best = min(paths, key=lambda p: (-p.score, p.tie))
                return best.first

            paths = children
            beam = self._select(children, last)

        return beam[0].first
