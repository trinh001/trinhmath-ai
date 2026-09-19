# Bàn giao GPT → Codex

Tài liệu này giữ lại phần hữu ích của mô hình “GPT nghĩ – Codex làm”: GPT dùng để làm rõ yêu cầu, lập kế hoạch hữu hạn và review; Codex kiểm tra repository, thực hiện thay đổi tối thiểu, chạy kiểm tra và báo cáo bằng chứng. Đây là quy ước làm việc của TrinhMath, không phải chỉ dẫn cài bridge/tunnel hay kết nối dữ liệu dự án với dịch vụ ngoài.

## Trước khi Codex sửa mã

Đọc theo thứ tự:

1. `AGENTS.md`, `PROJECT_REPORT_2026-09-13.md` và README của ứng dụng liên quan.
2. `ai/PROJECT_STATE.md`, `ai/ARCHITECTURE.md`, `ai/AI_RULES.md`, `ai/TASK_QUEUE.md`.
3. Diff Git hiện tại, module đích và test liên quan.

Không giả định thay đổi chưa commit là của mình. Không sao chép, xóa hay reset dữ liệu hiện có.

## Handoff bắt buộc

GPT hoặc người giao việc gửi một yêu cầu ngắn theo mẫu tại `ai/prompts/CODEX_HANDOFF_TEMPLATE.md`. Codex chỉ mở rộng phạm vi khi người dùng cho phép rõ ràng. Nếu thiếu dữ kiện nguồn, quyền thay đổi, hoặc một quyết định khó rollback, Codex dừng ở kế hoạch/rủi ro thay vì đoán.

## Chu trình thực hiện

1. Tái hiện hoặc đọc log, xác định nguyên nhân.
2. Sửa lát cắt nhỏ nhất, giữ API và dữ liệu tương thích.
3. Thêm regression test thuần nếu sửa lỗi.
4. Chạy test thích hợp, kiểm tra syntax/import và `git diff --check`.
5. Báo file đổi, lệnh/kết quả kiểm tra, rủi ro còn lại và việc cần giáo viên quyết định.

Mọi draft do OCR/AI tạo vẫn là dữ liệu cần review, không phải bằng chứng để duyệt hoặc phát hành.
