"""The interface every Tetris AI implements."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Placement:
    """Where to hard drop the current piece."""

    piece: list  # Shape matrix in the chosen orientation (same format as SHAPES).
    x: int       # Board column of the shape's left edge.


class TetrisAi(ABC):
    """Base class for AIs.

    To add an AI: subclass this in a new module under ais/, give it a unique
    `name`, implement choose(), and add the class to AI_CLASSES in ais/__init__.py.
    It then shows up in `main.py --ai`.
    """

    name = ""         # Used for --ai on the command line.
    description = ""  # Shown in --help.

    @abstractmethod
    def choose(self, board, kind, upcoming=()):
        """Pick a placement for piece `kind` (an index into SHAPES).

        `board` is Tetris.board: a list of rows, top row first; 0 is empty and
        nonzero is filled. Return a Placement, or None if nothing fits (game over).
        """

    @classmethod
    def add_arguments(cls, parser):
        """Add this AI's own command-line options (prefix them with the AI name)."""

    @classmethod
    def from_args(cls, args):
        """Build the AI from parsed command-line options."""
        return cls()


def play_turn(game, ai, future_pieces):
    """Ask `ai` where to put the current piece and play it.

    Returns (placement, landing_y), or None if the AI found no placement, in
    which case the game is over.
    """
    if game.game_over:
        return None

    if future_pieces < 0:
        raise ValueError("Future Pieces must be non-negative")

    upcoming = tuple(game.upcoming(future_pieces))
    
    placement = ai.choose(game.board, game.kind, upcoming)
    if placement is None:
        game.game_over = True
        return None
    y = game.landing_y(placement.piece, placement.x)
    game.place(placement.piece, placement.x)
    return placement, y
