
"""Benchmark the El-Tetris AI's beam search against the plain AI.

Every setting plays the same seeds, so all settings see the same pieces.
The control (no preview) runs the original El-Tetris algorithm first,
and each setting is compared with it.

    python3 benchmarkeltetris.py
    python3 benchmarkeltetris.py --rows 6 --games 200 --settings 1x8 2x8 2x8:sum 3x16
    python3 benchmarkeltetris.py --csv results.csv

A setting is PREVIEWxWIDTH[:MODE], e.g. 2x8 (2 preview pieces,
beam width 8, default final scoring) or 3x16:sum.
"""

import argparse
import csv
import math
import os
import statistics
import time
from multiprocessing import Pool

from ais import play_turn
from ais.eltetris import (
    DEFAULT_SCORE_MODE,
    SCORE_MODES,
    ElTetrisAi,
)
from tetris_base import MAX_ROWS, Tetris


CONTROL = (0, 1, DEFAULT_SCORE_MODE)
DEFAULT_SETTINGS = ["1x8", "2x8", "2x8:sum", "3x8"]


def parse_setting(text):
    """'2x8' -> (2, 8, 'final'); '3x16:sum' -> (3, 16, 'sum')."""
    try:
        spec, _, mode = text.partition(":")
        preview, width = (int(v) for v in spec.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"bad setting {text!r}; expected e.g. 2x8 or 3x16:sum"
        )

    mode = mode or DEFAULT_SCORE_MODE

    if preview < 1 or width < 1 or mode not in SCORE_MODES:
        raise argparse.ArgumentTypeError(
            f"bad setting {text!r}: preview and width must be >= 1, "
            f"mode one of {SCORE_MODES}"
        )

    return preview, width, mode


def label(setting):
    preview, width, mode = setting
    return (
        "no preview (control)"
        if preview == 0
        else f"preview {preview}, width {width}, {mode}"
    )


def play_game(job):
    """Play one game to game over or the piece cap; runs in a worker process."""
    (preview, width, mode), rows, cols, seed, cap = job

    game = Tetris(rows, cols, seed)
    ai = ElTetrisAi(
        preview=preview,
        beam_width=width,
        score_mode=mode,
    )

    start = time.perf_counter()

    while not game.game_over and (
        cap <= 0 or game.pieces_placed < cap
    ):
        play_turn(game, ai)

    return {
        "preview": preview,
        "width": width,
        "mode": mode,
        "seed": seed,
        "lines": game.lines_cleared,
        "pieces": game.pieces_placed,
        "seconds": time.perf_counter() - start,
        "capped": not game.game_over,
    }


def summarize(results, control_mean):
    lines = [r["lines"] for r in results]
    mean = statistics.mean(lines)

    # 95% confidence interval of the mean (normal approximation).
    half_ci = (
        1.96 * statistics.stdev(lines) / math.sqrt(len(lines))
        if len(lines) > 1
        else 0.0
    )

    pieces = sum(r["pieces"] for r in results)

    return {
        "mean": mean,
        "ci": half_ci,
        "median": statistics.median(lines),
        "ratio": mean / control_mean if control_mean else float("nan"),
        "ms_per_move": (
            1000 * sum(r["seconds"] for r in results) / max(pieces, 1)
        ),
        "capped": sum(r["capped"] for r in results),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark El-Tetris beam-search settings against the plain AI.",
        epilog=(
            "Lines-cleared results vary a lot between games (roughly exponentially), "
            "so use 100+ games per setting; ~300 gives about +-10% on the mean."
        ),
    )

    parser.add_argument(
        "--settings",
        nargs="*",
        type=parse_setting,
        default=[parse_setting(s) for s in DEFAULT_SETTINGS],
        metavar="PxW[:MODE]",
        help=(
            f"beam settings to test (default: {' '.join(DEFAULT_SETTINGS)}); "
            "give none to run only the control"
        ),
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=5,
        help="board rows (default 5; short boards end games quickly)",
    )

    parser.add_argument(
        "--cols",
        type=int,
        default=10,
        help="board cols (default 10)",
    )

    parser.add_argument(
        "--games",
        type=int,
        default=50,
        help="games per setting (default 50)",
    )

    parser.add_argument(
        "--first-seed",
        type=int,
        default=0,
        help="games use seeds first-seed .. first-seed+games-1 (default 0)",
    )

    parser.add_argument(
        "--cap",
        type=int,
        default=5000,
        help="stop a game after this many pieces; 0 = no cap (default 5000)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 1),
        help="parallel processes (default: CPU count - 1)",
    )

    parser.add_argument(
        "--csv",
        help="also write every game's result to this CSV file",
    )

    args = parser.parse_args()

    if not 1 <= args.rows <= MAX_ROWS:
        parser.error(f"--rows must be in [1, {MAX_ROWS}]")

    if args.games < 1:
        parser.error("--games must be >= 1")

    if args.workers < 1:
        parser.error("--workers must be >= 1")

    if args.cap < 0:
        parser.error("--cap must be >= 0")

    settings = [
        CONTROL,
        *[s for s in dict.fromkeys(args.settings) if s != CONTROL],
    ]

    seeds = range(args.first_seed, args.first_seed + args.games)

    print(
        f"El-Tetris | Board {args.rows}x{args.cols}, "
        f"{args.games} games per setting "
        f"(seeds {seeds.start}-{seeds.stop - 1}), "
        f"{f'cap {args.cap} pieces' if args.cap else 'no cap'}, "
        f"{args.workers} workers\n"
    )

    header = (
        f"{'setting':<30} {'mean lines':>11} {'95% CI':>9} "
        f"{'median':>8} {'vs control':>10} {'ms/move':>8} {'capped':>7}"
    )

    print(header)
    print("-" * len(header))

    all_results = []
    control_mean = None

    with Pool(args.workers) as pool:
        for setting in settings:
            jobs = [
                (setting, args.rows, args.cols, seed, args.cap)
                for seed in seeds
            ]

            results = pool.map(play_game, jobs, chunksize=1)
            all_results.extend(results)

            if control_mean is None:
                control_mean = statistics.mean(
                    r["lines"] for r in results
                )

            s = summarize(results, control_mean)

            print(
                f"{label(setting):<30} "
                f"{s['mean']:>11.1f} "
                f"{'±' + format(s['ci'], '.1f'):>9} "
                f"{s['median']:>8.1f} "
                f"{s['ratio']:>9.1f}x "
                f"{s['ms_per_move']:>8.2f} "
                f"{s['capped']:>3}/{len(results)}",
                flush=True,
            )

    if any(r["capped"] for r in all_results):
        print(
            "\nCapped games stopped early, so those settings' lines are lower "
            "bounds; raise --cap or lower --rows to measure them fully."
        )

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(all_results[0]),
            )
            writer.writeheader()
            writer.writerows(all_results)

        print(f"\nWrote {len(all_results)} games to {args.csv}")


if __name__ == "__main__":
    main()
