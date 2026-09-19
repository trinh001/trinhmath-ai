# TrinhMath AI — Persistent handoff

Đọc `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, tài liệu provider liên quan và Git state trước khi hành động. Không đưa secret, private source/OCR, database hay student data vào handoff.

## LAST COMPLETED

Đã dựng Phase 3 pilot prep: isolated runner, sanitized fixture, audit schema và budget/kill-switch/feature gates trên Phase 2 transport contract. Không có API call, key, C2C hay Qwen adapter.

## CURRENT STATE

Phase 3 local verification, final diff và secret gate đã PASS trên branch mới từ `origin/main`; commit/push còn chờ. App vẫn không import hay gọi provider mới, feature/pilot flags mặc định OFF.

## ACTIVE TASK

Commit/push branch Phase 3, rồi tạo PR và theo dõi CI. Không merge.

## ACTIVE BRANCH

`codex/deepseek-pilot-prep-2026-09-20` tại thời điểm checkpoint này. Luôn kiểm tra bằng `git branch --show-current` trước khi tiếp tục.

## LAST SAFE COMMIT

`c09b2ee` — `origin/main` an toàn làm base Phase 3; lấy SHA hiện hành bằng `git log -1 --format=%H` trước khi tiếp tục.

## TEST STATUS

Provider/router/transport/pilot: PASS (23); full `toan-ai-local`: PASS (72); isolated self-check và converter checks: PASS. Xem `ai/TEST_STATUS.md`.

## KNOWN RISKS

- First real run cần API key, data/budget approval, user-selected 5–20 sanitized tasks và separate review.
- Current content counts và historical self-check không phải truy vấn live.
- Math/image ambiguity vẫn bắt buộc teacher review.

## BLOCKERS

Không có blocker kỹ thuật cho verification local. API key/network/pilot thật là stop condition và chưa được ủy quyền.

## NEXT EXACT ACTION

Review staged diff, commit/push branch Phase 3 rồi tạo PR; không yêu cầu key, không chạy pilot thật và không merge `main`.
