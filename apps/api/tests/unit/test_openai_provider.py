"""OpenAICompatibleProvider against a local fake /chat/completions server (no network, no DB)."""

import json
import threading
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from app.generation.providers import AnchorView, GenRequest, OpenAICompatibleProvider, ProviderFormatError

GOOD = {"blocks": [{"key": "s0", "kind": "paragraph", "payload": {"text": "x"}, "transformation": "ORIGINAL",
                    "anchorAliases": ["A1"], "isFactual": True}]}
seen: list[dict[str, Any]] = []
reply: list[str] = []


class H(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        seen.append({"path": self.path, "auth": self.headers["Authorization"],
                     "body": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
        out = json.dumps({"model": "m1", "usage": {"prompt_tokens": 7, "completion_tokens": 3},
                          "choices": [{"message": {"content": reply[0]}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a: object) -> None:
        pass


@pytest.fixture
def provider() -> Any:
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    seen.clear()
    yield OpenAICompatibleProvider(f"http://127.0.0.1:{srv.server_port}/v1/", "k", "m0", timeout=5)
    srv.shutdown()


REQ = GenRequest(10, "WORKSHEET", 4, [], [AnchorView("A1", "c", "PARAGRAPH", {"para_index": 0}, "Đoạn.", [Decimal(1)])])


async def test_parses_json_and_sends_alias_only_prompt(provider: OpenAICompatibleProvider) -> None:
    reply[:] = ["```json\n" + json.dumps(GOOD) + "\n```"]  # fenced output is accepted
    r = await provider.generate(REQ)
    assert r.draft.blocks[0].anchorAliases == ["A1"] and (r.tokens_in, r.tokens_out, r.model) == (7, 3, "m1")
    s = seen[0]
    assert s["path"] == "/v1/chat/completions" and s["auth"] == "Bearer k" and s["body"]["temperature"] == 0
    assert "[A1]" in s["body"]["messages"][1]["content"] and "<anchors>" in s["body"]["messages"][1]["content"]


@pytest.mark.parametrize("bad", ["không phải json", '{"blocks": "x"}', "[]"])
async def test_invalid_output_is_a_format_error(provider: OpenAICompatibleProvider, bad: str) -> None:
    reply[:] = [bad]
    with pytest.raises(ProviderFormatError):
        await provider.generate(REQ)
