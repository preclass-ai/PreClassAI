# ruff: noqa: E501  (Vietnamese reply templates and keyword lists read better on one line)
"""Habit rule engine (0đ): intent detection, PII redaction, hint templates and the answer-leak guard.

Everything here is deterministic. Hints and refusals never depend on the answer key; the guard (`leak`) is a second
line that every outgoing reply passes (rule and LLM alike) before the student sees it.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.sources.numbers import parse_numbers

STOP = {"la", "va", "cua", "cho", "em", "co", "khong", "nay", "nao", "gi", "the", "nhu", "voi", "mot", "cac", "nhung",
        "duoc", "trong", "tu", "den", "bai", "cau", "hoi", "xin", "giup", "minh", "ban", "toi", "thi", "ma", "de"}
# Intent keywords are matched on normalised text (lower case, no diacritics) so one list covers both spellings.
INJECTION = ("bo qua", "ignore", "system prompt", "gia vo", "ban la giao vien", "ban la thay", "ban la co giao",
             "huong dan truoc", "previous instruction", "jailbreak", "developer mode", "pretend", "roleplay",
             "role play", "prompt he thong", "lap lai huong dan", "quen het", "forget", "in ra huong dan",
             "huong dan he thong", "nhap vai", "ban dang la")
ANSWER = ("dap an", "dap so", "answer", "ket qua bang", "ket qua la", "bang bao nhieu", "bao nhieu", "chon cau nao",
          "chon phuong an", "cau nao dung", "cho em ket qua", "tinh giup", "tinh ho", "giai giup", "giai ho", "lam ho",
          "lam giup", "nop ho", "ra bao nhieu", "bang may")
VERDICT = ("dung", "sai", "phai", "loai", "chinh xac", "correct", "wrong", "right", "true", "false",
           "lon nhat", "cao nhat", "nho nhat", "thap nhat", "nhieu nhat", "it nhat")
UNSAFE = {"dm", "dmm", "dcm", "vcl", "vl", "cc", "concac", "deo", "fuck", "shit", "sex", "porn", "giet", "tuy"}
UNSAFE_PHRASES = ("khieu dam", "ma tuy", "tu tu", "dit me", "du ma", "con cac")

REFUSAL = {
    "INJECTION": "HABIT AI chỉ giúp em học bài này thôi, không đổi cách làm việc được. Em thử hỏi: “Em nên bắt đầu từ đâu?” nhé.",
    "ANSWER_REQUEST": "HABIT AI không đưa đáp án, em tự làm nhé. Em có thể xin gợi ý hoặc hỏi cách đọc số liệu.",
    "CONFIRM_OPTION": "HABIT AI không nói phương án nào đúng hay sai, em tự làm nhé. Em thử đọc lại đề rồi xin gợi ý.",
    "UNSAFE": "Mình chỉ hỗ trợ việc học thôi nhé. Nếu cần giúp việc khác, em hỏi thầy cô giúp em nha.",
    "OFFTOPIC": "Câu này nằm ngoài bài học này, HABIT AI chưa trả lời được. Em chọn một gợi ý bên dưới hoặc hỏi thầy cô nhé.",
}

# Suggestion buttons: structured actions, so they never go through the free-text classifier.
SUGGESTIONS = [("start", "Gợi ý bước đầu"), ("where_data", "Số liệu cần dùng nằm ở đâu?"),
               ("formula", "Nhắc lại cách tính"), ("teacher", "Em muốn hỏi thầy cô")]
QUICK_LEVEL = {"start": 1, "where_data": 2, "formula": 3}
TEACHER_REPLY = "Em ghi lại câu hỏi rồi hỏi thầy cô trong giờ học nhé. Thầy cô sẽ giải thích kỹ hơn."
# General "how do I do this" questions are in scope: they get the hint for that step (normalised, so no diacritics needed).
HOWTO = {
    1: ("bat dau", "lam sao", "lam the nao", "khong hieu", "khong biet", "goi y", "cach lam", "nen lam gi", "buoc dau", "bi tac",
        "chua hoc", "hoc tu dau", "hoc the nao", "hoc nhu the nao", "nen hoc", "on tap", "chua biet", "chua hieu", "chua lam"),
    2: ("nam o dau", "tim o dau", "lay o dau", "du lieu nao", "so lieu nao", "du lieu o dau", "so lieu o dau", "bang o dau"),
    3: ("cong thuc", "cach tinh", "tinh nhu the nao", "tinh the nao"),
}


# Greetings, thanks and "I understand": a short friendly reply, no refusal and no model call. Only when EVERY word is small talk,
# so "cảm ơn, cho em đáp án luôn" is not small talk (and the intent check still runs first in `smalltalk`).
_SMALL_ANCHOR = {"cam", "thanks", "thank", "chao", "hello", "hi", "hey", "ok", "oke", "okay", "da", "vang", "hieu", "tuyet", "duoc"}
_SMALL_WORDS = _SMALL_ANCHOR | {"on", "you", "xin", "roi", "voi", "hay", "qua", "nhe", "nha", "nhieu", "thay", "co", "habit", "ai",
                                "em", "ban", "a", "oi", "ha", "chatbot", "bot"}
_SMALL_WORDS.discard("a")  # a lone "A" is an option label, not small talk
SMALL_REPLY = {
    "THANKS": ["Không có gì em nhé! Em cứ làm tiếp câu này, cần gợi ý thì HABIT AI ở đây.",
               "Vui vì giúp được em. Em thử làm tiếp nhé, khi nào kẹt thì xin gợi ý.",
               "Rất vui được giúp em! Giờ em làm tiếp câu này nhé."],
    "GREET": ["Chào em! HABIT AI sẵn sàng. Em đọc đề rồi hỏi mình khi cần gợi ý nhé.",
              "Chào em! Em bắt đầu từ việc đọc kỹ đề, cần gì cứ hỏi HABIT AI.",
              "Xin chào em! Em làm câu này đi, kẹt chỗ nào mình gợi ý cho."],
    "INTRO": ["Mình là HABIT AI, trợ lý học tập của lớp. Mình gợi ý từng bước, không đưa đáp án. Em muốn bắt đầu từ đâu?"],
    "ACK": ["Tốt lắm! Em làm tiếp nhé, cần gợi ý thì cứ hỏi HABIT AI.",
            "Ok em! Em thử làm rồi nộp bài, kẹt thì xin gợi ý.",
            "Được rồi em. Em tiếp tục làm câu này nhé."],
}


_WHO = ("ten gi", "ten la gi", "la ai", "ten minh", "ten ban", "ban la gi")  # "bạn tên gì", "bạn là ai": the assistant introduces itself


def smalltalk(msg: str) -> str | None:
    """INTRO | THANKS | GREET | ACK when the whole message is small talk, else None (any answer request or odd word means None)."""
    n = norm(msg)
    toks = n.split()
    if toks and len(toks) <= 10 and intent(msg, None) is None and any(k in f" {n} " for k in _WHO):
        return "INTRO"
    if not toks or len(toks) > 8 or intent(msg, None) is not None or not set(toks) <= _SMALL_WORDS or not set(toks) & _SMALL_ANCHOR:
        return None
    if set(toks) & {"cam", "thanks", "thank"}:
        return "THANKS"
    return "GREET" if set(toks) & {"chao", "hello", "hi", "hey"} else "ACK"


def howto(msg: str) -> int | None:
    n = f" {norm(msg)} "
    return next((lvl for lvl in (3, 2, 1) if any(c in n for c in HOWTO[lvl])), None)


_PHONE = re.compile(r"(?<!\d)(?:\+?84|0)[\d .\-]{8,12}\d(?!\d)")
_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
_ADDR = re.compile(r"(?i)\b(?:số nhà|so nha|ngõ|hẻm|đường|phường|quận|thôn|xóm)\s+[\w/\-]+(?:\s+[\w/\-]+)?")
_TAG = "[đã ẩn]"


def norm(s: str) -> str:
    d = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    d = "".join(c for c in d if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", d)).strip()


def redact(s: str) -> str:
    return _ADDR.sub(_TAG, _EMAIL.sub(_TAG, _PHONE.sub(_TAG, s)))


@dataclass
class ItemView:
    """What Habit may see of an item. `answer_*`/`explanation` are for the guard and for `explain` only."""
    id: str
    stem: str
    item_type: str
    skill: str
    options: list[tuple[str, str]]
    blocks: list[tuple[str, str, str]]  # (id, label, text) of approved content blocks; data_fact excluded
    unit: str | None
    period: str | None
    answer_label: str | None = None
    answer_value: Decimal | None = None
    explanation: str | None = None
    allowed: set[Decimal] = field(default_factory=set)


def build_view(snap: dict[str, Any], item: dict[str, Any]) -> ItemView:
    kids = [b for b in snap["blocks"] if b["parentId"] == item["id"]]

    def pick(k: str) -> dict[str, Any] | None:
        return next((b["payload"] for b in kids if b["kind"] == k), None)

    key, exp = pick("answer_key"), pick("explanation")
    opts = sorted((b["payload"]["label"], b["payload"]["text"]) for b in kids if b["kind"] == "option")
    label = {"heading": "Tiêu đề", "paragraph": "Đoạn văn", "instruction": "Câu dẫn"}
    blocks = [(b["id"], label[b["kind"]], b["payload"]["text"]) for b in snap["blocks"] if b["kind"] in label]
    fact: dict[str, Any] = next((b["payload"] for b in snap["blocks"] if b["kind"] == "data_fact"), {})
    val = key.get("value") if key else None
    v = ItemView(item["id"], item["payload"]["stem"], item["payload"]["itemType"], item["payload"]["skill"], opts, blocks,
                 fact.get("unit"), fact.get("period"), key.get("correct") if key else None,
                 Decimal(str(val)) if val is not None else None, exp["text"] if exp else None)
    for text in [v.stem, *(t for _, t in opts), *(t for _, _, t in blocks), str(v.period or "")]:
        v.allowed.update(parse_numbers(text))
    if v.answer_value is not None:
        v.allowed.discard(v.answer_value)
    return v


def intent(msg: str, v: ItemView | None) -> str | None:
    """Refusal reason for a student message, or None when it is a normal question."""
    n = f" {norm(msg)} "
    toks = set(n.split())
    if any(k in n for k in INJECTION):
        return "INJECTION"
    if toks & UNSAFE or any(k in n for k in UNSAFE_PHRASES):
        return "UNSAFE"
    if any(k in n for k in ANSWER):
        return "ANSWER_REQUEST"
    verdict = any(f" {k} " in n for k in VERDICT)
    labels = {lab.lower() for lab, _ in v.options} if v else set("abcd")
    mentions = bool(toks & labels) or "phuong an" in n or (v is not None and any(
        len(norm(t)) >= 3 and norm(t) in n for _, t in v.options))
    if (verdict and mentions) or "loai tru" in n or "phuong an nao" in n:
        return "CONFIRM_OPTION"
    return None


def _shingles(s: str, k: int = 5) -> set[tuple[str, ...]]:
    t = norm(s).split()
    return {tuple(t[i:i + k]) for i in range(len(t) - k + 1)}


def leak(text: str, v: ItemView) -> str | None:
    """Why `text` must not reach a student who has not answered this item yet (None = clean)."""
    n = f" {norm(text)} "
    if v.answer_label:
        correct = next((t for lab, t in v.options if lab == v.answer_label), "")
        if correct and norm(correct) in n:
            return "ANSWER"
    if v.answer_value is not None and v.answer_value in set(parse_numbers(text)):
        return "ANSWER"
    if re.search(r"\b(?:dap an|phuong an|lua chon|cau|chon|tra loi)\s+(?:la\s+)?[abcd]\b", n):
        return "ANSWER"
    labels = {lab.lower() for lab, _ in v.options}
    if (set(n.split()) & labels) and any(f" {k} " in n for k in VERDICT):
        return "ANSWER"
    if v.explanation and _shingles(text) & _shingles(v.explanation):
        return "ANSWER"
    return None


def number_ok(text: str, v: ItemView) -> bool:
    """VAL-03 style: every number must come from the approved content; small integers and years are tolerated."""
    for x in parse_numbers(text):
        if x in v.allowed or (x == x.to_integral_value() and (0 <= x <= 10 or 1900 <= x <= 2100) and x != v.answer_value):
            continue
        return False
    return True


L1 = {
    "READ_TABLE": ["Em đọc kỹ đề và xác định xem đề đang hỏi về vùng/đối tượng nào, năm nào, đơn vị gì nhé.",
                   "Bắt đầu bằng việc gạch chân từ khóa trong câu hỏi, rồi tìm đúng hàng và cột tương ứng.",
                   "Em thử nói bằng lời của mình: đề cho dữ liệu gì và hỏi điều gì?"],
    "COMPARE": ["Em hãy liệt kê các đối tượng cần so sánh, rồi xem chúng được so sánh theo tiêu chí nào.",
                "So sánh cần cùng đơn vị và cùng năm. Em kiểm tra điều đó trước nhé.",
                "Em thử sắp xếp các giá trị từ lớn đến nhỏ trong đầu, rồi đối chiếu với đề."],
    "CALCULATE": ["Em xác định đề yêu cầu tính đại lượng nào và cần những số liệu nào để tính.",
                  "Trước khi bấm máy, em viết ra phép tính bằng chữ (ví dụ: A so với B) và kiểm tra đơn vị.",
                  "Em tìm các số cần dùng trong đề, rồi xem đề muốn làm tròn hay giữ nguyên đơn vị."],
    "EXPLAIN": ["Em xem đề hỏi “cái gì” hay “vì sao”, rồi tìm ý liên quan trong phần nội dung bài.",
                "Em thử nêu một ý chính từ nội dung bài, sau đó nối nó với câu hỏi.",
                "Giải thích thường gồm: nêu hiện tượng, nêu nguyên nhân, dẫn chứng từ bài. Em thử viết từng ý."],
}
L3 = {
    "READ_TABLE": "Cách làm: xác định hàng (đối tượng) và cột (chỉ tiêu) mà đề hỏi, đọc giá trị ở ô giao nhau và ghi kèm đơn vị.",
    "COMPARE": "Cách làm: đưa các đối tượng về cùng đơn vị và cùng thời điểm, đọc giá trị từng đối tượng rồi đối chiếu với từng phương án trong đề.",
    "CALCULATE": "Cách làm: đọc các số cần dùng trong đề, chọn phép tính phù hợp với yêu cầu, tính cẩn thận rồi ghi đơn vị theo đề.",
    "EXPLAIN": "Cách làm: nêu ý chính, thêm dẫn chứng lấy từ nội dung bài đã học, và kết luận bằng một câu liên hệ đến câu hỏi.",
}


def _short(text: str, limit: int = 110) -> str:
    """First sentence only (student chose "chia nhỏ từng bước"): same content, less to read at once."""
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return first if len(first) <= limit else first[:limit].rsplit(" ", 1)[0] + "…"


L3B = {
    "READ_TABLE": "Cách làm khác: đặt ngón tay vào đúng hàng và đúng cột mà đề nhắc tới, đọc ô giao nhau, rồi kiểm tra đơn vị trước khi kết luận.",
    "COMPARE": "Cách làm khác: ghi giá trị của từng đối tượng ra nháp, xếp từ lớn đến nhỏ, rồi đọc từng phương án và đối chiếu với danh sách đó.",
    "CALCULATE": "Cách làm khác: viết công thức bằng chữ, thay các số lấy từ đề vào, tính từng bước và kiểm tra đơn vị ở cuối.",
    "EXPLAIN": "Cách làm khác: trả lời theo ba bước ngắn là hiện tượng, nguyên nhân, dẫn chứng lấy từ nội dung bài.",
}
NEXT_STEP = {
    1: "Em đã xem hết các gợi ý bước đầu rồi. Em bấm “Số liệu cần dùng nằm ở đâu?” để sang bước tiếp theo nhé.",
    2: "Em đã xem hết các gợi ý về nguồn số liệu rồi. Em bấm “Nhắc lại cách tính” để sang bước tiếp theo nhé.",
    3: "Em đã xem hết các gợi ý rồi. Em thử làm và nộp bài, hoặc bấm “Em muốn hỏi thầy cô” nhé.",
}


def hint(v: ItemView, level: int, reps: int = 0, small: bool = False,
         table_first: bool = False) -> tuple[str, list[tuple[str, str, str]]]:
    """Level 1: orientation; 2: point at approved source parts (never values); 3: method. `reps` = how often this level was
    already shown in this session: each press gives another template of the same level, and when they run out the reply
    points to the next level. `small` and `table_first` are student-chosen options: wording and order only, never what is revealed."""
    skill = v.skill if v.skill in L1 else "READ_TABLE"
    refs: list[tuple[str, str, str]] = []
    bits = [x for x in (f"đơn vị “{v.unit}”" if v.unit else "", f"năm {v.period}" if v.period else "") if x]
    where = f" Hãy tìm dữ liệu có {' và '.join(bits)}." if bits else ""
    if table_first:
        v2 = [f"Em nhìn vào bảng số liệu trước{' (' + ', '.join(bits) + ')' if bits else ''}, rồi mới đọc đoạn văn.",
              "Em ưu tiên bảng số liệu: tìm đúng hàng và cột đề hỏi, rồi mới quay lại đoạn văn để đối chiếu."]
    else:
        v2 = [f"Em xem lại phần nội dung của bài (tiêu đề và đoạn văn bên dưới).{where} Chỉ cần xác định đúng dữ liệu cần dùng, chưa cần tính vội.",
              f"Em đối chiếu từng từ khóa trong đề với tiêu đề và đoạn văn của bài, rồi đánh dấu chỗ có dữ liệu cần dùng.{where} Chưa cần tính vội."]
    variants = {1: [L1[skill][(reps + len(v.stem)) % 3]] if reps < 3 else [], 2: v2, 3: [L3[skill], L3B[skill]]}[min(max(level, 1), 3)]
    lvl = min(max(level, 1), 3)
    if reps >= (3 if lvl == 1 else len(variants)):
        return NEXT_STEP[lvl], []
    text = variants[0] if lvl == 1 else variants[reps]
    if lvl == 2:
        refs = [b for b in v.blocks if b[1] == "Tiêu đề"][:1] or ([] if table_first else [b for b in v.blocks if b[1] == "Đoạn văn"][:1])
    return (_short(text) if small else text), refs


def ask(v: ItemView, msg: str) -> tuple[str, list[tuple[str, str, str]]] | None:
    """Keyword match against the approved blocks; None when nothing in the lesson matches (→ OFFTOPIC)."""
    q = {t for t in norm(msg).split() if len(t) > 2 and t not in STOP}
    ranked = sorted(((len(q & set(norm(b[2]).split())), b) for b in v.blocks), key=lambda x: -x[0])
    hits = [b for s, b in ranked if s > 0 and leak(b[2], v) is None][:1]  # only the most relevant block
    if hits:
        return "Em thử đối chiếu với phần nội dung đã được thầy cô duyệt dưới đây, rồi tự rút ra câu trả lời nhé.", hits
    if q & (set(norm(v.stem).split()) | set(norm(" ".join(t for _, t in v.options)).split())):
        return "Câu hỏi này liên quan đến đề bài. Em đọc lại đề, gạch chân từ khóa rồi xin gợi ý nếu cần nhé.", []
    return None


def decide(v: ItemView, action: str, msg: str, used_hints: int, small: bool = False,
           table_first: bool = False, quick: str | None = None, seen: dict[int, int] | None = None,
           turn: int = 0) -> tuple[str, int, list[tuple[str, str, str]], str | None]:
    """The whole rule-mode decision, pure: (reply, hint level, source refs, refusal reason). `msg` is already redacted."""
    if action == "explain":  # caller guarantees the student answered this item
        return v.explanation or "Câu này chưa có lời giải.", 0, [], None
    level, reason = 0, None
    refs: list[tuple[str, str, str]] = []
    if action == "hint":
        level = min(used_hints + 1, 3)
        text, refs = hint(v, level, reps=(seen or {}).get(level, 0), small=small, table_first=table_first)
    elif quick:  # a suggestion button: structured, never classified as free text
        if quick == "teacher":
            return TEACHER_REPLY, 0, [], None
        level = QUICK_LEVEL[quick]
        text, refs = hint(v, level, reps=(seen or {}).get(level, 0), small=small, table_first=table_first)
    elif (kind := smalltalk(msg)) is not None:  # "cảm ơn", "ok", "em hiểu rồi": friendly, not "ngoài bài học"
        text = SMALL_REPLY[kind][turn % len(SMALL_REPLY[kind])]
    elif (lvl := howto(msg)) is not None and intent(msg, v) is None:  # "how do I start", "where is the data", ...
        level = lvl
        text, refs = hint(v, level, reps=(seen or {}).get(level, 0), small=small, table_first=table_first)
    else:
        reason = intent(msg, v)
        got = None if reason else ask(v, msg)
        if reason:
            text = REFUSAL[reason]
        elif got is None:
            text, reason = REFUSAL["OFFTOPIC"], "OFFTOPIC"
        else:
            text, refs = got
    refs = [r for r in refs if leak(r[2], v) is None]
    if leak(text, v):  # defence in depth: templates never contain the answer, so this should not fire
        text, reason = REFUSAL["ANSWER_REQUEST"], reason or "ANSWER_LEAK"
    return text, level, refs, reason
