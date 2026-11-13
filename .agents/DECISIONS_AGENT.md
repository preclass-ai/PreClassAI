# Quyết định của agent (vấn đề · lựa chọn · lý do)

- `.claude/settings.json` (D-001 §5.2: acceptEdits, bỏ python/pip, deny docker down -v) **chưa áp**: bị classifier chặn vì tự sửa quyền của agent. Khải áp tay.
- `.env.*.example` trong `infra/` được thêm ngoại lệ `!.env.*.example` vào `.gitignore` để commit được.
