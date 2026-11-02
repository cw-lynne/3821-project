# 3821-project

A Tetris environment for testing Tetris AIs, with a Python port of
[Misakamm's](https://github.com/misakamm/tetr-ai) record-setting C++ AI
(about 270 million lines on average on a 20×10 board) and a viewer for
stepping through an AI's moves.

## Quick start

```bash
pip install pygame          # only needed for the viewer
cd tetris-base
python3 main.py             # watch the default AI play
```

Requires Python 3.10 or newer.

## What's included

- **Tetris game** (`tetris_base.py`): a 7-piece game with configurable board
  size (up to 31 rows × 14 columns). It follows the classic survival rules (see
  [Rules](#rules)) and has a step API (`left`, `right`, `rotate`, `drop`) for
  agents that act one move at a time.
- **Piece generator** (`pcg.py`): a Python port of the `pcg32_k2_fast` random
  number generator and the 3-bit piece sampler from the C++ reference. Pieces
  are uniform and independent of history and the board. A given seed produces
  the same piece sequence as the C++ code.
- **Misakamm AI** (`ais/misakamm.py`): a port of the C++ `SimpleAi` with the
  same features, weights and tie-breaking. It plays exactly the same games as
  the C++ program for any seed and board size; this was checked by comparing
  340 full games against the compiled C++ program. An optional lookahead mode
  (`--lookahead`) is also ported.
- **Random AI** (`ais/random_ai.py`): drops each piece at a random legal spot.
  Useful as a baseline and as a template for new AIs.
- **Pluggable AI interface** (`ais/base.py`): any class that implements
  `choose()` can be selected with `--ai`.
- **Viewer** (`viewer.py`): step forward and back through an AI's placements,
  with the next 5 pieces previewed.
- **Headless runner** (`main.py --headless`): plays a game without a window and
  prints the result in the same format as the C++ `run_simple_ai`.

## Usage

Run everything from the `tetris-base` folder.

### Viewer

```bash
python3 main.py
```

| Key | Action |
|---|---|
| → | Show the next placement (the AI plays a new move at the end of the history) |
| ← | Step back through earlier placements |
| Hold → / ← | Scrub quickly |
| R | New game (replays the same game if `--seed` was given) |

Each frame shows the board just before the piece locks, with the AI's
placement outlined in white. The right panel previews the next 5 pieces, and
the status bar shows the move number, lines, score and seed. The AI never sees
the previews; they are for display only.

### Headless

```bash
python3 main.py --headless --pieces 5000 --seed 1
```

Prints `pieces=… lines=…`. If the piece limit is reached first, it also notes
that and prints the seed.

### Flags

| Flag | Default | Description |
|---|---|---|
| `--ai NAME` | `misakamm` | Which AI plays: `misakamm` or `random` |
| `--headless` | off | Run without a window |
| `--pieces N` | `10000` | Headless only: stop after N pieces; `0` plays until game over |
| `--rows N` | `20` | Board height, 1–31 |
| `--cols N` | `10` | Board width, 1–14 |
| `--seed N` | random | Piece seed; the same seed always gives the same pieces |
| `--lookahead` | off | misakamm only: extra one-piece search when the stack is high (stronger, much slower) |
| `--random-seed N` | random | random AI only: seed for its choices |
| `-h`, `--help` | | List all flags and available AIs |

### Examples

```bash
python3 main.py --seed 6 --rows 10                          # watch a specific game
python3 main.py --headless --rows 10 --seed 6 --pieces 0    # prints pieces=30204 lines=12073, as in the C++ README
python3 main.py --ai random --rows 10                       # watch the baseline AI
```

On the default 20×10 board the misakamm AI almost never loses, so give
headless runs a `--pieces` limit there. Use `--rows 6` to `--rows 10` to see
complete games quickly.

## Rules

The game uses the classic survival ruleset from the C++ reference, which is
also used in many Tetris AI papers:

1. Pieces spawn above the board, so the stack never blocks moving or rotating.
2. Only hard drop is allowed: no soft drop, slides or spins.
3. The game ends when a piece locks with any cell above the top row. This
   check happens before line clears.
4. Pieces come from the seeded generator described above. The C++ AI uses no
   next-piece preview.

Because of rules 1 and 2, a move is fully described by the piece's
orientation and the column it is dropped in.

## Project structure

```
tetris-base/
  main.py            command line (viewer or headless, --ai selects the AI)
  tetris_base.py     the game and its rules
  pcg.py             random number generator and piece sampler
  viewer.py          pygame step-through viewer
  ais/
    __init__.py      registry of available AIs (AI_CLASSES)
    base.py          TetrisAi interface, Placement, play_turn()
    bitboard.py      fast board helpers shared by AIs
    misakamm.py      Misakamm AI port
    random_ai.py     random baseline AI
```

## Adding a new AI

1. Create a module in `tetris-base/ais/`, for example `ais/my_ai.py`:

   ```python
   from .base import Placement, TetrisAi
   from .bitboard import board_to_bits, col_heights, legal_placements


   class MyAi(TetrisAi):
       name = "my-ai"                 # used with --ai
       description = "what it does"   # shown in --help

       def choose(self, board, kind):
           bits = board_to_bits(board)
           heights = col_heights(bits, len(board[0]))
           best = None
           for o, x, y, board_after, rows_cleared in legal_placements(bits, heights, kind):
               score = rows_cleared  # replace with your evaluation
               if best is None or score > best[0]:
                   best = (score, o, x)
           if best is None:
               return None  # nothing fits: the game ends
           return Placement(best[1].matrix, best[2])
   ```

2. Register it in `ais/__init__.py`:

   ```python
   from .my_ai import MyAi

   AI_CLASSES = [MisakammAi, RandomAi, MyAi]
   ```

3. Run it with `python3 main.py --ai my-ai`, or add `--headless`.

### What `choose()` receives and returns

- `board` is `Tetris.board`: a list of rows, top row first. `0` is an empty
  cell; a nonzero value is filled (the value is the piece kind + 1).
- `kind` is the current piece, an index into `SHAPES` in `tetris_base.py`:
  `0` I, `1` O, `2` T, `3` J, `4` L, `5` S, `6` Z.
- Return `Placement(piece, x)`, where `piece` is the shape matrix in the chosen
  orientation and `x` is the board column of its left edge. Return `None` if
  no placement fits, which ends the game.

### Helpers in `ais/bitboard.py`

Boards are stored as lists of row bitmasks (row 0 at the top, bit `c` =
column `c`), which makes evaluation fast in Python.

| Helper | Purpose |
|---|---|
| `board_to_bits(board)` | Convert `Tetris.board` to row bitmasks |
| `col_heights(bits, cols)` | Height of each column |
| `legal_placements(bits, heights, kind)` | Every legal hard drop: `(orientation, x, y, board_after, rows_cleared)` |
| `ORIENTATIONS[kind]` | Each piece's distinct rotations (`.matrix`, `.width`, `.rows`, `.bottom`) |
| `drop_y`, `lock` | Lower-level drop and lock operations |

### Command-line options for your AI

To give an AI its own flags, override two class methods. Start the flag names
with the AI's name so they don't clash with other AIs:

```python
@classmethod
def add_arguments(cls, parser):
    parser.add_argument("--my-ai-depth", type=int, default=1)

@classmethod
def from_args(cls, args):
    return cls(depth=args.my_ai_depth)
```

## Using the game from code

```python
from tetris_base import Tetris
from ais import AIS, play_turn

game = Tetris(rows=20, cols=10, seed=1)
ai = AIS["misakamm"]()
while not game.game_over and game.pieces_placed < 1000:
    play_turn(game, ai)
print(game.pieces_placed, game.lines_cleared, game.score)
```

Agents that act one move at a time can call `game.step(action)` with `"left"`,
`"right"`, `"rotate"` or `"drop"`. It returns `(state, lines_cleared_by_this_action, game_over)`.
`game.upcoming(n)` returns the next `n` pieces without changing the sequence.

## Performance

The Python AI places about 3,300 pieces per second on one core, roughly 54
times slower than the C++ version. That is fast enough for the viewer and for
games on smaller boards, but a full average game on a 20×10 board
(hundreds of millions of lines) would take days in Python.
