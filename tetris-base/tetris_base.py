"""The Tetris game and its rules. AIs live in ais/, the viewer in viewer.py and
the command line in main.py."""

import os
from collections import deque

from pcg import Pcg32K2Fast, PieceTypeRng, seed_from_int

# Default board dimensions: 10 columns (x) and 20 rows (y)
WIDTH, HEIGHT = 10, 20
MAX_ROWS, MAX_COLS = 31, 14  # Same limits as the C++ reference.

# Index 0 through 6 identifies I, O, T, J, L, S, Z respectively
SHAPES = [
    [[1, 1, 1, 1]],          # I
    [[1, 1], [1, 1]],        # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[1, 0, 0], [1, 1, 1]],  # J
    [[0, 0, 1], [1, 1, 1]],  # L
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]],  # Z
]

# The C++ draws pieces in the order I, J, L, O, S, T, Z; map them to SHAPES indices.
CPP_TO_KIND = (0, 3, 4, 1, 5, 2, 6)

SPAWN_Y = -4  # Pieces spawn fully above the board, so the stack never blocks moves.


def rotate_cw(piece):
    """Rotate a shape matrix 90 degrees clockwise."""
    return [list(row) for row in zip(*piece[::-1])]


class Tetris:
    """Classic survival rules, matching the C++ reference: pieces spawn above the
    board (the stack never blocks moving or rotating), only hard drop is allowed,
    and the game ends when a piece locks with any cell above the top row."""

    def __init__(self, rows=HEIGHT, cols=WIDTH, seed=None):
        if not 1 <= rows <= MAX_ROWS:
            raise ValueError(f"rows must be in [1, {MAX_ROWS}]")
        if not 1 <= cols <= MAX_COLS:
            raise ValueError(f"cols must be in [1, {MAX_COLS}]")
        self.rows, self.cols = rows, cols
        # Without a seed, pick a random one so the game can still be replayed.
        self.seed = seed if seed is not None else int.from_bytes(os.urandom(4), "little")
        self.start()

    def start(self):
        """ Clears board, reseeds the piece generator, and spawns a new piece """
        self.board = [[0] * self.cols for _ in range(self.rows)]
        self.score = 0
        self.lines_cleared = 0
        self.pieces_placed = 0
        self.game_over = False
        self.piece_rng = PieceTypeRng(Pcg32K2Fast(seed_from_int(self.seed)))
        self.queue = deque()  # Pieces already drawn by upcoming() but not yet spawned.
        self.spawn()
        return self

    def _draw_kind(self):
        return CPP_TO_KIND[self.piece_rng.next()]

    def upcoming(self, n):
        """Peek at the next n piece kinds without changing the piece sequence."""
        while len(self.queue) < n:
            self.queue.append(self._draw_kind())
        return list(self.queue)[:n]

    def spawn(self):
        """ Spawn the next piece above the board """
        self.kind = self.queue.popleft() if self.queue else self._draw_kind()
        self.piece = [row[:] for row in SHAPES[self.kind]]
        self.x = max(0, self.cols // 2 - len(self.piece[0]) // 2)
        self.y = SPAWN_Y

    def check_valid(self, piece, x, y):
        # dy/dx are positions *inside the piece*, not on the board.
        for dy, row in enumerate(piece):
            for dx, cell in enumerate(row):
                # Ignore empty squares of the piece shape.
                if not cell:
                    continue
                # Convert piece-local coordinates into board coordinates.
                px, py = x + dx, y + dy
                # Reject anything outside the left/right edges or below the floor.
                if px < 0 or px >= self.cols or py >= self.rows:
                    return False
                # Reject collisions with cells from previously locked pieces.
                if py >= 0 and self.board[py][px]:
                    return False
        return True

    def move(self, dx, dy):
        """ Move falling pieces """
        if self.check_valid(self.piece, self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            return True
        return False

    def landing_y(self, piece, x):
        """Row the top of `piece` would land on if hard dropped at column x."""
        y = self.y
        while self.check_valid(piece, x, y + 1):
            y += 1
        return y

    def lock(self):
        """Freeze a landed piece, remove complete rows, and spawn the next."""
        # Top-out check happens before line clears: any cell above the board ends the game.
        if any(cell and self.y + dy < 0
               for dy, row in enumerate(self.piece) for cell in row):
            self.game_over = True
            return
        for dy, row in enumerate(self.piece):
            for dx, cell in enumerate(row):
                if cell:
                    # Store 1–7: nonzero means occupied and determines color.
                    self.board[self.y + dy][self.x + dx] = self.kind + 1
        # all(row) is True if every cell in a row is nonzero (full).
        remaining = [row for row in self.board if not all(row)]
        cleared = self.rows - len(remaining)  # Number of full rows removed.
        # Add empty rows at the top, so the board keeps its height.
        self.board = [[0] * self.cols for _ in range(cleared)] + remaining
        self.lines_cleared += cleared
        self.pieces_placed += 1
        # Standardized simple scoring: 0, 100, 300, 500, 800 for 0–4 lines.
        self.score += [0, 100, 300, 500, 800][cleared]
        self.spawn()

    def step(self, action):
        """Actions: left, right, rotate, drop (hard drop only, no soft drop)"""
        if self.game_over:
            return self.get_state(), 0, True
        old_lines = self.lines_cleared # Needed to calculate this action's reward.
        # Dispatch an action to its corresponding piece movement.
        if action == "left":
            self.move(-1, 0)
        elif action == "right":
            self.move(1, 0)
        elif action == "rotate":
            # Above the board only the walls can block; shift left off the right wall.
            self.piece = rotate_cw(self.piece)
            self.x = min(self.x, self.cols - len(self.piece[0]))
        elif action == "drop":
            # Hard drop: descend until the next move would collide, then lock.
            while self.move(0, 1):
                pass
            self.lock()
        else:
            raise ValueError(f"Unknown action: {action}")
        # The reward is lines cleared by this action, NOT total score.
        return self.get_state(), self.lines_cleared - old_lines, self.game_over

    def place(self, piece, x):
        """Hard drop the current piece in the given orientation at column x.

        The piece is still above the board, so any orientation and column is reachable,
        exactly as with a sequence of rotate/left/right actions.
        """
        self.piece = [row[:] for row in piece]
        self.x = x
        return self.step("drop")

    def get_state(self):
        return {
            "board": [row[:] for row in self.board],
            "piece": [row[:] for row in self.piece],
            "x": self.x, "y": self.y,
            "score": self.score, "lines": self.lines_cleared,
            "game_over": self.game_over,
        }
