# 3821-project

Tetris AIs that use a preview of upcoming pieces. The project contains a
Python port of Misakamm's C++ Tetris AI (https://github.com/misakamm/tetr-ai),
which plays exactly like the C++, two other published controllers (BCTS by
Thiery & Scherrer, and El-Tetris by El-Ashi), and a beam search shared by all
three that lets them search over the next N pieces.

This README explains how to reproduce the benchmarks:

1. Plain Misakamm (no preview), checked against the C++.
2. Misakamm with a piece preview.
3. All three AIs with a preview.

It then explains the design choices behind the benchmark and the search, and
the further analysis built on them. Every experiment is logged in
`experiments/log.txt`, with its script in `experiments/` and its output in
`experiments/results/`.

## Setup

Python 3.10 or newer. No packages are needed for benchmarking (pygame is only
needed for the viewer). Run every command from the `tetris-base` folder:

    cd tetris-base

## 1. Plain Misakamm (no preview)

### Check that the port matches the C++

    python3 main.py --headless --rows 10 --seed 6 --pieces 0

This plays one game to the end and should print `pieces=30204 lines=12073`,
the same result as the C++ `run_simple_ai` for this seed and board. The Python
AI plays exactly the same moves as the C++ for any seed and board size (340
full games were checked against the compiled C++ program).

### Average over many games

    python3 benchmark.py --rows 10 --games 20 --cap 0 --settings

`--settings` with nothing after it runs only the plain AI. This takes about
20 seconds and gives a mean of 5013.1 lines (median 3471.5) over seeds 0-19.

Flags for `main.py` (single games):

| Flag | Default | Meaning |
|---|---|---|
| `--ai NAME` | misakamm | Which AI plays: `misakamm`, `random`, `el-tetris` or `bcts` |
| `--headless` | off | Play without a window and print `pieces=... lines=...` |
| `--rows N` | 20 | Board height (1-31) |
| `--cols N` | 10 | Board width (1-14) |
| `--seed N` | random | Seed for the piece sequence. The same seed always gives the same pieces, in both Python and C++ |
| `--pieces N` | 10000 | Stop after N pieces; 0 plays until game over. On a 20-row board the AI almost never loses, so keep a limit there |
| `--preview N` | 0 | Upcoming pieces the AI sees (see section 2). 0 plays exactly like the C++. Works for `misakamm`, `bcts` and `el-tetris` |
| `--beam-width K` | 8 | Beam width when `--preview` is above 0 |
| `--score-mode` | final | `final` or `sum`, see section 2 |

## 2. Misakamm with a piece preview

With `--preview N` the AI knows the current piece and the next N. It places
the current piece every legal way, keeps the best K resulting boards (merging
moves that lead to the same board), then does the same for each queued piece
in turn. It plays the first move of the best line found. Each move costs about
23 x (1 + N x K) board evaluations.

How a line of moves is scored is set by `--score-mode`: `final` (the
default) uses final-board (state) scoring, the evaluation of the last
placement in the line; `sum` uses cumulative (path) scoring, the total of the
evaluations of every placement in it. Both are the same beam search; only the
score used to rank lines differs.

### Reproduce the results

    python3 benchmark.py --games 100

This runs the plain AI (the control) and then the default preview settings
`1x8 2x8 2x8:sum 3x8`, each on seeds 0-99 of a 5-row board, with games
stopped at 5000 pieces. Every setting plays the same seeds, so they all get the
same pieces. Games run in parallel; this takes about 7 minutes on 11 cores.

Expected output (lines cleared are the same on every machine; ms/move depends
on the CPU):

    setting                         mean lines    95% CI   median vs control  ms/move  capped
    -----------------------------------------------------------------------------------------
    no preview (control)                  31.5      ±5.1     25.5       1.0x     0.30   0/100
    preview 1, width 8, final            133.0     ±23.6     90.5       4.2x     2.18   0/100
    preview 2, width 8, final            792.4    ±128.9    608.0      25.1x     4.36  11/100
    preview 2, width 8, sum              481.9     ±83.5    362.5      15.3x     4.47   1/100
    preview 3, width 8, final           1709.0    ±109.9   1998.0      54.2x     6.73  73/100

The 3x8 setting hit the cap in 73 of 100 games, so its true mean is higher.

A setting is written `PREVIEWxWIDTH[:MODE]`: `2x8` means 2 preview pieces,
beam width 8 and the default `final` scoring; `2x8:sum` uses `sum`
scoring. Other settings can be passed with `--settings`:

    python3 benchmark.py --games 100 --settings 1x8 2x2 2x32 3x8
    python3 benchmark.py --rows 6 --games 200 --settings 2x8 3x16:sum --csv results.csv

Flags for `benchmark.py`:

| Flag | Default | Meaning |
|---|---|---|
| `--ai NAME ...` | misakamm | AIs to benchmark: any of `misakamm`, `bcts`, `el-tetris`. Each runs every setting against its own control |
| `--settings S ...` | `1x8 2x8 2x8:sum 3x8` | Preview settings to run. The control (no preview) always runs first. Give no settings to run only the control |
| `--rows N` | 5 | Board height. Short boards keep games short; with a preview the AI rarely loses on tall boards |
| `--cols N` | 10 | Board width |
| `--games N` | 50 | Games per setting |
| `--first-seed N` | 0 | Games use seeds N to N + games - 1 |
| `--cap N` | 5000 | Stop a game after N pieces; 0 means no cap |
| `--workers N` | CPU count - 1 | Games played in parallel |
| `--csv FILE` | off | Also write every game (AI, setting, seed, lines, pieces, time, capped) to a CSV file |

Output columns:

| Column | Meaning |
|---|---|
| mean lines | Average lines cleared per game |
| 95% CI | 95% confidence interval of the mean |
| median | Median lines cleared |
| vs control | Mean divided by the control's mean |
| ms/move | Average time per placement |
| capped | Games that reached `--cap` before game over |

If a setting has capped games, its numbers are lower bounds. Raise `--cap` or
lower `--rows` to measure it fully. Lines cleared varies a lot from game to
game, so use 100 or more games per setting.

## 3. All three AIs with a preview

    python3 benchmark.py --ai misakamm bcts el-tetris --games 100 --settings 1x8 2x8 3x8

This runs each AI with no preview and with 1, 2 and 3 preview pieces (width 8,
`final` scoring) on the same seeds as section 2. Each AI is compared with its
own control. It takes about 22 minutes on 11 cores. Expected output:

    setting                         mean lines    95% CI   median vs control  ms/move  capped
    -----------------------------------------------------------------------------------------
    misakamm
    no preview (control)                  31.5      ±5.1     25.5       1.0x     0.36   0/100
    preview 1, width 8, final            133.0     ±23.6     90.5       4.2x     2.30   0/100
    preview 2, width 8, final            792.4    ±128.9    608.0      25.1x     4.63  11/100
    preview 3, width 8, final           1709.0    ±109.9   1998.0      54.2x     7.48  73/100
    bcts
    no preview (control)                  30.8      ±5.8     27.0       1.0x     0.86   0/100
    preview 1, width 8, final            101.6     ±21.0     65.0       3.3x     5.20   0/100
    preview 2, width 8, final            796.5    ±124.8    617.0      25.9x    10.18   9/100
    preview 3, width 8, final           1743.9     ±97.8   1998.0      56.6x    15.72  72/100
    el-tetris
    no preview (control)                  16.6      ±3.3     12.0       1.0x     0.31   0/100
    preview 1, width 8, final             26.7      ±5.3     17.5       1.6x     2.01   0/100
    preview 2, width 8, final             62.2     ±11.3     44.5       3.7x     4.05   0/100
    preview 3, width 8, final            325.2     ±71.5    173.0      19.6x     6.32   1/100

Misakamm and BCTS are not significantly different at any preview length
(paired sign tests, p = 0.07 to 0.84). Both beat El-Tetris at every preview
length (p <= 0.001; at 3x8 on 95 and 97 of 100 seeds), and El-Tetris gains
the least from a preview. BCTS takes about twice as long per move as the
other two.

## Notes

- Rules: the C++ survival rules. Pieces spawn above the board, only hard drops
  are used, and the game ends when a piece locks above the top row (checked
  before line clears). Pieces come from a port of the C++ `pcg32_k2_fast`
  generator, so a seed gives the same pieces as the C++. Results with a preview
  are an addition to the original AI; the published C++ results use no
  preview.
- Speed: the Python AI places about 3300 pieces per second without a preview,
  about 54 times slower than the C++.
- Viewer: `python3 main.py --rows 10` (needs `pip install pygame`) shows the AI
  playing. The right and left arrow keys step forward and back through its
  moves, and R starts a new game. Pieces the AI could see are outlined in
  yellow.
- Other AIs: `--ai random`, `--ai el-tetris` and `--ai bcts` select the other
  AIs. `el-tetris` and `bcts` use the same beam search and `--preview`,
  `--beam-width` and `--score-mode` options as `misakamm`.
  `python3 init_comparison.py` plays all of them without a preview on seeds
  0-4 of a 10-row board and prints lines cleared per game.
- Adding an AI: subclass `TetrisAi` in a new file under `tetris-base/ais/`
  (`ais/random_ai.py` is a minimal example), implement
  `choose(board, kind)` returning a `Placement` or `None`, and add the class to
  `AI_CLASSES` in `ais/__init__.py`. To receive upcoming pieces, set
  `self.preview` to the number of pieces required and accept
  `choose(board, kind, next_kinds)`. To take the shared `--preview`,
  `--beam-width` and `--score-mode` options, set `beam_search = True` and read
  them in `from_args`.
- Files: `main.py` (command line), `tetris_base.py` (game), `pcg.py` (piece
  generator), `viewer.py`, `benchmark.py`, `init_comparison.py`, and
  `ais/` (the AIs and shared bitboard helpers). `benchmarkbcts.py` and
  `benchmarkeltetris.py` are earlier single-AI copies of `benchmark.py`, which
  now covers every AI with `--ai`. `experiments/` holds the analysis scripts,
  `log.txt` (what each run did, what it tested and its result) and
  `results/`.

## Design choices

This section explains why the benchmark and the AI are set up the way they
are, and the problems that led to each decision.

### Board height: 5 rows

Game length grows rapidly with board height. The plain AI clears about 31
lines on a 5-row board, about 5000 on a 10-row board, and the C++ version
averages about 270 million on the standard 20-row board. A preview increases
this further: with 3 preview pieces the AI clears at least 54 times as many
lines as the plain AI on 5 rows.

Python is about 54 times slower than the C++, and with a preview each move
takes several milliseconds (7 ms for 3x8). The first benchmark used a
200,000-piece cap and did not finish in a practical time, and a 5-piece
preview setting did not finish within a 10-minute limit on 5 rows (it was later
measured on 4 rows, under "Further analysis"). On 5 rows, most games
with a short preview end on their own within seconds, so the results measure
complete games rather than games cut off by the cap. On taller boards the
stronger settings would hit the cap in nearly every game, and their results
could not be distinguished.

### Board width: 10 columns

10 is the standard Tetris width, used by the C++ program, its published
results and most Tetris AI papers. Keeping it allows the plain AI to be
checked against the C++ results (for example seed 6 on a 10-row board) and
keeps the results comparable with published ones. Only the height was reduced
to shorten games.

### Piece cap: 5000

The cap stops games that would otherwise run for a very long time. 5000
pieces is at most 2000 lines (5000 pieces x 4 cells / 10 columns), which takes
up to about 35 seconds per game with 3x8. This keeps a 100-game run to a few
minutes. Capped games are counted in the `capped` column, and their lines are
a lower bound. This is visible in the 3x8 row: 73 games hit the cap, so its
distribution is cut off near 2000 lines, and its median (1998.0) ends up above
its mean (1709.0), the opposite of the settings that rarely hit the cap.

### Number of games and seeds

Lines cleared varies widely between games, even with the same AI. In the
5-game comparison on a 10-row board (`init_comparison.py`), Misakamm cleared
between 345 and 3695 lines depending on the seed. A few games are not enough
to separate two settings, so the reference results use 100 games per setting.

Every setting plays the same seeds (0-99 by default), so every setting gets
exactly the same pieces. This removes the piece sequence as a source of
variation: a difference between two settings comes from the AI, not from one
setting receiving easier pieces. Because the piece generator is a port of the
C++ one, a seed also gives the same pieces in Python and C++, so the exact
numbers can be reproduced.

### Control row

The plain AI (no preview) always runs first, even if it is not listed. Every
other setting is reported as a multiple of it (`vs control`), which shows the
effect of the preview directly and guarantees the comparison uses the same
games and seeds.

### Output statistics

- Mean lines is the main result, as it is the standard measure in Tetris AI
  results.
- The 95% CI (1.96 x standard deviation / sqrt(games)) shows how much the mean
  could change with a different set of seeds. If two settings' intervals do
  not overlap, the difference is unlikely to be due to chance. For example,
  2x8 sum (481.9 +- 83.5) and 2x8 final (792.4 +- 128.9) do not overlap, so
  final scoring performs better at that setting. With 100 games the normal
  approximation behind the 1.96 is reasonable.
- The median is shown because the results are skewed: a few very long games
  raise the mean, so the median better represents a typical game.
- ms/move shows the cost of each setting, since a stronger setting is only
  practical if it runs in reasonable time.
- capped shows which numbers are lower bounds (see the piece cap above).

### Beam width: 8

The cost of a move grows with the beam width, about 23 x (1 + N x K) board
evaluations. In a 100-game test with 2 preview pieces and `final` scoring,
width 2 cleared 288 lines on average, width 8 cleared 792 and width 32
cleared 788, while the time per move went from 1.5 ms to 4.3 ms to 11.7 ms.
Widening the beam beyond 8 gave no further gain at about 2.7 times the cost,
so 8 is the default. (With `sum` scoring the same widths cleared 133, 482 and
521 lines.) It also matches the original C++ lookahead, which considered the
best 8 placements.

### Beam search instead of a full search

A full search tries every combination of placements for the whole queue, which
is about 23^(N+1) boards: around 12,000 for 2 preview pieces and 280,000 for 3.
That is too slow in Python. Beam search keeps only the best K boards after
each piece, so the cost grows linearly with the preview length instead of
exponentially. To check that pruning is the only difference, beam search with
an unlimited width was confirmed to choose the same move as the full search on
4,677 positions.

### Merging duplicate boards

Different lines of play can reach exactly the same board: two pieces of the
same kind placed in either order, different placements whose line clears
leave the same board, or different placements that happen to fill the same
cells. Without merging, those copies take up several slots in the beam. The
search therefore merges lines that reach the same board and keeps the best
one, so every slot holds a different position. The merge only compares
boards, so it costs almost nothing (the time per move below is the same with
and without it).

Duplicates are less common than might be expected. Measured over 40 games
each at 1x8 and 2x8 (5-row board), about 1.5-2% of the lines generated after
the first piece duplicate another line's board. They gather near the top of
the ranking, since good lines tend to reach the same good board: 15-18% of
search steps have a duplicate among the best 8 lines, and an unmerged beam of
8 holds about 7.6 different boards on average.

Effect on lines cleared, on the same 100 seeds (5-row board, cap 5000,
`final` scoring):

| Setting | Merged | Not merged | Seeds where merging clears more / fewer lines | Sign test p |
|---|---|---|---|---|
| 1x8 | 133.0 | 131.6 | 1 / 1 | - |
| 2x2 | 288.1 | 209.6 | 57 / 30 | 0.005 |
| 2x8 | 792.4 | 830.8 | 39 / 53 | 0.17 |
| 3x8 | 1709.0 | 1739.2 | 34 / 38 | 0.72 |

Merging matters only when the beam is narrow. With width 2, a single
duplicate takes half of the beam, and merging raises the mean by 37%, a
difference well outside chance. With width 8, a duplicate costs one slot in
eight, and the results with and without merging are not significantly
different (2x8 is slightly lower with merging, but within the confidence
intervals). With a preview of 1 the beam is only used for the last piece, so
merging changes almost nothing. Merging is kept because it gives a large
gain at narrow widths at no measurable cost at the default width. Widths up to
32 are tested under "Further analysis" below.

### Multi Piece Evaluation Modes (Sum and Final)

Beam search scores each placement with the AI's own evaluation function: for
Misakamm, `MisakammAi._evaluate` in `ais/misakamm.py`, the same one the C++ AI
uses to choose its move (BCTS and El-Tetris use theirs). The tables in this
section are for Misakamm. With a preview, a line of play contains several
placements, so the search also needs a rule for combining their evaluations
into one score for the line. That rule decides how the extra information is
used, which is why both options are kept and compared.

With `--preview 2`, a line of play is three moves: the current piece and the
two previewed pieces. If e1, e2 and e3 are the evaluations of those three
moves, the two modes score the line as:

    sum:    e1 + e2 + e3
    final:  e3

and the line with the highest score is chosen. With `sum`, the landing height
and line clears of every move count and every intermediate board is judged.
With `final`, earlier moves count only through the board they lead to.

Both modes are the same beam search: every board in the beam is expanded with
every placement of the next piece, duplicate boards are merged, and the best K
lines are kept. The only difference is the score used to rank lines, which
corresponds to two standard ways of scoring a search:

- `sum` is cumulative (path) scoring. A line's score depends on the whole
  route it took, as in beam search for language models, which ranks
  sentences by their total log-probability.
- `final` is final-board (state) scoring. A line's score depends on where it
  ends up (apart from the last move's landing height and line clears), as in
  game-playing search such as chess engines, which evaluate the end position.

In both modes the placements depend on each other, since each piece is placed
on the board left by the previous one; the modes differ only in whether the
boards passed through along the way affect the score.

Which rule works better was not clear in advance, so both were benchmarked
on the same 100 seeds (5-row board, cap 5000):

| Setting | sum: mean lines | final: mean lines | Seeds where final clears more / fewer lines |
|---|---|---|---|
| 1x8 | 101.3 | 133.0 | 58 / 41 |
| 2x2 | 132.9 | 288.1 | 71 / 28 |
| 2x8 | 481.9 | 792.4 | 64 / 34 |
| 2x32 | 520.5 | 787.9 | 58 / 40 |
| 3x8 | 1406.3 | 1709.0 | 55 / 31 |

`final` clears more lines at every setting, and at the same cost per move, so
it is the default. Its lead is understated at the stronger settings, because
it hits the cap more often (73 of 100 games at 3x8, against 46 for `sum`).

`sum` was a plausible choice. Under these rules the number of lines cleared
is set by how long the AI survives: every piece adds 4 cells and every cleared
line removes 10, so lines cleared is approximately (4 x pieces - cells left on
the board) / 10, or 0.4 lines per piece for every setting. A stronger setting
does not clear lines faster; it survives more pieces by staying away from the
top of the board. `sum` counts the landing height of every move in the line,
so it prefers lines that stay low the whole way, and it does keep the lowest
stacks. Average column height after each move, measured separately on the
same 5-row board (seeds 0-99, cap 2000):

| Setting | Mean lines | Average column height | Moves with the stack 1 row from the top |
|---|---|---|---|
| control | 31.5 | 1.99 | 58.3% |
| 1x8 sum | 101.3 | 1.88 | 56.1% |
| 2x8 sum | 406.9 | 1.71 | 50.9% |
| 2x8 final | 517.3 | 1.85 | 55.7% |
| 3x8 sum | 684.3 | 1.65 | 49.2% |
| 3x8 final | 752.5 | 1.77 | 53.0% |

(Mean lines are lower than in the table above because of the lower cap.)

Yet `final` survives longer while keeping slightly higher stacks. The likely
reason is that the queue is known. Every move in a line of play is certain:
the pieces are known, and lines that top out along the way are already
discarded by the search, so an intermediate board is a guaranteed, temporary
step rather than a risk. The only board that carries into the unknown future
is the one left once the queue is used up, and `final` scores exactly that
board. `sum` also scores the intermediate boards, so it penalises temporary
positions that the preview makes harmless, such as a gap or well that a known
upcoming piece will fill, or a higher placement that lets the next piece
clear a line. Setups like these are what a preview makes possible, and `sum`
discourages them. The plain AI's evaluation is cautious about such boards
because it cannot see the next piece; for the moves the preview covers, that
caution is no longer needed.

### When every line loses

Near the top of the board, every line in the beam can end in a game over on
some queued piece. The AI then plays the best line from one piece earlier
instead of giving up. The first version of this mixed the score of one line
with the tie-break of another and could pick a move that did not match either.
After the fix, it was tested against the full search on 4,160 nearly full
boards (1,704 of them where every line loses), with no differences.

### Preview off by default

`--preview` defaults to 0 so the default AI plays exactly like the C++
program. That gives a verified baseline: before measuring anything new, the
plain AI can be checked move for move against the C++ (340 full games were
compared). The preview is not part of the original AI, so it is opt-in and
reported separately from the C++ results.

### Workers: CPU count - 1

Games are independent, so they run in parallel, one per process, which cuts
the time of a run by about the number of cores. One core is left free so the
computer stays usable during a long run. Results do not depend on the number of
workers; only the run time does.

## Further analysis

These experiments extend the design choices above. Each is logged in
`experiments/log.txt` (entries 20-21 and 26-32) with its script and full
output in `experiments/results/`. All use final scoring and seeds starting
at 0.

### Plain Misakamm and BCTS across board heights

Without a preview, Misakamm and BCTS are tied on 5 rows, but Misakamm's lead
grows with the board height (100 paired games per height, no cap;
`python3 experiments/bcts_vs_misakamm_heights.py 100 5 6 7 8 9`, about 2
minutes, and `python3 experiments/bcts_vs_misakamm_uncapped.py 50` for 10
rows):

| Rows | BCTS | Misakamm | Mean ratio | Misakamm better on | Sign test p |
|---|---|---|---|---|---|
| 5 | 30.8 | 31.5 | 1.02x | 51/100 | 0.84 |
| 6 | 72.5 | 96.7 | 1.33x | 55/100 | 0.27 |
| 7 | 213.9 | 257.9 | 1.21x | 55/100 | 0.37 |
| 8 | 551.8 | 852.4 | 1.54x | 59/100 | 0.07 |
| 9 | 1339.6 | 2235.3 | 1.67x | 65/100 | 0.004 |
| 10 (50 games) | 3911.6 | 7292.4 | 1.86x | 30/50 | 0.20 |

This matches the published 20-row records, where Misakamm (about 270 million
lines) is far ahead of BCTS (about 35 million). On short boards both AIs lose
to the same runs of bad pieces, which hides the difference between two strong
evaluation functions, so the 5-row benchmark measures what the preview adds
rather than ranking the base AIs.

### Merging duplicate boards at larger beam widths

Misakamm at preview 2, 100 games on a 5-row board, cap 5000, run with and
without merging (`python3 experiments/merge_by_width.py 100 2 4 8 16 32`,
about 18 minutes). The last column is the share of the K lines kept by the
unmerged search, before the last piece, that are different boards. (The
earlier "7.6 of 8" figure was measured differently: on the best 8 of the
merged search's candidate lines, at every step after the first piece.)

| Width | Merged | Not merged | Seeds where merging clears more / fewer lines | Sign test p | Different boards kept without merging |
|---|---|---|---|---|---|
| 2 | 288.1 | 209.6 | 57 / 30 | 0.005 | 98.8% |
| 4 | 701.6 | 759.1 | 50 / 49 | 1.00 | 98.2% |
| 8 | 792.4 | 830.8 | 39 / 53 | 0.18 | 97.9% |
| 16 | 646.9 | 720.6 | 31 / 41 | 0.29 | 97.4% |
| 32 | 787.9 | 807.5 | 32 / 38 | 0.55 | 96.9% |

Merging helps only at width 2. From width 4 upwards the difference is not
significant at any width; the unmerged search is slightly ahead on the means,
but within chance. Duplicates make up only 1-3% of the kept lines at every
width, so the cost of a duplicate depends on the beam size: at width 2 one
duplicate removes half the beam, while at width 32 it removes one line in 32.

To find out whether merging really makes the search worse at larger widths, a
second test compares single decisions instead of whole games
(`python3 experiments/merge_disagreements.py 33 220 2 8 32`, about 13
minutes). Misakamm plays 33 games, and at every move the unmerged search is
also asked for its choice on the same board and queue. At positions where the
two choose differently, both moves are played from a copy of the game, and
both copies continue with the same AI until game over, with the same pieces:

| Width | Moves where merging changes the choice | Merged move leads to more / fewer lines | Sign test p | Same, where merging found a higher-scoring line | Same, where the scores were equal |
|---|---|---|---|---|---|
| 2 | 1.66% | 65 / 47 | 0.11 | 46 / 27 (p = 0.03) | 19 / 19 |
| 8 | 0.60% | 71 / 70 | 1.00 | 46 / 48 | 25 / 22 |
| 32 | 0.12% | 21 / 18 | 0.75 | 17 / 16 | 4 / 2 |

(220 positions sampled at widths 2 and 8, all 50 found at width 32.)

Three possible causes of a harmful merge were checked:

- The first move kept for a merged board. When two first moves lead to the
  same board, the merge keeps the one that wins the tie-break and ignores the
  board each first move leaves behind, even though the AI searches again next
  turn with a new piece visible. About 40% of the disagreements are of this
  kind (equal best scores, different first move), but these moves do as well
  as the unmerged ones at every width, so this rule does no harm.
- Lines that score higher but play worse. The slots freed by merging can
  hold lines that the evaluation rates higher. At width 2 these lines really
  are better (46 / 27). From width 8 they are no better or worse in play,
  and the size of the score gain does not predict the result (rank
  correlation -0.02 at width 8). Past this point the evaluation cannot tell
  apart the extra lines found, which matches the flat results for widths
  8-32 in the table above. The extra lines do not hurt, though.
- Noise. Merging changes 1 move in 170 at width 8 and 1 in 830 at width 32,
  and a single different move largely decides the rest of the game: from the
  same position, the two continuations' lines have a rank correlation of
  only 0.34 at width 8 and 0.15 at width 32. Each game in the comparison above
  is therefore close to an independent draw. For 2x8, the difference between
  two 100-game means of independent games has a standard deviation of about
  93 lines, larger than every gap in the table above (20-74 lines), and the
  unmerged search coming out ahead at all four widths happens by chance with
  probability 0.125.

The slightly higher unmerged results are therefore noise. Merging never makes
the decisions worse, it clearly helps at width 2, and it costs no time, so it
is kept.

### Board height

Every AI at previews 0, 1 and 2 (width 8), cap 20000, on 4- and 5-row boards
(100 games) and 6-row boards (50 games, to keep the run near half an hour):

    python3 experiments/height_sweep.py --rows 4 5 --games 100
    python3 experiments/height_sweep.py --rows 6 --games 50

Mean lines cleared (games that reached the cap in brackets):

| AI | Rows | No preview | Preview 1 | Preview 2 | Preview 2 vs no preview |
|---|---|---|---|---|---|
| Misakamm | 4 | 8.6 | 20.4 | 65.7 | 7.6x |
| Misakamm | 5 | 31.5 | 133.0 | 858.4 | 27x |
| Misakamm | 6 | 107.4 | 1073.6 | >= 5266.6 (19/50) | >= 49x |
| BCTS | 4 | 7.8 | 20.4 | 81.7 | 10x |
| BCTS | 5 | 30.8 | 101.6 | 916.2 | 30x |
| BCTS | 6 | 76.5 | 567.4 | >= 4772.1 (17/50) | >= 62x |
| El-Tetris | 4 | 3.7 | 4.3 | 10.8 | 2.9x |
| El-Tetris | 5 | 16.6 | 26.7 | 62.2 | 3.7x |
| El-Tetris | 6 | 40.3 | 135.5 | 580.5 | 14x |

Each extra row multiplies lines cleared several times for every AI and
setting, and the gain from a preview grows with the board height. The 5-row
results therefore understate what a preview is worth on taller boards rather
than overstate it. The ordering of the AIs is the same at every height:
Misakamm and BCTS are close, and El-Tetris is well behind and gains least from
a preview. The gain is smallest on 4 rows, where there is the least room to
use the extra information.

### Stack height

The same runs record the column heights after every placement. On 5 rows:

| AI | Preview | Mean lines | Average max column height | Average column height | Moves with the stack 1 row from the top |
|---|---|---|---|---|---|
| Misakamm | 0 | 31.5 | 3.67 | 1.99 | 58% |
| Misakamm | 1 | 133.0 | 3.71 | 1.95 | 60% |
| Misakamm | 2 | 858.4 | 3.61 | 1.85 | 56% |
| BCTS | 0 | 30.8 | 3.58 | 1.97 | 56% |
| BCTS | 1 | 101.6 | 3.72 | 1.96 | 60% |
| BCTS | 2 | 916.2 | 3.63 | 1.85 | 56% |
| El-Tetris | 0 | 16.6 | 3.54 | 1.97 | 50% |
| El-Tetris | 1 | 26.7 | 3.72 | 2.11 | 57% |
| El-Tetris | 2 | 62.2 | 3.77 | 2.11 | 59% |

A low stack does not emerge as the main strategy. With a preview of 2,
Misakamm and BCTS clear about 30 times as many lines, yet their highest column
is just as high and the stack is near the top just as often; only the average
column height falls, by 5-10%. El-Tetris's stack gets higher with a preview
while it clears more lines. The same holds on 4 and 6 rows. This refines the
stack-height table under "Multi Piece Evaluation Modes": `sum` scoring does
keep lower stacks, but `final` scoring is stronger without them.

Since lines cleared is fixed at about 0.4 per piece, a stronger AI is one that
survives longer, and these results show that it survives without spending much
less time near the top. A likely explanation is that the preview makes high
positions safer: when the next pieces are known, the search only enters a high
position if the queued pieces can be placed after it without topping out, so
the stack can run high with less risk of being caught by an unknown piece.
The plain AIs face the same heights but cannot tell which high positions they
can recover from.

Across board heights, the highest column grows by only about half a row per
extra row of board (average max height / rows: about 0.78 on 4 rows, 0.73 on
5, 0.69 on 6), so a taller board mainly adds headroom above the stack, which
is why games get so much longer.

### Longer games: a 20000-piece cap

The 5000-piece cap was reached in about 72% of 3x8 games, so 3x8 was rerun
for Misakamm and BCTS with a 20000-piece cap (at most 8000 lines), on 50 games
to keep the run to about 20 minutes:

    python3 benchmark.py --ai misakamm bcts --games 50 --cap 20000 --settings 3x8

| Setting (5 rows, seeds 0-49) | Cap 5000 | Cap 20000 |
|---|---|---|
| Misakamm 3x8 | 1668.7 (37/50 capped) | >= 4220.6 (14/50 capped) |
| BCTS 3x8 | 1767.5 (35/50 capped) | >= 4401.2 (11/50 capped) |
| Misakamm 2x8 (seeds 0-99) | 792.4 (11/100 capped) | 858.4 (0/100 capped) |
| BCTS 2x8 (seeds 0-99) | 796.5 (9/100 capped) | 916.2 (0/100 capped) |

The 5000 cap hid more than half of the 3x8 result, and some 3x8 games still
reach the 20000 cap, so its true mean is higher again. At the higher cap,
Misakamm and BCTS are still not significantly different at 3x8 (Misakamm
clears more on 22 seeds and fewer on 26, p = 0.67). The 2x8 results are now
complete: no 5-row game at preview 2 reaches 20000 pieces.

### Preview length: 4 and 5 pieces

Previews of 4 and 5 pieces make games so long that a 5-row board caps nearly
every game, so these runs use a 4-row board. A first run at beam width 4 (50
games, cap 5000, about 1.5 minutes):

    python3 benchmark.py --rows 4 --games 50 --cap 5000 --settings 1x4 2x4 3x4 4x4 5x4

A second run at width 8 (200 games, cap 10000). It was split in two because
the 5x8 games need about 14 minutes on their own; both parts play the same
seeds, and their controls are identical:

    python3 benchmark.py --rows 4 --games 200 --cap 10000 --settings 3x8 4x8
    python3 benchmark.py --rows 4 --games 200 --cap 10000 --settings 5x8

Previews 1 and 2 at width 8 come from the board height runs above (100
games, cap 20000). Mean lines cleared on 4 rows (capped games in brackets):

| Preview | Width 4 (50 games) | Gain over one fewer | Width 8 | Gain over one fewer | ms/move at width 8 |
|---|---|---|---|---|---|
| 0 | 9.1 | - | 8.4 | - | 0.30 |
| 1 | 21.3 | 2.3x | 20.4 | 2.4x | - |
| 2 | 56.3 | 2.6x | 65.7 | 3.2x | - |
| 3 | 169.5 | 3.0x | 228.8 | 3.5x | 4.91 |
| 4 | 475.7 (1/50) | 2.8x | 902.0 (4/200) | 3.9x | 6.87 |
| 5 | >= 700.1 (5/50) | >= 1.5x | >= 1987.2 (39/200) | >= 2.2x | 9.05 |

At width 4 the step from 4 to 5 preview pieces is small and not significant
per seed (5 beats 4 on 28 seeds and loses on 22, p = 0.48), while every
earlier step is (p < 0.01). At width 8 the same step is at least 2.2x, and
the 95% confidence intervals of 4x8 (up to 1029.9) and 5x8 (from 1795.1) do
not overlap. The flattening at width 4 therefore comes from the narrow beam:
with only 4 lines kept after each piece, a 5-piece search loses most of what
it could gain. A deeper preview needs a wide enough beam to pay off.

### An approximation for preview length

With a wide enough beam, each extra preview piece multiplies lines cleared by
a roughly constant factor, so lines cleared grow exponentially with the
preview length N. A least-squares fit of log(lines) against N for Misakamm at
width 8 gives:

| Board | Fitted on | Fit | Predicted next preview | Measured |
|---|---|---|---|---|
| 4 rows | previews 0-4 | lines ~ 7.1 x 3.24^N | 2551 at N = 5 | >= 1987.2 (39/200 capped) |
| 5 rows | previews 0-2 | lines ~ 29.3 x 5.22^N | 4175 at N = 3 | >= 4220.6 (14/50 capped) |

Both fits predict a setting they were not fitted on, within what the capped
results allow. A likely explanation for the exponential form: since lines
cleared is fixed at about 0.4 per piece, lines measure how many pieces the AI
survives, and a game ends when the AI meets a run of pieces it cannot place
safely. If each extra known piece reduces the chance of that, per piece, by a
roughly constant factor, game length grows by that factor for every preview
piece.

The approximation has limits:

- The factor is smaller for the first preview piece and grows a little with
  each step (2.4x, 3.2x, 3.5x, 3.9x on 4 rows), since with one preview piece
  the beam only acts on the last piece.
- The factor grows with board height (about 3.2x on 4 rows, 5.2x on 5 rows),
  so it cannot be carried over to taller boards. For comparison, an extra row
  of board without a preview multiplies lines by about 3.5x (8.6, 31.5 and
  107.4 lines on 4, 5 and 6 rows): one preview piece is worth about one row on
  4 rows and more than one on 5.
- It holds only while the beam is wide enough, as the width 4 results show.
- The fits rest on 3-5 points each, the highest preview at each height is a
  lower bound, and each point is a single run of 100-200 games.

The cost of a preview grows linearly instead: at width 8, each extra preview
piece adds about 2 ms per move.
