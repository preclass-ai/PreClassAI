"""Run the CV 5512 lesson plan reader on real plans kept LOCALLY and print statistics only (never any text).

    cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/eval_lesson_plans.py [folder]    # default: ../../private/giao-an

Counts lessons, how many have all 4 activities, MCQ answered from an underline vs needing the teacher, redacted pieces, time
and peak Python memory per file. The folder is gitignored (`private/`); do not paste its content anywhere.
"""

import sys
import time
import tracemalloc
from collections import Counter
from pathlib import Path

from app.lessonplan import parse_plan_file


def main() -> None:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "private" / "giao-an")
    files = sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.docx"))
    tot: Counter[str] = Counter()
    dist: Counter[int] = Counter()
    for k, f in enumerate(files, 1):
        tracemalloc.start()
        t0 = time.perf_counter()
        try:
            plan = parse_plan_file(f.read_bytes())
        except Exception as e:  # noqa: BLE001 report the failure class only
            print(f"file {k}: FAILED {type(e).__name__}")
            tracemalloc.stop()
            continue
        secs = time.perf_counter() - t0
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        mcq = sum(len(x.mcqs) for x in plan.lessons)
        by_ul = sum(1 for x in plan.lessons for m in x.mcqs if not m.needs_confirmation)
        for x in plan.lessons:
            dist[len(x.activities)] += 1
        full = sum(1 for x in plan.lessons if len(x.activities) == 4)
        types = Counter(a.anchor_type for a in plan.anchors)
        red = sum(x.redacted for x in plan.lessons)
        print(f"file {k}: pages={plan.pages} lessons={len(plan.lessons)} full4={full} mcq={mcq} underline={by_ul} "
              f"anchors={len(plan.anchors)} boxes={types['knowledge_box']} cells={types['table_cell']} figs={types['figure_caption']} "
              f"redacted={red} time={secs:.1f}s peakPyMB={peak:.0f}")
        tot.update(files=1, lessons=len(plan.lessons), full4=full, mcq=mcq, underline=by_ul, redacted=red,
                   no_meta=sum(1 for x in plan.lessons if not (x.ppct_period and x.title)),
                   no_date=sum(1 for x in plan.lessons if x.taught_from is None),
                   mcq_lessons=sum(1 for x in plan.lessons if x.mcqs),
                   mcq_lessons_no_answer=sum(1 for x in plan.lessons if x.mcqs and all(m.needs_confirmation for m in x.mcqs)))
    n = max(1, tot["lessons"])
    print(f"TOTAL files={tot['files']} lessons={tot['lessons']} 4/4 activities={tot['full4']} ({100 * tot['full4'] / n:.0f}%) "
          f"activities distribution={dict(sorted(dist.items()))}")
    m = max(1, tot["mcq"])
    print(f"MCQ={tot['mcq']} answered by underline={tot['underline']} ({100 * tot['underline'] / m:.0f}%) "
          f"needs confirmation={tot['mcq'] - tot['underline']} ({100 * (tot['mcq'] - tot['underline']) / m:.0f}%) "
          f"lessons with MCQ but no underline found={tot['mcq_lessons_no_answer']}/{tot['mcq_lessons']}")
    print(f"lessons without ppct/title={tot['no_meta']} without teach date={tot['no_date']} redacted pieces={tot['redacted']}")


if __name__ == "__main__":
    main()
