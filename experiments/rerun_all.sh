#!/usr/bin/env bash
# Re-run every reproducible entry in log.txt and save each output to
# experiments/results/. Takes about 45 minutes on 11 cores.
#
#   bash experiments/rerun_all.sh
#
# Entry 1 needs the teammate's cw/future-piece branch; it is checked out into a
# temporary worktree and removed afterwards.
set -euo pipefail

EXP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$EXP")"
OUT="$EXP/results"
mkdir -p "$OUT"
cd "$REPO/tetris-base"

run() {  # run NAME COMMAND...: print a header, run, save the output.
    local name="$1"; shift
    echo "== $name: $*"
    local start=$SECONDS
    "$@" > "$OUT/$name.txt" 2>&1
    echo "   done in $((SECONDS - start)) s -> results/$name.txt"
}

WT="$(mktemp -d)/future-piece"
git -C "$REPO" worktree add -q --detach "$WT" origin/cw/future-piece
run 01_future_piece_branch python3 "$EXP/future_piece_branch.py" "$WT/tetris-base"
git -C "$REPO" worktree remove --force "$WT"

run 02_preview1_6rows      python3 "$EXP/preview1_6rows.py"
run 03_reference_benchmark python3 benchmark.py --games 100
run 04_cpp_match           python3 main.py --headless --rows 10 --seed 6 --pieces 0
run 05_control_10rows      python3 benchmark.py --rows 10 --games 20 --cap 0 --settings
run 06_sum_vs_final        python3 benchmark.py --games 100 --settings 1x8:sum 1x8:final \
    2x2:sum 2x2:final 2x8:sum 2x8:final 2x32:sum 2x32:final 3x8:sum 3x8:final \
    --csv "$OUT/06_sum_vs_final.csv"
run 07_stack_height        python3 "$EXP/stack_height.py" 5 100 2000
run 08_eval_stats          python3 "$EXP/eval_stats.py"
run 09_duplicate_frequency python3 "$EXP/duplicate_frequency.py"
run 11_merge_vs_no_merge   python3 "$EXP/merge_vs_no_merge.py"
find "$REPO" -name __pycache__ -prune -exec rm -rf {} +
echo "all done"
