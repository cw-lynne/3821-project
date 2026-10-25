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
    import pygame

    pygame.init()
    cell = 30

    screen = pygame.display.set_mode((WIDTH * cell, HEIGHT * cell + 55))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)
    game = Tetris()
    fall_time = 0
    running = True

    # Main game loop: handle input -> apply gravity -> render board.
    while running:
        elapsed = clock.tick(60)  # Time elapsed since the previous frame (ms).
        fall_time += elapsed
        # Read window-close and keyboard events.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()
                    fall_time = 0
                elif not game.game_over:
                    # Translate keyboard keys into actions for Tetris.step().
                    keys = {
                        pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
                        pygame.K_UP: "rotate", pygame.K_DOWN: "down",
                        pygame.K_SPACE: "drop",
                    }
                    if event.key in keys:
                        game.step(keys[event.key])

        if fall_time >= 500 and not game.game_over:
            game.step("tick")
            fall_time = 0

        display = [row[:] for row in state["board"]]
        if not game.game_over:
            for dy, row in enumerate(game.piece):
                for dx, filled in enumerate(row):
                    if filled and 0 <= game.y + dy < HEIGHT:
                        display[game.y + dy][game.x + dx] = game.kind + 1

        for y, row in enumerate(display):
            for x, value in enumerate(row):
                rect = pygame.Rect(x * cell, y * cell, cell, cell)
                pygame.draw.rect(screen, COLORS[value - 1] if value else (31, 35, 45), rect)
                pygame.draw.rect(screen, (56, 60, 72), rect, 1)
        
        screen.fill((18, 20, 28))
        state = game.get_state()

        status = f"Score: {game.score}   Lines Cleared: {game.lines_cleared}"
        if game.game_over:
            status = "GAME OVER  |  R to restart"
        screen.blit(font.render(status, True, (245, 245, 245)), (10, HEIGHT * cell + 14))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()