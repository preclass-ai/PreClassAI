"""One real run of the quiz drafting against a local lesson plan, for the numbers only. Writes nothing, prints NO plan content.

    cd apps/api            # CHAT_LLM_BASE_URL / CHAT_LLM_API_KEY / CHAT_LLM_MODEL come from the environment or .env
    uv run python ../../scripts/ops/quizgen_real_run.py "<path to a plan .pdf or .docx>" [--lesson 1]

Per lesson: extracted MCQ, drafted / valid / rejected (with reasons), seconds and tokens for the quiz call and the review call.
"""
import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.getcwd())  # run from apps/api
from app.config import get_settings  # noqa: E402
from app.habit import llm, rules  # noqa: E402
from app.lessonplan import parse_plan_file, quizgen  # noqa: E402
from app.sources.formats import Limits  # noqa: E402


def text_of(plan, doc) -> str:  # type: ignore[no-untyped-def]
    skip = {i for q in doc.mcqs for i in (q.stem, *q.options)}
    seen: set[int] = set()
    lines: list[str] = []
    for s in doc.sections:
        for i in s.anchors:
            if i not in skip and i not in seen:
                seen.add(i)
                lines.append(plan.anchors[i].excerpt)
    return rules.redact("\n".join(lines))[: quizgen.MAX_TEXT]


async def main(path: str, only: int | None) -> None:
    cfg = get_settings()
    client = quizgen.get_client()
    if client is None:
        sys.exit("no model: set CHAT_LLM_BASE_URL, CHAT_LLM_API_KEY, CHAT_LLM_MODEL")
    plan = parse_plan_file(open(path, "rb").read(), Limits())
    print(f"lessons read: {len(plan.lessons)}, model: {cfg.chat_llm_model}, fallback: {cfg.chat_llm_model_fallback or '-'}")
    for n, doc in enumerate(plan.lessons, 1):
        if only and n != only:
            continue
        text = text_of(plan, doc)
        src = quizgen.Source(text)
        print(f"\nlesson {n}: plan text {len(text)} chars, extracted MCQ {len(doc.mcqs)}")
        for kind, system, key, model, want in (("quiz", quizgen.SYSTEM_QUIZ, "questions", quizgen.AiQuestion, cfg.quiz_gen_per_lesson + 2),
                                               ("review", quizgen.SYSTEM_REVIEW, "cards", quizgen.AiCard, 5)):
            t0 = time.monotonic()
            ask = f"Soạn cần {want} {'câu hỏi' if kind == 'quiz' else 'thẻ ôn tập'} từ <plan>."
            try:
                got, bad, tokens, calls, used = await quizgen._ask(client, system, text, ask, key, model, 4000, 90.0)  # noqa: SLF001
            except Exception as e:  # noqa: BLE001
                print(f"  {kind}: model error {type(e).__name__}")
                continue
            rej: dict[str, int] = {"schema": bad} if bad else {}
            ok = 0
            for d in got:
                why = quizgen.check_question(d, src) if isinstance(d, quizgen.AiQuestion) else quizgen.check_card(d, src)  # type: ignore[arg-type]
                if why:
                    rej[why] = rej.get(why, 0) + 1
                else:
                    ok += 1
            print(f"  {kind}: drafted {len(got) + bad}, valid {ok}, rejected {sum(rej.values())} {rej or ''}, "
                  f"{time.monotonic() - t0:.1f}s, {tokens} tokens, {calls} call(s), model {used or '?'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--lesson", type=int, default=None)
    a = ap.parse_args()
    asyncio.run(main(a.path, a.lesson))
