"""Python port of Misakamm's SimpleAi (classic survival rules), with an optional
beam search over a preview of upcoming pieces.

With no preview (the default) it plays exactly the same games as the C++
reference for any seed and board size.
"""

from dataclasses import astuple, dataclass
from typing import NamedTuple

from tetris_base import SHAPES

from .base import Placement, TetrisAi
from .bitboard import ORIENTATIONS, board_to_bits, col_heights, legal_placements


@dataclass
class AiWeights:
    vertical: int = 95  # Column transitions.
    hole: int = 401
    x1_hole: int = 88
    x2_hole: int = 88
    landing_height: int = 67
    rows_cleared: int = 86
    hole_depth: int = 75
    well_depth_2: int = 176
    well_depth_3: int = 99
    shape_adaptability: int = 117


ROW_TRANSITIONS_WEIGHT = 100

# How a beam search scores a sequence of placements:
#   sum:   total of every placement's evaluation
#   final: evaluation of the last placement only
SCORE_MODES = ("sum", "final")


def _build_adapt_patterns():
    """Map each bottom-profile height-diff pattern to the piece kinds it fits."""
    patterns = {}
    for kind, orientations in enumerate(ORIENTATIONS):
        if kind == 0:  # The I piece is excluded.
            continue
        unique = set()
        for o in orientations:
            if o.width <= 1:
                continue
            diff = tuple(o.bottom[i + 1] - o.bottom[i] for i in range(o.width - 1))
            # Keep both slope directions so matching is robust to contour convention.
            unique.add(diff)
            unique.add(tuple(-d for d in diff))
        for pattern in unique:
            patterns.setdefault(pattern, []).append(kind)
    return patterns


ADAPT_PATTERNS = _build_adapt_patterns()
ADAPT_SCORES = (0, 4, 6)  # Score for 0, 1, and 2+ matches of a piece kind.


def _hole_masks(cols):
    x0 = 1 | (1 << (cols - 1) if cols > 1 else 0)
    x1 = ((1 << 1) | (1 << (cols - 2))) & ~x0 if cols > 2 else 0
    x2 = ((1 << 2) | (1 << (cols - 3))) & ~x0 & ~x1 if cols > 4 else 0
    return x0, x1, x2


def _line_and_hole_metrics(bits, heights, cols):
    """Return (row_transitions, column_transitions, holes, x0, x1, x2, hole_depth)."""
    rows = len(bits)
    full_row_mask = (1 << cols) - 1
    x0_mask, x1_mask, x2_mask = _hole_masks(cols)
    inner_mask = (1 << (cols - 1)) - 1 if cols > 1 else 0
    right_edge_bit = 1 << (cols - 1)
    hole_start_row = rows - max(heights)

    row_trans = col_trans = holes = x0 = x1 = x2 = hole_depth = 0
    found_hole_depth = False
    sky_mask = full_row_mask  # Columns with no filled cell above the current row.
    prev_row = 0
    for r, row_bits in enumerate(bits):
        # The top boundary counts as empty for column transitions.
        col_trans += (row_bits if r == 0 else prev_row ^ row_bits).bit_count()
        prev_row = row_bits

        # Both side walls count as filled for row transitions.
        if not row_bits & 1:
            row_trans += 1
        row_trans += ((row_bits ^ (row_bits >> 1)) & inner_mask).bit_count()
        if not row_bits & right_edge_bit:
            row_trans += 1

        if r >= hole_start_row:
            hole_bits = ~row_bits & ~sky_mask & full_row_mask
            if hole_bits:
                holes += hole_bits.bit_count()
                x0 += (hole_bits & x0_mask).bit_count()
                x1 += (hole_bits & x1_mask).bit_count()
                x2 += (hole_bits & x2_mask).bit_count()
                # hole_depth: tallest column among the topmost row of holes.
                if not found_hole_depth:
                    for c in range(cols):
                        if hole_bits >> c & 1:
                            hole_depth = max(hole_depth, heights[c])
                    found_hole_depth = True
            sky_mask &= ~row_bits
    # The floor counts as filled for column transitions.
    col_trans += (~prev_row & full_row_mask).bit_count()
    return row_trans, col_trans, holes, x0, x1, x2, hole_depth


def _build_well_score_table(rows, well_depth_2, well_depth_3, deep_score_x10):
    # Values are stored at 10x scale (depth 1 = well2 / 5), so the caller
    # applies coefficient 6 (= 60 / 10) to the well depth score.
    table = [0] * (rows + 1)
    if rows >= 1:
        table[1] = 2 * well_depth_2
    if rows >= 2:
        table[2] = 10 * well_depth_2
    for depth in range(3, rows + 1):
        table[depth] = 10 * well_depth_3 + (depth - 2) * deep_score_x10
    return table


def _well_table_for_col(tables, cols, c):
    if c == 0 or c == cols - 1:
        return tables["x0"]
    if c == 1 or c == cols - 2:
        return tables["x1"]
    if c == 2 or c == cols - 3:
        return tables["x2"]
    return tables["normal"]


def _well_depth(heights, rows, cols, tables):
    total = largest = 0
    for c in range(cols):
        center = heights[c]
        left = heights[c - 1] if c > 0 else rows
        right = heights[c + 1] if c < cols - 1 else rows
        if left < center or right < center:
            continue
        score = _well_table_for_col(tables, cols, c)[min(left, right) - center]
        if score <= 0:
            continue
        total += score
        largest = max(largest, score)
    return 2 * total - largest


def _shape_adaptability(heights):
    matches = [0] * len(SHAPES)
    n = len(heights)
    for i in range(n - 1):
        d = heights[i + 1] - heights[i]
        for kind in ADAPT_PATTERNS.get((d,), ()):
            matches[kind] += 1
        if i + 2 < n:
            for kind in ADAPT_PATTERNS.get((d, heights[i + 2] - heights[i + 1]), ()):
                matches[kind] += 1
    return sum(ADAPT_SCORES[min(m, 2)] for m in matches[1:])


class _Path(NamedTuple):
    """A line of play in the beam search."""

    score: float   # Path score so far (see SCORE_MODES).
    tie: tuple     # Tie-break key of the first move; smaller wins.
    first: object  # Placement of the current piece that starts this line.
    bits: list     # Board after the last placement.


class MisakammAi(TetrisAi):
    name = "misakamm"
    description = ("port of Misakamm's C++ SimpleAi (~270M lines on a 20x10 board), "
                   "with optional beam search over a piece preview")

    def __init__(self, weights=None, preview=0, beam_width=8, score_mode="sum"):
        if preview < 0:
            raise ValueError("preview must be >= 0")
        if beam_width < 1:
            raise ValueError("beam_width must be >= 1")
        if score_mode not in SCORE_MODES:
            raise ValueError(f"score_mode must be one of {SCORE_MODES}")
        self.weights = weights or AiWeights()
        self.preview = preview          # Upcoming pieces searched (0 = C++ behaviour).
        self.beam_width = beam_width    # Lines kept after each piece of the search.
        self.score_mode = score_mode
        self._well_tables = None
        self._well_tables_key = None

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--preview", type=int, default=0, metavar="N",
                            help="misakamm: number of upcoming pieces the AI sees and "
                                 "searches (default 0 = same play as the C++)")
        parser.add_argument("--beam-width", type=int, default=8, metavar="K",
                            help="misakamm: lines of play kept after each piece of the "
                                 "beam search (default 8)")
        parser.add_argument("--score-mode", choices=SCORE_MODES, default="sum",
                            help="misakamm: score a line by the sum of its placements' "
                                 "evaluations or by the last one only (default sum)")

    @classmethod
    def from_args(cls, args):
        return cls(preview=args.preview, beam_width=args.beam_width,
                   score_mode=args.score_mode)

    def _well_tables_for_rows(self, rows):
        key = (rows, astuple(self.weights))
        if key != self._well_tables_key:
            w = self.weights
            self._well_tables = {
                "normal": _build_well_score_table(rows, w.well_depth_2, w.well_depth_3,
                                                  10 * w.hole),
                "x0": _build_well_score_table(rows, w.well_depth_2, w.well_depth_3,
                                              10 * w.hole + 15 * w.x1_hole),
                "x1": _build_well_score_table(rows, w.well_depth_2, w.well_depth_3,
                                              10 * (w.hole + w.x1_hole)),
                "x2": _build_well_score_table(rows, w.well_depth_2, w.well_depth_3,
                                              10 * (w.hole + w.x2_hole)),
            }
            self._well_tables_key = key
        return self._well_tables

    def _evaluate(self, bits, heights, rows_cleared, landing_height_x4, tables):
        w = self.weights
        cols = len(heights)
        row_trans, col_trans, holes, x0, x1, x2, hole_depth = \
            _line_and_hole_metrics(bits, heights, cols)
        well_depth = _well_depth(heights, len(bits), cols, tables)
        shape_adaptability = _shape_adaptability(heights)
        return (15 * w.landing_height * landing_height_x4
                + 60 * w.rows_cleared * rows_cleared
                - 60 * ROW_TRANSITIONS_WEIGHT * row_trans
                - 60 * w.vertical * col_trans
                - 60 * w.hole * holes
                - 90 * w.x1_hole * x0
                - 60 * w.x1_hole * x1
                - 60 * w.x2_hole * x2
                - 60 * w.hole_depth * hole_depth
                - 6 * well_depth
                + 10 * w.shape_adaptability * shape_adaptability)

    def _placements(self, bits, heights, kind, tables):
        """Yield (orientation, x, score, board_after) for every legal hard drop."""
        cols = len(heights)
        for o, x, y, sim, cleared in legal_placements(bits, heights, kind):
            score = self._evaluate(sim, col_heights(sim, cols), cleared,
                                   4 * y + o.landing_base, tables)
            yield o, x, score, sim

    def _first_moves(self, bits, heights, kind, tables):
        """Every placement of the current piece as a one-move _Path."""
        cols = len(heights)
        paths = []
        for i, (o, x, score, sim) in enumerate(self._placements(bits, heights, kind, tables)):
            # Ties prefer placements closer to the board center, then the smaller
            # C++ x (shape box position), then C++ search order.
            center_bias = abs(2 * x + o.width - 1 - (cols - 1))
            paths.append(_Path(score, (center_bias, x - o.offset, i), Placement(o.matrix, x), sim))
        return paths

    def _select(self, paths, last):
        """Merge lines that reach the same board, then keep the best beam_width.

        Returned best first. `last` is True after the final piece of the search.
        """
        merged = {}
        for p in paths:
            key = tuple(p.bits)
            old = merged.get(key)
            if old is None:
                merged[key] = p
            elif self.score_mode == "final" and not last:
                # Only the last placement counts, and what follows depends only on
                # the board, so keep the first move that would win a tie; the
                # higher score is just used for pruning.
                winner = old if old.tie <= p.tie else p
                merged[key] = winner._replace(score=max(old.score, p.score))
            elif (-p.score, p.tie) < (-old.score, old.tie):
                merged[key] = p
        ranked = sorted(merged.values(), key=lambda p: (-p.score, p.tie))
        return ranked[:self.beam_width]

    def choose(self, board, kind, next_kinds=()):
        rows, cols = len(board), len(board[0])
        bits = board_to_bits(board)
        heights = col_heights(bits, cols)
        tables = self._well_tables_for_rows(rows)

        paths = self._first_moves(bits, heights, kind, tables)
        if not paths:
            return None
        queue = list(next_kinds)[:self.preview]
        if not queue:
            # No preview: the C++ reference's choice, the best single placement.
            return min(paths, key=lambda p: (-p.score, p.tie)).first

        # Beam search: place the queued pieces one at a time, keeping only the
        # best beam_width distinct boards after each piece.
        beam = self._select(paths, last=False)
        for depth, next_kind in enumerate(queue):
            last = depth == len(queue) - 1
            children = []
            for path in beam:
                for _, _, step, sim in self._placements(path.bits, col_heights(path.bits, cols),
                                                        next_kind, tables):
                    score = path.score + step if self.score_mode == "sum" else step
                    children.append(path._replace(score=score, bits=sim))
            if not children:
                # Every kept line tops out on this piece: play the best line so far,
                # judged on the unmerged lines so each score matches its first move.
                return min(paths, key=lambda p: (-p.score, p.tie)).first
            paths = children
            beam = self._select(children, last)
        return beam[0].first
