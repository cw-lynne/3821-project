"""Why merging duplicate boards might hurt at larger widths: a decision-level test.

Whole-game comparisons are noisy: once two searches pick one different move,
the rest of the game differs, so a seed's result is close to a fresh draw.
This test compares single decisions instead.

Phase 1: play Misakamm (merged, preview 2, final scoring) and, at every move,
also ask the unmerged search for its choice on the same board and queue,
without playing it. Record every position where the two choices differ, with
each search's best line score.

Phase 2: from a random sample of those positions, play the merged choice and
the unmerged choice, then continue both games with the same merged AI until
game over (or the rollout cap). Same pieces in both, so only that one decision
differs.

    python3 experiments/merge_disagreements.py [games] [rollouts] [width ...]
"""
import copy, csv, math, os, random, statistics, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tetris-base"))
from tetris_base import Tetris
from ais.misakamm import MisakammAi

ROWS, PREVIEW, GAME_CAP, ROLLOUT_CAP = 5, 2, 2000, 5000
RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


class Recording:
    """Remembers the score of the best line from the last search."""

    def _select(self, paths, last):
        ranked = self._rank(paths, last)
        if last:
            self.best_score = ranked[0].score if ranked else None
        return ranked

    def choose(self, board, kind, next_kinds=()):
        self.best_score = None  # Stays None if the search fell back (every line lost).
        return super().choose(board, kind, next_kinds)


class MergedAi(Recording, MisakammAi):
    def _rank(self, paths, last):
        return MisakammAi._select(self, paths, last)


class NoMergeAi(Recording, MisakammAi):
    def _rank(self, paths, last):
        return sorted(paths, key=lambda p: (-p.score, p.tie))[:self.beam_width]


def make(cls, width):
    return cls(preview=PREVIEW, beam_width=width, score_mode="final")


def place(game, placement):
    if placement is None:
        game.game_over = True
    else:
        game.place(placement.piece, placement.x)


def find_disagreements(job):
    """Phase 1 for one seed: returns (moves, list of disagreement records)."""
    width, seed = job
    game, ai, shadow = Tetris(ROWS, 10, seed), make(MergedAi, width), make(NoMergeAi, width)
    found = []
    while not game.game_over and game.pieces_placed < GAME_CAP:
        queue = game.upcoming(PREVIEW)
        m = ai.choose(game.board, game.kind, queue)
        n = shadow.choose(game.board, game.kind, queue)
        if m is not None and n is not None and (m.piece, m.x) != (n.piece, n.x):
            found.append({"seed": seed, "piece": game.pieces_placed, "game": copy.deepcopy(game),
                          "merged": m, "unmerged": n,
                          "merged_score": ai.best_score, "unmerged_score": shadow.best_score})
        place(game, m)
    return game.pieces_placed, found


def rollout(job):
    """Phase 2: play one decision, then continue with the merged AI."""
    width, game, placement = job
    ai = make(MergedAi, width)
    start_lines, start_pieces = game.lines_cleared, game.pieces_placed
    place(game, placement)
    while not game.game_over and game.pieces_placed - start_pieces < ROLLOUT_CAP:
        place(game, ai.choose(game.board, game.kind, game.upcoming(PREVIEW)))
    return game.lines_cleared - start_lines, not game.game_over


def sign_test(wins, losses):
    """Two-sided sign test p-value (ties dropped)."""
    n = wins + losses
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    return statistics.correlation(ranks(xs), ranks(ys))


def compare(label, rows):
    if not rows:
        print(f"    {label}: none")
        return
    m = [r["merged_lines"] for r in rows]
    n = [r["unmerged_lines"] for r in rows]
    wins = sum(a > b for a, b in zip(m, n))
    losses = sum(a < b for a, b in zip(m, n))
    print(f"    {label} (n={len(rows)}): mean lines after merged move {statistics.mean(m):.1f}, "
          f"after unmerged move {statistics.mean(n):.1f}; merged better {wins}, worse {losses}, "
          f"same {len(rows) - wins - losses}, p = {sign_test(wins, losses):.3f}")


if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 33
    n_rollouts = int(sys.argv[2]) if len(sys.argv) > 2 else 220
    widths = [int(w) for w in sys.argv[3:]] or [2, 8, 32]
    print(f"rows {ROWS}, preview {PREVIEW}, final scoring; phase 1: {games} games (seeds 0-{games - 1}), "
          f"cap {GAME_CAP} pieces; phase 2: {n_rollouts} sampled positions, rollouts to game over "
          f"or {ROLLOUT_CAP} pieces")
    out_rows = []
    with Pool(11) as pool:
        for width in widths:
            phase1 = pool.map(find_disagreements, [(width, s) for s in range(games)], chunksize=1)
            moves = sum(p for p, _ in phase1)
            found = [d for _, f in phase1 for d in f]
            higher = sum(d["merged_score"] > d["unmerged_score"] for d in found)
            equal = sum(d["merged_score"] == d["unmerged_score"] for d in found)
            print(f"\nwidth {width}: {len(found)} disagreements in {moves} moves "
                  f"({100 * len(found) / moves:.2f}%); merged best line scores higher in {higher}, "
                  f"equal in {equal}, lower in {len(found) - higher - equal}")
            sample = random.Random(width).sample(found, min(n_rollouts, len(found)))
            jobs = [(width, copy.deepcopy(d["game"]), d[k]) for d in sample for k in ("merged", "unmerged")]
            res = pool.map(rollout, jobs, chunksize=1)
            rows = []
            for i, d in enumerate(sample):
                (ml, mc), (nl, nc) = res[2 * i], res[2 * i + 1]
                rows.append({"width": width, "seed": d["seed"], "piece": d["piece"],
                             "merged_score": d["merged_score"], "unmerged_score": d["unmerged_score"],
                             "score_gap": d["merged_score"] - d["unmerged_score"],
                             "merged_lines": ml, "unmerged_lines": nl,
                             "merged_capped": mc, "unmerged_capped": nc})
            out_rows.extend(rows)
            capped = sum(r["merged_capped"] + r["unmerged_capped"] for r in rows)
            print(f"  rollouts: {len(rows)} positions, {capped}/{2 * len(rows)} rollouts capped")
            compare("all", rows)
            compare("merged line scores higher", [r for r in rows if r["score_gap"] > 0])
            compare("scores equal (tie broken differently)", [r for r in rows if r["score_gap"] == 0])
            diffs = [r["merged_lines"] - r["unmerged_lines"] for r in rows]
            if len(rows) > 2:
                print(f"    Spearman between the two rollouts' lines: "
                      f"{spearman([r['merged_lines'] for r in rows], [r['unmerged_lines'] for r in rows]):.2f}; "
                      f"between score gap and line difference: "
                      f"{spearman([r['score_gap'] for r in rows], diffs):.2f}", flush=True)
    path = os.path.join(RESULTS, "29_merge_disagreements.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"\nWrote {len(out_rows)} positions to {path}")
