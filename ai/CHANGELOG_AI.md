# Nhật ký thay đổi bộ nhớ AI

## 2026-09-20 — Phase 3 DeepSeek pilot preparation

- Added standalone `deepseek_pilot.py`: explicit pilot policy, kill switch, task/item/retry/timeout/payload/token guards, FAST/PRO routing audit, redacted metadata and review-only results.
- Added two synthetic algebra/code fixtures and a pilot contract. No source/OCR/student/database record was copied; no app integration, key read or API request exists.
- PASS local: 23 provider/router/transport/pilot tests; 72 full pytest; isolated self-check; converter suite; final diff/security gate. Commit/push and CI are pending.

## 2026-09-20 — Phase 2 injected transport guardrails

- `DeepSeekProvider` nay có injected transport contract, `FakeDeepSeekTransport` và `UrllibDeepSeekTransport` explicit. HTTP transport không được tạo mặc định; test dùng fake opener, nên repository/CI không có API call.
- Mọi outbound attempt phải qua feature flag, dry-run, API-key presence, model mapping, task-class allow-list, timeout/retry/item/payload bounds và sensitive-payload rejection. Response phải là JSON mapping hợp lệ; retry chỉ theo giới hạn request.
- Không thay đổi `app.py`, data/OCR/database, release flow hay cấu hình key. Phase này chưa đủ điều kiện để yêu cầu `DEEPSEEK_API_KEY`.
- PASS local: 15 provider/router/transport tests; 64 full pytest; isolated self-check; converter compile/test suite; `git diff --check` và secret scan. Implementation branch đã push; PR/CI chờ submission GitHub được xác nhận.

## 2026-09-20 — Phase 1 DeepSeek offline provider/router

- Active workflow is GPT -> Codex -> DeepSeek FAST/PRO; Qwen was removed from the active roadmap, task queue and provider prompt.
- Added standalone `ai_provider.py` and `model_router.py`: aliases FAST/PRO, configurable mappings, OFF-by-default feature flag, Fake provider, dry-run and fail-closed result handling. No HTTP client, API key, API call or app integration was added.
- Added deterministic routing with explicit codes for default, vision, complex, two FAST failures and critical review. PRO is not routed for vision.
- Standardized persistent handoff, active task, test status, provider policy and continuous runbook for future sessions.

### Xác minh

- PASS: 59 `toan-ai-local` tests, including 10 offline provider/router tests; isolated self-check; converter checks; Python compile/import.
- PASS local final gate: `git diff --check` và quét tracked files không thấy secret/token/key có độ tin cậy cao. GitHub Actions implementation run `35457468504` PASS ở cả `trinhmath-code` và `converter-code`.

## 2026-09-19 — Đánh giá gói “GPT nghĩ – Codex làm”

- Đã kiểm kê gói “GPT nghĩ – Codex làm” được cung cấp cục bộ như một ứng dụng Node/TypeScript bên ngoài.
- Chỉ tiếp nhận mô hình bàn giao có kiểm soát GPT → Codex thành tài liệu dự án; không sao chép code, script, config, dependency, test, OAuth, Cloudflare tunnel hay cài đặt của gói.
- Thêm `PROJECT_STATE.md`, `TASK_QUEUE.md`, `GPT_TO_CODEX.md` và mẫu handoff để các phiên sau có ngữ cảnh thực tế mà không cần cài công cụ bên ngoài.
- Không thay đổi mã ứng dụng, database, raw OCR, nguồn tài liệu, dữ liệu học sinh, secret hoặc trạng thái phát hành.

### Xác minh

- PASS: `toan-ai-local` self-check trên bản sao tạm cô lập — `candidates=4843, ready_multiple_choice=4`.
- PASS: `toan-ai-local` — 49 pytest tests và Python compile/import.
- PASS: `math-document-converter` — `test_core.py`, `test_matching.py`, `test_question_parser.py`, `test_review_storage.py` và Python compile/import.
- Không phát hiện secret/token/key thực trong Git-tracked files qua tên tệp và mẫu khóa có độ tin cậy cao. Chuỗi trông giống secret trong test của gói ngoài là fixture/sentinel kiểm thử, không phải credential vận hành.
