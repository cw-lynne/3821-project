"""Command line: watch an AI in the viewer, or run it headless.

    python3 main.py                                    # viewer, default AI
    python3 main.py --ai random                        # viewer, another AI
    python3 main.py --headless --rows 10 --seed 6 --pieces 0
"""

import argparse

from ais import AI_CLASSES, AIS, DEFAULT_AI, play_turn
from ais.misakamm import DEFAULT_SCORE_MODE, SCORE_MODES
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
    beam = parser.add_argument_group(
        f"beam search options ({', '.join(cls.name for cls in AI_CLASSES if cls.beam_search)})")
    beam.add_argument("--preview", type=int, default=0, metavar="N",
                      help="number of upcoming pieces the AI sees and searches "
                           "(default 0 = no search, the AI's original play)")
    beam.add_argument("--beam-width", type=int, default=8, metavar="K",
                      help="lines of play kept after each piece of the beam search (default 8)")
    beam.add_argument("--score-mode", choices=SCORE_MODES, default=DEFAULT_SCORE_MODE,
                      help="score a line by the sum of its placements' evaluations or by "
                           f"the last one only (default {DEFAULT_SCORE_MODE})")
    for cls in AI_CLASSES:
        cls.add_arguments(parser.add_argument_group(f"{cls.name} AI options"))
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.preview and not AIS[args.ai].beam_search:
        parser.error(f"--preview is not supported by the {args.ai} AI")
    ai = AIS[args.ai].from_args(args)
    if args.headless:
        run_headless(ai, args.pieces, args.rows, args.cols, args.seed)
    else:
        from viewer import run_viewer
        run_viewer(ai, args.rows, args.cols, args.seed)


if __name__ == "__main__":
    main()
