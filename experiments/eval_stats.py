"""Statistics of Misakamm's evaluation over plain (no preview) games."""
import statistics, sys
from multiprocessing import Pool
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais import play_turn
from ais import misakamm as M
from ais.bitboard import board_to_bits, col_heights, legal_placements

TERMS = ["landing height", "rows cleared", "row transitions", "col transitions", "holes",
         "edge holes x0", "x1 holes", "x2 holes", "hole depth", "wells", "shape adaptability"]

def terms(ai, bits, heights, cleared, lh4, tables):
    w = ai.weights
    rt, ct, holes, x0, x1, x2, hd = M._line_and_hole_metrics(bits, heights, len(heights))
    return [15 * w.landing_height * lh4, 60 * w.rows_cleared * cleared,
            -60 * M.ROW_TRANSITIONS_WEIGHT * rt, -60 * w.vertical * ct, -60 * w.hole * holes,
            -90 * w.x1_hole * x0, -60 * w.x1_hole * x1, -60 * w.x2_hole * x2,
            -60 * w.hole_depth * hd, -6 * M._well_depth(heights, len(bits), len(heights), tables),
            10 * w.shape_adaptability * M._shape_adaptability(heights)]

def play(job):
    rows, seed, cap = job
    g, ai = Tetris(rows, 10, seed), M.MisakammAi()
    tables = ai._well_tables_for_rows(rows)
    chosen, every, spread, breakdown = [], [], [], []
    while not g.game_over and g.pieces_placed < cap:
        bits = board_to_bits(g.board)
        cands = []
        for o, x, y, sim, cl in legal_placements(bits, col_heights(bits, 10), g.kind):
            t = terms(ai, sim, col_heights(sim, 10), cl, 4 * y + o.landing_base, tables)
            cands.append((sum(t), t))
        if not cands:
            break
        cands.sort(key=lambda c: -c[0])
        chosen.append(cands[0][0]); breakdown.append(cands[0][1])
        every += [c[0] for c in cands]; spread.append(cands[0][0] - cands[-1][0])
        play_turn(g, ai)
    return chosen, every, spread, breakdown

def pct(v, p):
    v = sorted(v); return v[int(p * (len(v) - 1))]

if __name__ == "__main__":
    with Pool(11) as pool:
        for rows, games, cap in [(5, 100, 10**9), (10, 20, 2000), (20, 10, 2000)]:
            res = pool.map(play, [(rows, s, cap) for s in range(games)], chunksize=1)
            chosen = [v for r in res for v in r[0]]; every = [v for r in res for v in r[1]]
            spread = [v for r in res for v in r[2]]; bd = [t for r in res for t in r[3]]
            print(f"\n== rows={rows}: {games} games, {len(chosen)} moves, {len(every)} candidate placements")
            for name, v in [("chosen move", chosen), ("all candidates", every), ("best - worst per move", spread)]:
                print(f"  {name:<22} min {min(v):>9}  p5 {pct(v,.05):>9}  median {statistics.median(v):>9.0f}"
                      f"  mean {statistics.mean(v):>9.0f}  p95 {pct(v,.95):>9}  max {max(v):>9}  sd {statistics.pstdev(v):>8.0f}")
            print("  mean contribution of each term to the chosen move:")
            for i, name in enumerate(TERMS):
                print(f"    {name:<20} {statistics.mean(t[i] for t in bd):>9.0f}")
