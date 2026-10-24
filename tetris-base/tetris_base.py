import random

# Board dimensions: 10 columns (x) and 20 rows (y)
WIDTH, HEIGHT = 10, 20

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

# Colors for the shapes
COLORS = [
    (0, 210, 220), (235, 205, 0), (170, 75, 215),
    (50, 95, 220), (245, 150, 35), (65, 190, 90), (225, 65, 75)
]

class Tetris:
    def __init__(self):
        self.start()

    def start(self):
        """ Clears board and spawns a new piece """
        self.board = [[0] * WIDTH for _ in range(HEIGHT)]
        self.score = 0
        self.lines_cleared = 0
        self.game_over = False
        self.spawn()
        return self

    def spawn(self):
        """ Randomise falling pieces """
        self.kind = random.randrange(len(SHAPES))
        self.piece = [row[:] for row in SHAPES[self.kind]]
        self.x = WIDTH // 2 - len(self.piece[0]) // 2
        self.y = 0
        if not self.check_valid(self.piece, self.x, self.y):
            self.game_over = True

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
                if px < 0 or px >= WIDTH or py >= HEIGHT:
                    return False
                # Reject collisions with cells from previously locked pieces.
                if py >= 0 and self.board[py][px]:
                    return False
        return True

    def move(self, dx, dy):
        """ Move falling pieces """
        if self._valid(self.piece, self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            return True
        return False

    def step(self):
        """User Actions: Right, Left, Down, """

def main():
    return 0


if __name__ == "__main__":
    main()