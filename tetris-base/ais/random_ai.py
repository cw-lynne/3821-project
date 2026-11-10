"""Baseline AI that drops each piece at a random legal spot. Also a minimal
template for writing a new AI."""

import random

from .base import Placement, TetrisAi
from .bitboard import board_to_bits, col_heights, legal_placements


class RandomAi(TetrisAi):
    name = "random"
    description = "random legal placement (baseline)"

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--random-seed", type=int, default=None,
                            help="seed for the random AI's choices")

    @classmethod
    def from_args(cls, args):
        return cls(seed=args.random_seed)

    def choose(self, board, kind, upcoming=()):
        bits = board_to_bits(board)
        options = [(o, x) for o, x, _, _, _ in
                   legal_placements(bits, col_heights(bits, len(board[0])), kind)]
        if not options:
            return None
        o, x = self.rng.choice(options)
        return Placement(o.matrix, x)
