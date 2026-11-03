import json
from pathlib import Path

from .base import Placement, TetrisAi
from .bitboard import board_to_bits, col_heights, legal_placements


GAMMA = 0.9999
MAX_HEIGHT = 20
MAX_HOLES = 200
TERMINAL_HEIGHT = 16

DEFAULT_TABLE = Path(__file__).with_name("tsitsiklis_values.json")


def extract_features(bits, cols):
    """Extract (wall height, number of holes) from a board."""

    heights = col_heights(bits, cols)
    wall_height = max(heights, default=0)

    holes = 0

    # A hole is an empty cell with occupied cells both above and below it.
    for c in range(cols):
        occupied_rows = [
            r for r in range(len(bits))
            if bits[r] & (1 << c)
        ]

        if len(occupied_rows) < 2:
            continue

        top = occupied_rows[0]
        bottom = occupied_rows[-1]

        occupied = len(occupied_rows)
        holes += (bottom - top + 1) - occupied

    return (
        min(wall_height, MAX_HEIGHT),
        min(holes, MAX_HOLES)
    )


def load_value_table(path=DEFAULT_TABLE):
    """Load the learned value table, or initialise it to zero."""

    if not path.exists():
        return [
            [0.0] * (MAX_HOLES + 1)
            for _ in range(MAX_HEIGHT + 1)
        ]

    with open(path, "r") as f:
        table = json.load(f)

    if len(table) != MAX_HEIGHT + 1:
        raise ValueError("Invalid Tsitsiklis value table height")

    if any(len(row) != MAX_HOLES + 1 for row in table):
        raise ValueError("Invalid Tsitsiklis value table width")

    return table


class TsitsiklisAi(TetrisAi):
    name = "tsitsiklis"
    description = "Tsitsiklis and van Roy feature-based value iteration"

    def __init__(self):
        self.values = load_value_table()

    def value(self, bits, cols):
        """Estimate the future value of a board."""

        height, holes = extract_features(bits, cols)

        # Match the terminal-height convention in the original paper.
        if height > TERMINAL_HEIGHT:
            return 0.0

        return self.values[height][holes]

    def choose(self, board, kind):
        bits = board_to_bits(board)
        cols = len(board[0])
        heights = col_heights(bits, cols)

        best = None

        for o, x, y, board_after, rows_cleared in legal_placements(
            bits, heights, kind
        ):
            future_value = self.value(board_after, cols)

            # Bellman-style action evaluation:
            # immediate reward + discounted future value.
            score = rows_cleared + GAMMA * future_value

            if best is None or score > best[0]:
                best = (score, o, x)

        if best is None:
            return None

        return Placement(best[1].matrix, best[2])

    
    def train_step(self, board, kind, alpha=0.1):
        """Perform one asynchronous approximate value iteration update."""

        bits = board_to_bits(board)
        cols = len(board[0])

        height, holes = extract_features(bits, cols)

        if height > TERMINAL_HEIGHT:
            return

        heights = col_heights(bits, cols)

        best_target = 0.0

        for o, x, y, board_after, rows_cleared in legal_placements(
            bits, heights, kind
        ):
            target = (
                rows_cleared
                + GAMMA * self.value(board_after, cols)
            )

            best_target = max(best_target, target)

        # Update the value associated with this feature combination.
        old_value = self.values[height][holes]

        self.values[height][holes] = (
            (1 - alpha) * old_value
            + alpha * best_target
        )

    def save(self, path=DEFAULT_TABLE):
        """Save the learned value table."""

        with open(path, "w") as f:
            json.dump(self.values, f)

