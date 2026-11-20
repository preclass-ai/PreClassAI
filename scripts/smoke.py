#!/usr/bin/env python3
"""End-to-end smoke of the whole flow against a running stack (GĐ10 gate). Stdlib only.

    python scripts/smoke.py --base https://localhost --insecure [--password "$SEED_PASSWORD"] [--student-password ...] [--student-id E2E-1 --class-code E2E] [--basic-auth user:pass]
    python scripts/smoke.py --base https://pre-class-ai.vercel.app          # cloud demo

teacher: source -> lesson -> generate (mock) -> review each block -> publish -> assign
student: list/open assignment (no answers leak) -> attempt -> explanation after answering
teacher: withdraw -> student gets 410. Uses the demo seed accounts (staging only). Exit 1 on the first failure.
"""
import argparse
import base64
import http.cookiejar
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

HEADERS = {"Content-Type": "application/json", "X-PreClass-CSRF": "1"}
LEAK = {"provenance", "anchor", "review", "validation", "answerKey", "answer_key", "contentHash", "withdrawReason"}


class Client:
    def __init__(self, base: str, insecure: bool, basic_auth: str = "") -> None:
        self.base = base.rstrip("/")
        self.auth = {"Authorization": "Basic " + base64.b64encode(basic_auth.encode()).decode()} if basic_auth else {}
        ctx = ssl.create_default_context()
        if insecure:  # Caddy's local CA on `localhost`
            ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
                                              urllib.request.HTTPSHandler(context=ctx))

    def call(self, method: str, path: str, body: object = None) -> tuple[int, dict]:
        req = urllib.request.Request(self.base + path, method=method, headers={**HEADERS, **self.auth, "Origin": self.base},
                                     data=None if body is None else json.dumps(body).encode())
        try:
            with self.op.open(req, timeout=30) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")


def keys(o: object) -> set[str]:
    if isinstance(o, dict):
        return set(o) | {k for v in o.values() for k in keys(v)}
    if isinstance(o, list):
        return {k for v in o for k in keys(v)}
    return set()


def step(name: str, c: Client, method: str, path: str, body: object = None, want: int = 200) -> dict:
    status, out = c.call(method, path, body)
    ok = status == want
    print(f"{'ok  ' if ok else 'FAIL'} {name} [{status}]")
    if not ok:
        print(json.dumps(out, ensure_ascii=False)[:600])
        sys.exit(1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://localhost")
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--password", default="preclass-demo", help="teacher password (and the default for students)")
    ap.add_argument("--student-password", default=None, help="student password (default: --password)")
    ap.add_argument("--student-id", default="HS10-01", help="student login code; on the cloud demo use E2E-1")
    ap.add_argument("--class-code", default="10A1", help="class that receives the smoke lesson; on the cloud demo use E2E (never KS)")
    ap.add_argument("--basic-auth", default="", help="user:pass if the site sits behind basic auth (preview tunnel)")
    a = ap.parse_args()
    t, s = Client(a.base, a.insecure, a.basic_auth), Client(a.base, a.insecure, a.basic_auth)

    step("health", t, "GET", "/v1/health")
    step("teacher login", t, "POST", "/v1/auth/login", {"identifier": "gv.dia@preclass.local", "password": a.password})
    text = ("Số dân các vùng (DỮ LIỆU MINH HỌA)\n\nDân cư phân bố không đều giữa các vùng.\n\n"
            "| Vùng | Số dân (triệu người) |\n|---|---|\n| Đồng bằng sông Hồng | 23,2 |\n| Tây Nguyên | 5,9 |\n"
            "| Đông Nam Bộ | 17,8 |\n| Duyên hải miền Trung | 9,4 |")
    src = step("source", t, "POST", "/v1/sources", {"title": f"[E2E] Smoke {uuid.uuid4().hex[:6]}", "text": text}, 201)
    lesson = step("lesson", t, "POST", "/v1/lessons", {"title": "[E2E] Smoke", "grade": 10,
                  "sourceRevisionIds": [src["latestRevision"]["id"]]}, 201)
    rev = lesson["currentRevision"]["id"]
    job = step("generate", t, "POST", f"/v1/lessons/{lesson['id']}/generate", {"outputType": "WORKSHEET", "nItems": 4}, 202)
    for _ in range(60):  # poll up to ~2 min
        j = step("job", t, "GET", f"/v1/jobs/{job['jobId']}")
        if j["status"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(2)
    assert j["status"] == "SUCCEEDED", j
    for b in step("blocks", t, "GET", f"/v1/revisions/{rev}/blocks")["items"]:
        step(f"review {b['kind']}", t, "POST", f"/v1/blocks/{b['id']}/reviews",
             {"action": "APPROVE", "contentHash": b["contentHash"]}, 201)
    assert step("publish-check", t, "GET", f"/v1/revisions/{rev}/publish-check")["canPublish"] is True
    version = step("lesson", t, "GET", f"/v1/lessons/{lesson['id']}")["currentRevision"]["version"]
    pub = step("publish", t, "POST", f"/v1/revisions/{rev}/publish", {"confirmChecked": True, "version": version}, 201)
    cls = next(x for x in step("classes", t, "GET", "/v1/classes")["items"] if x["code"] == a.class_code)
    now = datetime.now(timezone.utc)
    asg = step("assign", t, "POST", f"/v1/published/{pub['id']}/assignments", {
        "classId": cls["id"], "openAt": (now - timedelta(hours=1)).isoformat(), "dueAt": (now + timedelta(days=1)).isoformat()}, 201)

    step("student login", s, "POST", "/v1/auth/login", {"identifier": a.student_id, "password": a.student_password or a.password})
    listed = step("student list", s, "GET", "/v1/student/assignments")["items"]
    assert any(x["id"] == asg["id"] for x in listed), "assignment not visible to student"
    d = step("student open", s, "GET", f"/v1/student/assignments/{asg['id']}")
    assert d["items"] and not (keys(d) & LEAK), keys(d) & LEAK  # PR-08
    item = next(i for i in d["items"] if i["itemType"] == "MCQ")
    r = step("attempt", s, "POST", f"/v1/student/assignments/{asg['id']}/attempts",
             {"itemId": item["id"], "answer": {"choice": "A"}, "requestId": str(uuid.uuid4())}, 201)
    assert r["explanation"], "explanation must appear after answering"

    step("withdraw", t, "POST", f"/v1/published/{pub['id']}/withdraw", {"reason": "Smoke test"})
    step("student after withdraw", s, "GET", f"/v1/student/assignments/{asg['id']}", want=410)
    print("SMOKE OK")


if __name__ == "__main__":
    main()
