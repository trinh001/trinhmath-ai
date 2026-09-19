# Nhật ký thay đổi bộ nhớ AI

## 2026-09-20 — Phase 1 DeepSeek offline provider/router

- Active workflow is GPT -> Codex -> DeepSeek FAST/PRO; Qwen was removed from the active roadmap, task queue and provider prompt.
- Added standalone `ai_provider.py` and `model_router.py`: aliases FAST/PRO, configurable mappings, OFF-by-default feature flag, Fake provider, dry-run and fail-closed result handling. No HTTP client, API key, API call or app integration was added.
- Added deterministic routing with explicit codes for default, vision, complex, two FAST failures and critical review. PRO is not routed for vision.
- Standardized persistent handoff, active task, test status, provider policy and continuous runbook for future sessions.

### Xác minh

- PASS: 59 `toan-ai-local` tests, including 10 offline provider/router tests; isolated self-check; converter checks; Python compile/import.
- PASS local final gate: `git diff --check` và quét tracked files không thấy secret/token/key có độ tin cậy cao. CI vẫn chờ branch được push.

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
