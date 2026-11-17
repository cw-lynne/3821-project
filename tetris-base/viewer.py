"""Pygame viewer: step through an AI's placements with the arrow keys."""

from ais import play_turn
from tetris_base import SHAPES, Tetris

# Colors for the shapes
COLORS = [
    (0, 210, 220), (235, 205, 0), (170, 75, 215),
    (50, 95, 220), (245, 150, 35), (65, 190, 90), (225, 65, 75)
]

PREVIEW_COUNT = 5  # Upcoming pieces shown in the side panel (more if the AI sees more).


def record_frame(game, ai):
    """Play one AI placement and return a frame showing it: the board before the
    piece locks, plus the piece at its landing position. Returns None on game over."""
    board = [row[:] for row in game.board]
    kind, lines, score = game.kind, game.lines_cleared, game.score
    turn = play_turn(game, ai)
    if turn is None:
        return None
    placement, y = turn
    return {
        "board": board, "kind": kind,
        "piece": placement.piece, "x": placement.x, "y": y,
        "lines": lines, "score": score,
        # Locking spawns the following piece; it and the ones after it are shown in
        # the panel. The AI saw the first ai.preview of them when choosing this move.
        "next_kinds": [] if game.game_over
        else [game.kind] + game.upcoming(max(PREVIEW_COUNT, ai.preview) - 1),
    }


def run_viewer(ai, rows, cols, seed=None):
    import pygame

    pygame.init()
    cell = min(30, 600 // rows)  # Keep tall boards on screen.

    # Side panel for the next-piece preview. Every shape is at most 2 rows tall;
    # slots shrink so a long preview still fits on screen.
    panel_width = max(5 * cell, 150)
    slot_height = max(28, min(68, 760 // max(PREVIEW_COUNT, ai.preview)))
    preview_cell = (slot_height - 20) // 2
    panel_height = 40 + max(PREVIEW_COUNT, ai.preview) * slot_height
    area_height = max(rows * cell, panel_height)  # Board or panel, whichever is taller.
    screen = pygame.display.set_mode((cols * cell + panel_width, area_height + 55))
    pygame.display.set_caption(f"Tetris AI Viewer: {ai.name}")
    # Holding an arrow key repeats it, for quickly scrubbing through placements.
    pygame.key.set_repeat(250, 40)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    def new_game():
        # With a seed, R replays the same game; otherwise each game gets a new seed.
        game = Tetris(rows, cols, seed)
        return game, [record_frame(game, ai)]

    game, history = new_game()
    index = 0  # Frame currently shown.
    running = True

    # Viewer loop: arrow keys step through the AI's placements -> render frame.
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game, history = new_game()
                    index = 0
                elif event.key == pygame.K_LEFT:
                    index = max(0, index - 1)
                elif event.key == pygame.K_RIGHT:
                    # Past the newest frame, ask the AI for its next placement.
                    if index == len(history) - 1 and history[-1] is not None:
                        history.append(record_frame(game, ai))
                    index = min(len(history) - 1, index + 1)

        screen.fill((18, 20, 28))
        frame = history[index]
        if frame is None:
            # Game-over frame: show the final board with no pending piece.
            frame = {"board": game.board, "piece": [], "x": 0, "y": 0, "kind": 0,
                     "next_kinds": [], "lines": game.lines_cleared, "score": game.score}

        for y, row in enumerate(frame["board"]):
            for x, value in enumerate(row):
                rect = pygame.Rect(x * cell, y * cell, cell, cell)
                pygame.draw.rect(screen, COLORS[value - 1] if value else (31, 35, 45), rect)
                pygame.draw.rect(screen, (56, 60, 72), rect, 1)

        # The AI's placement for this frame, outlined so it stands out from the stack.
        for dy, row in enumerate(frame["piece"]):
            for dx, filled in enumerate(row):
                if filled and 0 <= frame["y"] + dy < rows:
                    rect = pygame.Rect((frame["x"] + dx) * cell, (frame["y"] + dy) * cell,
                                       cell, cell)
                    pygame.draw.rect(screen, COLORS[frame["kind"]], rect)
                    pygame.draw.rect(screen, (255, 255, 255), rect, 3)

        # Upcoming-piece previews stacked down the right panel, soonest at the top.
        # Pieces the AI saw when choosing this move are outlined.
        panel_x = cols * cell + 15
        title = f"Next (AI saw {ai.preview})" if ai.preview else "Next"
        screen.blit(font.render(title, True, (245, 245, 245)), (panel_x, 10))
        for slot, kind in enumerate(frame["next_kinds"]):
            top = 40 + slot * slot_height
            if slot < ai.preview:
                outline = pygame.Rect(panel_x - 5, top - 4, 4 * preview_cell + 10,
                                      2 * preview_cell + 8)
                pygame.draw.rect(screen, (255, 215, 90), outline, 2)
            for dy, row in enumerate(SHAPES[kind]):
                for dx, filled in enumerate(row):
                    if filled:
                        rect = pygame.Rect(panel_x + dx * preview_cell, top + dy * preview_cell,
                                           preview_cell, preview_cell)
                        pygame.draw.rect(screen, COLORS[kind], rect)
                        pygame.draw.rect(screen, (56, 60, 72), rect, 1)

        status =(f"Move {index + 1}/{len(history)} | Lines: {frame['lines']}"
                  f" | Score: {frame['score']}")
        if history[index] is None:
            status = f"GAME OVER | Lines: {frame['lines']} | R: new game"
        status += f" | Seed: {game.seed}"
        screen.blit(font.render(status, True, (245, 245, 245)), (10, area_height + 8))
        hint = "Left/Right: step through moves | R: new game"
        screen.blit(font.render(hint, True, (150, 155, 170)), (10, area_height + 30))
        pygame.display.flip()

    pygame.quit()
