"use client";

import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Button, ErrorBox } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";

type Card = Schemas["StudentReviewCard"];
type State = Schemas["ReviewState"];
export type Stage = "ask" | "review" | "quiz";

/** Saves progress of the quick review (cards seen, self-check results). Not scored. */
function useSave(assignmentId: string, onSaved: () => void) {
  return useMutation({
    mutationFn: (body: Schemas["ReviewProgressIn"]) =>
      unwrap(api.PUT("/v1/student/assignments/{assignment_id}/review", { params: { path: { assignment_id: assignmentId } }, body })),
    onSuccess: onSaved,
  });
}

/** "1. Ôn nhanh" then "2. Làm bài kiểm tra": the two steps of a lesson that has a quick review. */
export function Steps({ stage }: { stage: Stage }) {
  const first = stage !== "quiz";
  return (
    <ol className="steps" aria-label="Các bước của bài">
      <li aria-current={first ? "step" : undefined} className={first ? "on" : "done"}>
        1. Ôn nhanh
      </li>
      <li aria-current={first ? undefined : "step"} className={first ? "" : "on"}>
        2. Làm bài kiểm tra
      </li>
    </ol>
  );
}

/** First visit: one question. "Chưa" goes to the review first, "Rồi" straight to the quiz. */
export function ReviewAsk({ assignmentId, onChoose, onSaved }: { assignmentId: string; onChoose: (c: "not_yet" | "done") => void; onSaved: () => void }) {
  const save = useSave(assignmentId, onSaved);
  const pick = (choice: "not_yet" | "done") => {
    onChoose(choice);
    save.mutate({ choice });
  };
  return (
    <section className="card stack" aria-labelledby="learned-q">
      <h2 id="learned-q">Em đã học bài này chưa?</h2>
      <div className="row">
        <Button variant="primary" onClick={() => pick("not_yet")}>
          Chưa, ôn trước
        </Button>
        <Button onClick={() => pick("done")}>Rồi, làm luôn</Button>
      </div>
      <ErrorBox error={save.error} />
    </section>
  );
}

export function ReviewStepper({ assignmentId, cards, state, startId, onDone, onSaved }: {
  assignmentId: string;
  cards: Card[];
  state: State;
  startId?: string | null;
  onDone: () => void;
  onSaved: () => void;
}) {
  const first = Math.max(0, cards.findIndex((c) => c.id === startId));
  const [idx, setIdx] = useState(first);
  const [picked, setPicked] = useState<Record<string, boolean>>({}); // card id -> the self-check answer chosen ("true" statement or not)
  const save = useSave(assignmentId, onSaved);
  const card = cards[Math.min(idx, cards.length - 1)];
  const sent = useRef<Set<string>>(new Set(state.seenIds));
  const last = idx >= cards.length - 1;

  useEffect(() => {
    setIdx(first);
  }, [first]);
  useEffect(() => {
    // viewing a card counts as seeing it; progress only moves forward on the server
    if (card && !sent.current.has(card.id)) {
      sent.current.add(card.id);
      save.mutate({ seenIds: [card.id] });
    }
  }, [card, save]);

  if (!card) return null;
  const answered = card.id in picked || card.id in (state.checks ?? {});
  const answer = (said: boolean) => {
    setPicked((x) => ({ ...x, [card.id]: said }));
    save.mutate({ checks: { [card.id]: said === card.check.answerTrue } });
  };
  const right = card.id in picked ? picked[card.id] === card.check.answerTrue : state.checks?.[card.id];
  const finish = () => {
    save.mutate({ reviewed: true }, { onSuccess: onDone });
  };

  return (
    <section className="card stack" aria-labelledby="review-title">
      <p className="muted small">
        Thẻ {idx + 1}/{cards.length} · không tính điểm
      </p>
      <h2 id="review-title">{card.title}</h2>
      <ul>
        {card.points.map((p, i) => (
          <li key={i}>{p}</li>
        ))}
      </ul>
      <p className="review-example">
        <strong>Ví dụ:</strong> {card.example}
      </p>
      <div className="stack" role="group" aria-label="Tự kiểm tra nhanh">
        <p>
          <strong>Tự kiểm tra:</strong> {card.check.statement}
        </p>
        <div className="row">
          <Button disabled={answered} onClick={() => answer(true)}>
            Đúng
          </Button>
          <Button disabled={answered} onClick={() => answer(false)}>
            Sai
          </Button>
        </div>
        {answered ? (
          <div className={`alert alert-${right ? "success" : "info"}`} role="status">
            <strong>{right ? "Đúng rồi" : "Chưa đúng"}</strong>
            <p className="explanation">{card.check.explanation}</p>
          </div>
        ) : null}
      </div>
      <ErrorBox error={save.error} />
      <div className="row">
        <Button disabled={idx <= 0} onClick={() => setIdx((i) => Math.max(0, i - 1))}>
          Thẻ trước
        </Button>
        {last ? (
          <Button variant="primary" onClick={finish}>
            Xong, làm bài
          </Button>
        ) : (
          <Button variant="primary" onClick={() => setIdx((i) => i + 1)}>
            Thẻ tiếp
          </Button>
        )}
      </div>
      {!last ? (
        <Button variant="ghost" onClick={finish}>
          Đủ rồi, làm bài
        </Button>
      ) : null}
    </section>
  );
}
