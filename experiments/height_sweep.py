"""Lines cleared and stack height per AI, board height and preview length.

Every combination plays the same seeds. After every placement the column
heights are recorded, so each game also reports its average maximum column
height, average column height, and the share of moves with the stack within one
row of the top. This tests how results scale with board height and whether
stronger settings keep the stack lower.

    python3 experiments/height_sweep.py --ai misakamm bcts el-tetris --rows 4 5 6 \\
        --previews 0 1 2 --games 100 --cap 20000 --csv results.csv
"""
import argparse, csv, math, os, statistics, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import AIS, play_turn
from ais.bitboard import board_to_bits, col_heights


def play(job):
    name, rows, preview, width, seed, cap = job
    g = Tetris(rows, 10, seed)
    ai = AIS[name](preview=preview, beam_width=width, score_mode="final")
    maxh = avgh = near_top = moves = 0
    t = time.perf_counter()
    while not g.game_over and g.pieces_placed < cap:
        play_turn(g, ai)
        if g.game_over:
            break
        h = col_heights(board_to_bits(g.board), 10)
        maxh += max(h)
        avgh += sum(h) / 10
        near_top += max(h) >= rows - 1
        moves += 1
    moves = max(moves, 1)
    return {"ai": name, "rows": rows, "preview": preview, "width": width, "seed": seed,
            "lines": g.lines_cleared, "pieces": g.pieces_placed, "capped": not g.game_over,
            "seconds": time.perf_counter() - t, "max_height": maxh / moves,
            "mean_height": avgh / moves, "near_top": near_top / moves}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai", nargs="+", default=["misakamm", "bcts", "el-tetris"])
    parser.add_argument("--rows", nargs="+", type=int, default=[4, 5, 6])
    parser.add_argument("--previews", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--cap", type=int, default=20000)
    parser.add_argument("--csv")
    args = parser.parse_args()

    print(f"{args.games} games per combination (seeds 0-{args.games - 1}), width {args.width}, "
          f"final scoring, cap {args.cap}")
    print(f"{'ai':<10}{'rows':>5}{'preview':>8}{'mean lines':>11}{'95% CI':>9}{'median':>8}"
          f"{'max h':>7}{'mean h':>7}{'max h/rows':>11}{'near top':>9}{'ms/move':>8}{'capped':>8}")
    results = []
    with Pool(11) as pool:
        for name in args.ai:
            for rows in args.rows:
                for preview in args.previews:
                    jobs = [(name, rows, preview, args.width, s, args.cap) for s in range(args.games)]
                    res = pool.map(play, jobs, chunksize=1)
                    results.extend(res)
                    lines = [r["lines"] for r in res]
                    ci = 1.96 * statistics.stdev(lines) / math.sqrt(len(lines))
                    mh = statistics.mean(r["max_height"] for r in res)
                    ms = 1000 * sum(r["seconds"] for r in res) / max(sum(r["pieces"] for r in res), 1)
                    print(f"{name:<10}{rows:>5}{preview:>8}{statistics.mean(lines):>11.1f}{'±%.1f' % ci:>9}"
                          f"{statistics.median(lines):>8.1f}{mh:>7.2f}"
                          f"{statistics.mean(r['mean_height'] for r in res):>7.2f}{mh / rows:>11.2f}"
                          f"{100 * statistics.mean(r['near_top'] for r in res):>8.1f}%{ms:>8.2f}"
                          f"{sum(r['capped'] for r in res):>4}/{len(res)}", flush=True)
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0]))
            writer.writeheader()
            writer.writerows(results)
