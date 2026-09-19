# Hàng đợi công việc TrinhMath AI

## Trạng thái hiện tại

- Đánh giá gói tham khảo `codex-with-chatgpt-main` và chuẩn hóa bộ nhớ dự án GPT → Codex đã hoàn tất. Không đưa Node bridge, tunnel, OAuth hoặc dependency của gói vào hai ứng dụng TrinhMath.

## Việc tiếp theo đã có căn cứ

1. Giáo viên đối chiếu một nhóm draft parser cục bộ với tài liệu nguồn; công thức/hình chưa rõ phải tiếp tục `BLOCK + REQUIRE TEACHER REVIEW`.
2. Khi có nguồn hoặc bản chép tay rõ, kiểm tra một nhóm MathType/hình theo luồng ảnh → công thức → draft → review; không suy đoán công thức.
3. Khi có đủ câu đã duyệt theo bài, kiểm thử một lượt học sinh hoàn chỉnh: chọn phạm vi → làm → nộp → bản đồ chủ đề → đề xuất luyện tiếp.
4. Trước bất kỳ thay đổi OCR provider nào, lập golden set được giáo viên cho phép và benchmark cục bộ; không cài model hoặc gọi API tính phí chỉ để thử.

## Không tự đưa vào hàng đợi triển khai

- Không cài hoặc vận hành `codex-with-chatgpt`: đây là công cụ tích hợp bên ngoài có Cloudflare tunnel/OAuth, không phải một nhu cầu đã được phê duyệt của TrinhMath.
- Không tự triển khai cloud, migration database, thay đổi phân quyền hoặc phát hành nội dung.
