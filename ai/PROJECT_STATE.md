# TrinhMath AI — trạng thái dự án

_Cập nhật: 19/09/2026. Đây là ảnh chụp từ mã nguồn, `PROJECT_REPORT_2026-09-13.md` và `toan-ai-local/PROGRESS.md`; các số liệu nội dung không phải truy vấn trực tiếp cơ sở dữ liệu._

## Ứng dụng hiện có

- `toan-ai-local/` là ứng dụng Streamlit cục bộ cho giáo viên/học sinh, kho câu hỏi và các hàng rào phát hành.
- `math-document-converter/` là workbench OCR/parser cục bộ riêng. Output của nó không tự trở thành nội dung học sinh.
- Pipeline bắt buộc: nguồn → OCR/parser → candidate → draft → structural validation → math verification → teacher review → approved question → student variant → release validation → practice/adaptive guidance.

## Trạng thái nội dung đã ghi nhận

- 387 tài liệu Word/PDF đã lập chỉ mục; 4.843 candidate; 2.192 lượt đọc ảnh/công thức cache cục bộ.
- 7 câu nguồn đã duyệt, 5 biến thể được phát hành an toàn; 36 draft chờ review, gồm 21 draft parser cục bộ bắt buộc đối chiếu giáo viên.
- Công thức/hình mơ hồ, ranh giới câu không chắc và lời giải thiếu bị chặn khỏi học sinh.

## Trạng thái workspace khi cập nhật

- Source đã được kiểm tra và đồng bộ an toàn trong ngày 19/09/2026. Khi cần biết branch, commit hoặc trạng thái hiện tại, luôn chạy Git (`git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`); tài liệu này không quyết định branch.
- Khi ảnh chụp trạng thái này được tạo, workspace có thay đổi chưa commit từ trước. Không coi thay đổi chưa kiểm tra là của phiên hiện tại và không ghi đè chúng.
- Không có thay đổi nào được phép vào database, raw OCR, tài liệu nguồn, dữ liệu học sinh, trạng thái review/approval/release hoặc API key.

## Xác minh gần nhất

- 19/09/2026: chạy `self_check.py` trên bản sao tạm cô lập, PASS: `candidates=4843, ready_multiple_choice=4`.
- 19/09/2026: `toan-ai-local` pytest, PASS: 49 tests.
- 19/09/2026: bốn test script của `math-document-converter`, PASS; Python compile/import cũng PASS.

## Checkpoint kỹ thuật 20/09/2026

- Thêm provider abstraction offline và router FAST/PRO độc lập; `app.py` chưa gọi hoặc import provider, DeepSeek mặc định OFF và không có HTTP client/API key trong repository.
- Workflow active là GPT -> Codex -> DeepSeek FAST/PRO; Qwen không thuộc roadmap/provider active.
- 59 pytest của `toan-ai-local` (gồm 10 test provider/router offline), self-check cô lập và bốn converter checks đều PASS. Xem `ai/TEST_STATUS.md` để biết lệnh và giới hạn của lần chạy.

## Phase 2 transport guardrails 20/09/2026

- DeepSeek transport là interface injected với Fake và `UrllibDeepSeekTransport` explicit; không có default HTTP client, nên không thể phát sinh external request chỉ vì môi trường có key/flag.
- Allow-list, bounds, payload secret rejection, retry bounded và JSON response validation đều fail closed; `app.py` vẫn không gọi provider.
- 64 pytest (15 provider/router/transport tests), isolated self-check và converter checks PASS. Xem `ai/TEST_STATUS.md` để biết trạng thái commit/CI hiện thời.

Các lần chạy này không dùng API trả phí và không sửa database, raw OCR hay nguồn thật: self-check dùng junction chỉ-đọc tới nguồn và database riêng trong thư mục tạm.
