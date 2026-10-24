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

    def move(self):
        """ Move falling pieces """

    def step(self):
        """User Actions: Right, Left, Down, """

def main():
    return 0


if __name__ == "__main__":
    main()