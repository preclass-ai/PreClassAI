# ruff: noqa: E501
"""One real run of the quiz drafting against a local lesson plan, for the numbers only. Writes nothing, prints NO plan content.

    cd apps/api            # CHAT_LLM_BASE_URL / CHAT_LLM_API_KEY / QUIZ_GEN_MODEL[_FALLBACK] come from the environment or .env
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
    return rules.redact("\n".join(lines))


async def main(path: str, only: int | None) -> None:
    cfg = get_settings()
    client = quizgen.get_client()
    if client is None:
        sys.exit("no model: set CHAT_LLM_BASE_URL, CHAT_LLM_API_KEY and QUIZ_GEN_MODEL")
    plan = parse_plan_file(open(path, "rb").read(), Limits())
    print(f"lessons read: {len(plan.lessons)}, quiz+review model: {cfg.quiz_gen_model}, fallback: {cfg.quiz_gen_model_fallback or '-'} (QUIZ_GEN_MODEL / QUIZ_GEN_MODEL_FALLBACK; chat keeps {cfg.chat_llm_model})")
    for n, doc in enumerate(plan.lessons, 1):
        if only and n != only:
            continue
        sentences = quizgen.fit(quizgen.split_sentences(text_of(plan, doc)), max(quizgen.SYSTEM_QUIZ, quizgen.SYSTEM_REVIEW, key=len))
        src = quizgen.Source("\n".join(sentences))
        text = quizgen.numbered(src)  # what the model sees: [S1] ... [Sn]
        print(f"\nlesson {n}: {len(src.sentences)} numbered sentences, about {quizgen.est_tokens(text)} prompt tokens, extracted MCQ {len(doc.mcqs)}")
        for kind, system, key, model, want, max_tokens in (
                ("quiz", quizgen.SYSTEM_QUIZ, "questions", quizgen.AiQuestion, cfg.quiz_gen_per_lesson + 2, 3000),
                ("review", quizgen.SYSTEM_REVIEW, "cards", quizgen.AiCard, 5, 1300)):  # same limits as the real job
            if kind == "review" and cfg.quiz_gen_gap_s > 0:
                print(f"  waiting {cfg.quiz_gen_gap_s:g}s (QUIZ_GEN_GAP_S) before the review call")
                await asyncio.sleep(cfg.quiz_gen_gap_s)
            t0 = time.monotonic()
            ask = f"Soạn cần {want} {'câu hỏi' if kind == 'quiz' else 'thẻ ôn tập'} từ <plan>."
            try:
                got, bad, tokens, calls, used, failed = await quizgen._ask(client, system, text, ask, key, model, max_tokens, 90.0)  # noqa: SLF001
            except Exception as e:  # noqa: BLE001
                print(f"  {kind}: model error, status {llm.why(e)}, failed models {getattr(e, 'attempts', [])}, "
                      f"prompt {len(text)} chars + max_tokens {max_tokens}")
                continue
            rej: dict[str, int] = {"schema": bad} if bad else {}
            ok = 0
            scores: list[int] = []
            for d in got:
                why = quizgen.check_question(d, src) if isinstance(d, quizgen.AiQuestion) else quizgen.check_card(d, src)  # type: ignore[arg-type]
                if why:
                    rej[why] = rej.get(why, 0) + 1
                    if why == "quote_not_in_plan":
                        scores.append(quizgen.quote_score(getattr(d, "source_quote", ""), src))  # numbers only, never the text
                else:
                    ok += 1
            print(f"  {kind}: drafted {len(got) + bad}, valid {ok}, rejected {sum(rej.values())} {rej or ''}, "
                  f"{time.monotonic() - t0:.1f}s, {tokens} tokens, {calls} call(s), model {used or '?'}, failed models first {failed or '-'}")
            if scores:
                print(f"    best quote match per rejected item (0 to 100, pass at {quizgen.FUZZY_MIN}): {scores}")
            ids = sum(1 for d in got if getattr(d, "source_sentence_ids", None))
            print(f"    drafts that used sentence ids: {ids}/{len(got)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--lesson", type=int, default=None)
    a = ap.parse_args()
    asyncio.run(main(a.path, a.lesson))
