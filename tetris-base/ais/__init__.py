"""Registry of available AIs. Add new AI classes to AI_CLASSES."""

from .base import Placement, TetrisAi, play_turn
from .misakamm import MisakammAi
from .random_ai import RandomAi
from .bcts import BctsAi

AI_CLASSES = [MisakammAi, RandomAi, BctsAi]
AIS = {cls.name: cls for cls in AI_CLASSES}
DEFAULT_AI = MisakammAi.name

__all__ = ["AIS", "AI_CLASSES", "DEFAULT_AI", "Placement", "TetrisAi", "play_turn"]
