"""Command line: watch an AI in the viewer, or run it headless.

    python3 main.py                                    # viewer, default AI
    python3 main.py --ai random                        # viewer, another AI
    python3 main.py --headless --rows 10 --seed 6 --pieces 0
"""

import argparse

from ais import AI_CLASSES, AIS, DEFAULT_AI, play_turn
from tetris_base import HEIGHT, MAX_COLS, MAX_ROWS, WIDTH, Tetris


def run_headless(ai, max_pieces, rows=HEIGHT, cols=WIDTH, seed=None):
    """Play one AI game without a window and print pieces/lines like run_simple_ai.

    max_pieces <= 0 means play until the game ends.
    """
    game = Tetris(rows, cols, seed)
    while not game.game_over and (max_pieces <= 0 or game.pieces_placed < max_pieces):
        play_turn(game, ai)
    note = "" if game.game_over else f" (stopped at the piece limit, seed={game.seed})"
    print(f"pieces={game.pieces_placed} lines={game.lines_cleared}{note}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Watch a Tetris AI play, or run it headless.",
        epilog="AIs: " + "; ".join(f"{cls.name}: {cls.description}" for cls in AI_CLASSES),
    )
    parser.add_argument("--ai", choices=list(AIS), default=DEFAULT_AI,
                        help=f"which AI plays (default: {DEFAULT_AI})")
    parser.add_argument("--headless", action="store_true", help="run the AI without a window")
    parser.add_argument("--pieces", type=int, default=10000,
                        help="piece limit for --headless (0 = play until game over)")
    parser.add_argument("--rows", type=int, default=HEIGHT, help=f"board rows, 1-{MAX_ROWS}")
    parser.add_argument("--cols", type=int, default=WIDTH, help=f"board cols, 1-{MAX_COLS}")
    parser.add_argument("--seed", type=int, default=None, help="piece seed (random if omitted)")
    for cls in AI_CLASSES:
        cls.add_arguments(parser.add_argument_group(f"{cls.name} AI options"))
    return parser


def main():
    args = build_parser().parse_args()
    ai = AIS[args.ai].from_args(args)
    if args.headless:
        run_headless(ai, args.pieces, args.rows, args.cols, args.seed)
    else:
        from viewer import run_viewer
        run_viewer(ai, args.rows, args.cols, args.seed)


if __name__ == "__main__":
    main()
