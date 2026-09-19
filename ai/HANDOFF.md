# TrinhMath AI — Persistent handoff

Đọc `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, tài liệu provider liên quan và Git state trước khi hành động. Không đưa secret, private source/OCR, database hay student data vào handoff.

## LAST COMPLETED

Đã dựng Phase 2 injected DeepSeek transport contract cùng allow-list, limit, redaction, retry, response validation và Fake transport. Không có HTTP client thật, API call, key, C2C hay Qwen adapter.

## CURRENT STATE

Phase 2 local verification, diff và secret gate đã PASS; implementation commit đã push trên branch mới từ `origin/main`. App vẫn không import hay gọi provider mới, feature flag DeepSeek mặc định OFF.

## ACTIVE TASK

Tạo PR Phase 2 sau xác nhận submission GitHub, rồi theo dõi CI. Không merge.

## ACTIVE BRANCH

`codex/deepseek-transport-2026-09-20` tại thời điểm checkpoint này. Luôn kiểm tra bằng `git branch --show-current` trước khi tiếp tục.

## LAST SAFE COMMIT

`d47b248` — `origin/main` an toàn làm base Phase 2; lấy SHA hiện hành bằng `git log -1 --format=%H` trước khi tiếp tục.

## TEST STATUS

Provider/router/transport: PASS (14); full `toan-ai-local`: PASS (63); isolated self-check và converter checks: PASS. Xem `ai/TEST_STATUS.md`.

## KNOWN RISKS

- Không có HTTP transport có chủ ý; run thật cần implementation review riêng, key, data/budget approval và separate review.
- Current content counts và historical self-check không phải truy vấn live.
- Math/image ambiguity vẫn bắt buộc teacher review.

## BLOCKERS

Không có blocker kỹ thuật cho verification local. HTTP implementation/API key/network/pilot là stop condition và chưa được ủy quyền.

## NEXT EXACT ACTION

Sau xác nhận, tạo PR từ `codex/deepseek-transport-2026-09-20` vào `main`, rồi theo dõi CI; không bật transport HTTP, không yêu cầu key, không chạy pilot và không merge `main`.
