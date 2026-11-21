"""VAL-10 heuristics and the seed audit (scripts/ops/check_seed_leak.py): the six seed lessons must not answer themselves."""

import importlib.util
from pathlib import Path

from app.validation.leak import item_answer_leaks, severity

OPTS = [("A", "Trung du và miền núi phía Bắc"), ("B", "Tây Nguyên"), ("C", "Đồng bằng sông Hồng"), ("D", "Đông Nam Bộ")]
KEY = {"correct": "C"}


def fact(name: str, v: str) -> tuple[str, str, str]:
    return (name, "data_fact", f"{name}: số dân {v} triệu người 2020 {name}")


def kinds(visible: list[tuple[str, str, str]], opts: list[tuple[str, str]] = OPTS, key: dict = KEY, t: str = "MCQ") -> set[str]:  # type: ignore[type-arg]
    return {f["kind"] for f in item_answer_leaks(t, opts, key, visible)}


def test_the_seed_audit_script_finds_nothing() -> None:
    path = Path(__file__).resolve().parents[4] / "scripts" / "ops" / "check_seed_leak.py"
    spec = importlib.util.spec_from_file_location("check_seed_leak", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bad, labels, n = mod.audit()
    assert n == 12 and not bad, bad
    assert len(labels) >= 3, labels  # the right answer is not always "A"


def test_the_whole_table_shown_is_not_a_leak_and_bang_is_not_bang() -> None:
    table = [fact("Trung du và miền núi phía Bắc", "12,6"), fact("Tây Nguyên", "5,9"), fact("Đồng bằng sông Hồng", "23,2"),
             fact("Đông Nam Bộ", "17,8")]
    stem = ("q2", "stem", "Tính chênh lệch số dân giữa vùng cao nhất và vùng thấp nhất trong bảng.")  # "bảng" ≠ "bằng"
    assert kinds(table + [stem]) == set()


def test_the_old_seed_leaks_are_caught() -> None:
    only_max = [fact("Đồng bằng sông Hồng", "23,2")]  # the old single data fact: the answer row alone
    assert "SINGLED_OUT" in kinds(only_max) and severity(item_answer_leaks("MCQ", OPTS, KEY, only_max)) == "BLOCKER"
    para = [("p", "paragraph", "Năm 2020, vùng đông dân nhất tập trung ở đồng bằng, nơi có điều kiện sản xuất thuận lợi.")]
    assert "CUE_TOKEN" in kinds(para) and severity(item_answer_leaks("MCQ", OPTS, KEY, para)) == "WARNING"
    named = [("p", "paragraph", "Đồng bằng sông Hồng có số dân lớn nhất cả nước.")]
    assert "OPTION_WITH_CUE" in kinds(named) and severity(item_answer_leaks("MCQ", OPTS, KEY, named)) == "BLOCKER"
    other_q = [("q2", "stem", "Tính chênh lệch số dân giữa Đồng bằng sông Hồng và Tây Nguyên.")]  # names two options, one is the answer
    assert kinds(other_q) == {"NARROWS"}


def test_numeric_answer_visible_elsewhere_is_a_blocker() -> None:
    key = {"value": 17.3, "unit": "triệu người"}
    para = [("p", "paragraph", "Chênh lệch giữa hai vùng là 17,3 triệu người.")]
    assert kinds(para, [], key, "NUMERIC") == {"NUMBER"}
    assert kinds([("p", "paragraph", "Năm 2020 có 23,2 và 5,9 triệu người.")], [], key, "NUMERIC") == set()
