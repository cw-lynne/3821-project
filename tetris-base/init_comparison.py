"""Compare the registered AIs by lines cleared, without piece preview.

Every AI plays the same seeds, so they all see the same pieces, and each game
runs until game over. AIs that use a preview (lookahead) are left out; misakamm
plays with its default of no preview, exactly like the C++ version.

    python3 init_comparison.py                     # 5 games on a 10-row board
    python3 init_comparison.py --games 20 --first-seed 100
"""

import argparse
import os
import statistics
from multiprocessing import Pool

from ais import AI_CLASSES, AIS, play_turn
from ais.random_ai import RandomAi
from tetris_base import MAX_ROWS, Tetris


def make_ai(name, seed):
    cls = AIS[name]
    # Seed the random AI from the game so its results are reproducible too.
    return cls(seed=seed) if cls is RandomAi else cls()


def play_game(job):
    """Play one game to game over (or the cap); runs in a worker process."""
    name, rows, cols, seed, cap = job
    game = Tetris(rows, cols, seed)
    ai = make_ai(name, seed)
    while not game.game_over and (cap <= 0 or game.pieces_placed < cap):
        play_turn(game, ai)
    return game.lines_cleared, not game.game_over


def main():
    parser = argparse.ArgumentParser(description="Compare AIs (no lookahead) by lines cleared.")
    parser.add_argument("--rows", type=int, default=10, help="board rows (default 10)")
    parser.add_argument("--cols", type=int, default=10, help="board cols (default 10)")
    parser.add_argument("--games", type=int, default=5, help="games per AI (default 5)")
    parser.add_argument("--first-seed", type=int, default=0,
                        help="games use seeds first-seed .. first-seed+games-1 (default 0)")
    parser.add_argument("--cap", type=int, default=0,
                        help="stop a game after this many pieces; 0 = no cap (default 0)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                        help="parallel processes (default: CPU count - 1)")
    args = parser.parse_args()
    if not 1 <= args.rows <= MAX_ROWS:
        parser.error(f"--rows must be in [1, {MAX_ROWS}]")

    names = [cls.name for cls in AI_CLASSES if make_ai(cls.name, 0).preview == 0]
    seeds = list(range(args.first_seed, args.first_seed + args.games))
    jobs = [(name, args.rows, args.cols, seed, args.cap) for name in names for seed in seeds]
    print(f"Board {args.rows}x{args.cols}, {args.games} games per AI (seeds {seeds[0]}-{seeds[-1]}), "
          f"cap {args.cap or 'none'}\n")

    with Pool(args.workers) as pool:
        results = pool.map(play_game, jobs, chunksize=1)

    seed_width = max(8, max(len(str(s)) for s in seeds) + 5)
    header = f"{'AI':<12}" + "".join(f"{'seed ' + str(s):>{seed_width}}" for s in seeds) + f"{'mean':>12}"
    print(header)
    print("-" * len(header))
    capped = False
    for i, name in enumerate(names):
        games = results[i * len(seeds):(i + 1) * len(seeds)]
        cells = ""
        for lines, was_capped in games:
            cells += f"{str(lines) + ('*' if was_capped else ''):>{seed_width}}"
            capped |= was_capped
        print(f"{name:<12}{cells}{statistics.mean(lines for lines, _ in games):>12.1f}")
    if capped:
        print("\n* hit the piece cap, so that game's lines are a lower bound.")


if __name__ == "__main__":
    main()
