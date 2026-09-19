# Codex Continuous Runbook

Dùng prompt ngắn này ở đầu mỗi phiên Codex:

```text
Tiếp tục TrinhMath AI theo chế độ continuous execution.

Đọc theo thứ tự:
1. AGENTS.md
2. ai/PROJECT_STATE.md
3. ai/ARCHITECTURE.md
4. ai/AI_RULES.md
5. ai/MULTI_AI_WORKFLOW.md
6. ai/PROVIDER_POLICY.md
7. ai/MASTER_EXECUTION_PLAN.md
8. ai/TASK_QUEUE.md
9. ai/TEST_STATUS.md
10. git status + git log + diff hiện tại

Sau đó:
- xác định phase hiện tại;
- chọn task đầu tiên đủ điều kiện và reversible;
- tự quyết các chi tiết kỹ thuật nhỏ;
- không hỏi lại nếu không thuộc STOP CONDITIONS;
- làm theo lát cắt nhỏ;
- thêm/điều chỉnh test;
- chạy test liên quan và rộng hơn;
- cập nhật TASK_QUEUE/TEST_STATUS;
- commit/push trên branch riêng;
- tạo PR nếu checkpoint đủ lớn;
- tiếp tục task kế tiếp nếu không có blocker.

STOP CONDITIONS — chỉ dừng hỏi tôi khi:
1. cần API key, account, payment hoặc budget;
2. cần gửi dữ liệu riêng ra ngoài;
3. cần deploy public/cloud;
4. cần migration/xóa/ghi đè dữ liệu khó rollback;
5. cần teacher approval nội dung Toán;
6. có thay đổi product/architecture lớn khó đảo ngược;
7. test fail mà chưa xác định được root cause;
8. phát hiện secret hoặc data leak risk.

Không push thẳng main.
Không auto-merge.
Không gọi paid API khi chưa có approval.
Không tự approve/release câu hỏi.
Không gửi database/student data/raw source hàng loạt ra external provider.

Cuối mỗi checkpoint, báo:
DONE:
FILES:
TESTS:
RISKS:
BLOCKERS:
NEXT:
```

## Cách dùng

- Nếu Codex hết token/session: mở phiên mới và dán đúng prompt trên.
- Không cần kể lại toàn bộ dự án.
- Nếu TASK_QUEUE đã được cập nhật tốt, phiên mới sẽ tiếp tục đúng chỗ.
- Nếu local có thay đổi chưa commit, Codex phải bảo toàn trước khi làm tiếp.
