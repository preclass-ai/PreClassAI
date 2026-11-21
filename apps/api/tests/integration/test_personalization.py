"""Personalization (ADR-0013): student-chosen options, focus-mode flag, rule-based advice, Habit wording, survey flags."""

import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app import personalization
from app.config import get_settings
from app.ids import uid
from tests.conftest import login
from tests.integration.test_guest import answer_first_mcq, guests_on, new_guest  # noqa: F401  (fixture re-export)

pytestmark = pytest.mark.db
ASSIGN = uid("dan-so-vung:assignment")
URL = f"/v1/student/assignments/{ASSIGN}"
PREFS = "/v1/student/preferences"
CORRECT = "C"  # the seed puts the largest row (the answer of the first MCQ) in the third position


@pytest.fixture
async def on(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[pytest.MonkeyPatch]:
    monkeypatch.setenv("CHAT_ENABLED", "true")
    monkeypatch.setenv("PERSONALIZATION_ENABLED", "true")
    get_settings.cache_clear()
    yield monkeypatch
    monkeypatch.undo()
    get_settings.cache_clear()


async def put(c: httpx.AsyncClient, prefs: dict[str, str]) -> httpx.Response:
    return await c.put(PREFS, json={"preferences": prefs})


async def hint_texts(c: httpx.AsyncClient, item: str) -> list[dict[str, Any]]:
    out = []
    for _ in range(3):
        r = await c.post(f"{URL}/chat", json={"itemId": item, "action": "hint", "requestId": str(uuid.uuid4())})
        assert r.status_code == 200, r.text
        out.append(r.json())
    return out


async def test_flag_off_is_404_and_invisible(client: httpx.AsyncClient) -> None:
    await login(client, "HS10-01")
    assert (await client.get(PREFS)).status_code == 404
    assert (await put(client, {"chia_nho_tung_buoc": "on"})).status_code == 404
    assert (await client.delete(PREFS)).status_code == 404
    assert (await client.get("/v1/auth/config")).json()["personalizationEnabled"] is False


async def test_preferences_crud_defaults_off_and_isolation(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await login(client, "HS10-01")
    assert (await client.get(PREFS)).json() == {"preferences": {}}  # default: everything off
    r = await put(client, {"chia_nho_tung_buoc": "on", "hen_gio_tap_trung": "10"})
    assert r.status_code == 200 and r.json()["preferences"] == {"chia_nho_tung_buoc": "on", "hen_gio_tap_trung": "10"}
    r = await put(client, {"hen_gio_tap_trung": "5", "chia_nho_tung_buoc": "off"})
    assert r.json()["preferences"] == {"hen_gio_tap_trung": "5"}  # partial update, off removes
    await client.post("/v1/auth/logout")
    await login(client, "HS10-02")
    assert (await client.get(PREFS)).json() == {"preferences": {}}  # another student sees nothing of it
    await client.post("/v1/auth/logout")
    await login(client, "HS10-01")
    assert (await client.delete(PREFS)).json() == {"preferences": {}}
    assert (await client.get(PREFS)).json() == {"preferences": {}}


async def test_validation_and_roles(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    assert (await client.get(PREFS)).status_code == 401
    await login(client, "HS10-01")
    for bad in ({"mbti": "on"}, {"adhd": "on"}, {"personality": "on"}, {"hen_gio_tap_trung": "on"}, {"nhac_tien_do": "10"},
                {"chia_nho_tung_buoc": "maybe"}):
        assert (await put(client, bad)).status_code == 422, bad  # only the fixed options, with their own values
    await client.post("/v1/auth/logout")
    await login(client, "gv.dia@preclass.local")
    assert (await client.get(PREFS)).status_code == 403  # preferences are the student's own


async def test_habit_wording_follows_options_without_leaking(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await login(client, "HS10-01")
    items = (await client.get(URL)).json()["items"]
    plain = await hint_texts(client, items[0]["id"])
    await put(client, {"chia_nho_tung_buoc": "on", "uu_tien_bang_so_lieu": "on"})
    small = await hint_texts(client, items[1]["id"])
    assert all(len(s["reply"]) <= len(p["reply"]) + 120 and s["reply"] for s, p in zip(small, plain, strict=True))
    assert "bảng số liệu trước" in small[1]["reply"]  # table first
    assert all(r["label"] == "Tiêu đề" for r in small[1]["sourceRefs"])
    assert len(small[0]["reply"]) <= 111 and len(small[2]["reply"]) <= 111  # one short sentence


async def test_advice_review_quiet_and_preview(client: httpx.AsyncClient, db: AsyncSession, on: pytest.MonkeyPatch) -> None:
    on.setattr(personalization, "REVIEW_MIN_ATTEMPTS", 1)
    on.setattr(personalization, "QUIET_MIN_ATTEMPTS", 1)
    await login(client, "HS10-01")
    items = (await client.get(URL)).json()["items"]
    mcq = next(i for i in items if i["itemType"] == "MCQ")
    sid = uid("user:HS10-01")
    assert await personalization.skill_advice(db, sid) == {}  # no results yet: no advice, nothing stored
    r = await client.post(f"{URL}/attempts", json={"itemId": mcq["id"], "answer": {"choice": "B"}, "requestId": str(uuid.uuid4())})
    assert r.json()["isCorrect"] is False
    assert await personalization.skill_advice(db, sid) == {"COMPARE": "REVIEW"}
    other = next(i for i in items if i["id"] != mcq["id"])
    on.setattr(personalization, "skill_advice", lambda *_a, **_k: _async({other["skill"]: "REVIEW"}))
    h = (await client.get(f"{URL}/habit")).json()["hintsAvailable"]
    adv = {x["itemId"]: x for x in h}
    assert adv[other["id"]]["advice"] == "REVIEW" and adv[other["id"]]["preview"]  # Gợi ý 1 shown open, not counted
    assert adv[other["id"]]["hintsUsed"] == 0 and adv[mcq["id"]]["advice"] is None  # answered items get no advice


async def _async(v: Any) -> Any:
    return v


async def test_quiet_skill_when_right_first_time_without_hints(client: httpx.AsyncClient, db: AsyncSession,
                                                                on: pytest.MonkeyPatch) -> None:
    on.setattr(personalization, "QUIET_MIN_ATTEMPTS", 1)
    await login(client, "HS10-02")
    mcq = next(i for i in (await client.get(URL)).json()["items"] if i["itemType"] == "MCQ")
    r = await client.post(f"{URL}/attempts", json={"itemId": mcq["id"], "answer": {"choice": CORRECT}, "requestId": str(uuid.uuid4())})
    assert r.json()["isCorrect"] is True
    assert await personalization.skill_advice(db, uid("user:HS10-02")) == {"COMPARE": "QUIET"}


async def test_nothing_about_the_student_is_stored_or_inferred(db: AsyncSession) -> None:
    cols = (await db.execute(__import__("sqlalchemy").text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'student_preference'"))).scalars().all()
    assert set(cols) == {"student_id", "key", "value", "updated_at"}


def test_no_psychological_labels_in_code() -> None:
    """ADR-0013: no MBTI / ADHD / personality / health-label field anywhere in the application code."""
    banned = ("mbti", "adhd", "personality", "autis", "dyslex", "tính cách", "rối loạn", "trầm cảm", "learning_style")
    root = Path(__file__).resolve().parents[4]
    hits = []
    for base, exts in ((root / "apps/api/app", {".py"}), (root / "apps/api/alembic", {".py", ".sql"}),
                       (root / "apps/web/src", {".ts", ".tsx"}), (root / "apps/web/app", {".ts", ".tsx", ".css"})):
        for f in base.rglob("*"):
            if f.suffix in exts and f.is_file():
                text = f.read_text(encoding="utf-8", errors="ignore").lower()
                hits += [f"{f.relative_to(root)}: {w}" for w in banned if w in text]
    assert not hits, hits


async def test_survey_csv_has_option_flags_and_focus_mode(client: httpx.AsyncClient, guests_on: None,  # noqa: F811
                                                          on: pytest.MonkeyPatch) -> None:
    on.setenv("GUEST_ACCESS_ENABLED", "true")
    get_settings.cache_clear()
    g = await new_guest(client)
    assert (await put(client, {"hen_gio_tap_trung": "10", "uu_tien_bang_so_lieu": "on", "focus_mode_used": "on"})).status_code == 200
    await answer_first_mcq(client, str((await client.get("/v1/student/assignments")).json()["items"][0]["id"]))
    client.cookies.clear()
    await login(client, "admin@preclass.local")
    lines = (await client.get("/v1/admin/survey/export.csv")).text.strip().split("\n")
    head, row = lines[0].split(","), lines[1].split(",")
    flags = dict(zip(head, row, strict=True))
    assert row[0] == g["surveyCode"] and (flags["pref_chia_nho"], flags["pref_hen_gio_phut"], flags["pref_bang_so_lieu"],
                                          flags["pref_giai_thich"], flags["pref_nhac_tien_do"], flags["focus_mode_used"]) == \
        ("0", "10", "1", "0", "0", "1")
    assert not any(w in lines[0].lower() for w in ("mbti", "adhd", "personality", "tam_ly"))
