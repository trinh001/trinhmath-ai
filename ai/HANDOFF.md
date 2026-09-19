# TrinhMath AI — Persistent handoff

Đọc `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, tài liệu provider liên quan và Git state trước khi hành động. Không đưa secret, private source/OCR, database hay student data vào handoff.

## LAST COMPLETED

Đã dựng provider abstraction offline, Fake provider và router FAST/PRO với unit tests. Không có DeepSeek HTTP transport, API call, key, C2C hay Qwen adapter.

## CURRENT STATE

Phase 1 local verification đã PASS và đang ở checkpoint commit/push. App vẫn không import hay gọi provider mới; feature flag DeepSeek mặc định OFF.

## ACTIVE TASK

Commit/push checkpoint an toàn để cập nhật PR #3, rồi theo dõi CI; không merge.

## ACTIVE BRANCH

`codex-continuous-plan-2026-09-19` tại thời điểm checkpoint này. Luôn kiểm tra bằng `git branch --show-current` trước khi tiếp tục.

## LAST SAFE COMMIT

`ef99071` — implementation checkpoint đã qua full local verification; lấy SHA hiện hành bằng `git log -1 --format=%H` trước khi tiếp tục.

## TEST STATUS

Provider/router: PASS (10); full `toan-ai-local`: PASS (59); isolated self-check và converter checks: PASS. Xem `ai/TEST_STATUS.md`.

## KNOWN RISKS

- Provider interface chưa có transport có chủ ý; run thật cần key, data/budget approval và separate review.
- Current content counts và historical self-check không phải truy vấn live.
- Math/image ambiguity vẫn bắt buộc teacher review.

## BLOCKERS

Không có blocker kỹ thuật cho verification local. API key/network/pilot là stop condition và chưa được ủy quyền.

## NEXT EXACT ACTION

Chạy một lượt `git diff --check`, review staged diff, rồi commit/push branch PR. Sau push, kiểm tra CI. Không merge `main`.
