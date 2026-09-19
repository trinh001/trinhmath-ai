# TrinhMath AI — Persistent handoff

Đọc `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, tài liệu provider liên quan và Git state trước khi hành động. Không đưa secret, private source/OCR, database hay student data vào handoff.

## LAST COMPLETED

Phase 3 now caps `max_output_tokens`/request `max_tokens`, total pilot token budget, JSON-only response format, HTTP 429->200 retry and truncated JSON rejection. All tests remain injected/offline; no API call or key.

## CURRENT STATE

Narrow guard update is locally verified (21 targeted, 74 full tests; diff/secret gate PASS) and ready to commit/push. App still does not import or call the provider; feature/pilot flags remain OFF.

## ACTIVE TASK

Commit/push this narrow guard update, then stop. Do not merge or request a key.

## ACTIVE BRANCH

`codex/deepseek-pilot-prep-2026-09-20` tại thời điểm checkpoint này. Luôn kiểm tra bằng `git branch --show-current` trước khi tiếp tục.

## LAST SAFE COMMIT

`da8de28` — implementation checkpoint Phase 3 đã qua full local verification; lấy SHA hiện hành bằng `git log -1 --format=%H` trước khi tiếp tục.

## TEST STATUS

Provider/router/transport/pilot: PASS (23); full `toan-ai-local`: PASS (72); isolated self-check và converter checks: PASS. Xem `ai/TEST_STATUS.md`.

## KNOWN RISKS

- First real run cần API key, data/budget approval, user-selected 5–20 sanitized tasks và separate review.
- Current content counts và historical self-check không phải truy vấn live.
- Math/image ambiguity vẫn bắt buộc teacher review.

## BLOCKERS

Không có blocker kỹ thuật cho verification local. API key/network/pilot thật là stop condition và chưa được ủy quyền.

## NEXT EXACT ACTION

After push, wait for new user scope; do not request a key, run a real pilot or merge `main`.
