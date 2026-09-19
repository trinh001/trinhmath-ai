# TrinhMath AI — Hướng dẫn làm việc lâu dài

## Phạm vi và nguồn sự thật

- Repository gồm hai ứng dụng cục bộ: `toan-ai-local` (học tập/ngân hàng câu hỏi) và `math-document-converter` (OCR, parser, matching).
- Đọc `PROJECT_REPORT_2026-09-13.md`, `toan-ai-local/PROGRESS.md`, README của hai ứng dụng, `.gitignore`, lịch sử Git và test liên quan trước khi thay đổi.
- Code và dữ liệu hiện có là nguồn sự thật. Không thiết kế lại toàn bộ ứng dụng hoặc viết lại pipeline đã tồn tại nếu chưa xác minh nó thiếu.

## Pipeline và an toàn dữ liệu

Luồng bắt buộc là: `Tài liệu → Parser/OCR → Candidate → Draft AI/cục bộ → Structural validation → Math verification → Teacher review → Approved question → Student variant → Release validation → Luyện tập → Topic performance → Adaptive practice`.

- OCR/AI tạo dữ liệu không đồng nghĩa dữ liệu được phép hiển thị cho học sinh.
- Không tự phát hành; dữ liệu mơ hồ phải `BLOCK + REQUIRE TEACHER REVIEW`.
- Chặn biến thể có đề/lời giải/đáp án thiếu, `None`/`null`, OCR note, ranh giới câu nghi ngờ, hình/công thức chưa rõ, lựa chọn rỗng/trùng, thiếu bốn phương án, đáp án sai nhãn, hoặc mâu thuẫn giữa lời giải và đáp án.
- Không đoán công thức OCR/MathType. Giữ ảnh nguồn, raw OCR, confidence, trạng thái review và bản chép tay giáo viên tách biệt với nguồn.
- Converter không tự phát hành sang ngân hàng học sinh. Mọi liên kết cần truy vết và qua review riêng.

## Bảo toàn dữ liệu và bảo mật

- Không ghi đè nguồn, raw OCR, câu đã duyệt, lịch sử review, kết quả học sinh, ID tham chiếu hoặc migration mất dữ liệu.
- Mọi cải tiến nội dung đi theo `SOURCE → DERIVED VERSION → REVIEW → APPROVED`.
- Không commit API key, mật khẩu, database, tài liệu nguồn, ảnh OCR, login state hay dữ liệu máy cục bộ. Giữ `.gitignore` hiệu lực.
- Không tự gọi API tốn phí, triển khai cloud/public, thay đổi tài khoản/quyền hoặc xóa dữ liệu. Chỉ hỏi người dùng khi những việc này, hoặc lựa chọn kiến trúc khó rollback, là cần thiết.

## Cách phát triển và kiểm tra

- Tự quyết các lựa chọn kỹ thuật nhỏ, có thể rollback và không thay đổi hành vi sản phẩm đáng kể.
- Refactor từng lát cắt, giữ API tương thích, rồi chạy test trước khi đi tiếp.
- Khi gặp lỗi: tái hiện → đọc log → tìm nguyên nhân → sửa tối thiểu → thêm regression test → chạy kiểm tra liên quan và rộng hơn.
- Giữ `self_check.py`; bổ sung test thuần trong `toan-ai-local/tests/` để không phụ thuộc dữ liệu riêng tư. CI không được phụ thuộc API key, database hoặc tài liệu cục bộ.
- Math verifier chỉ trả `VERIFIED`, `CONTRADICTED`, `INCONCLUSIVE` hoặc `UNSUPPORTED`; `INCONCLUSIVE` không phải đã kiểm chứng.
- Cập nhật `toan-ai-local/PROGRESS.md` và báo cáo kỹ thuật sau mỗi thay đổi đáng kể, nêu file sửa, test, rủi ro và bước tiếp theo.
