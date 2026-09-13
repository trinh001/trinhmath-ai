# TrinhMath AI — Tiến độ phát triển

_Cập nhật: 13/09/2026_

## Trạng thái hiện tại

- Kho đã lập chỉ mục: **387 tài liệu** Word/PDF.
- Câu ứng viên đã tách từ nguồn: **4.843 câu**.
- Kết quả đọc ảnh/công thức đã lưu cục bộ: **2.192 ảnh**; kết quả được tái sử dụng, không gửi lại AI khi không cần thiết.
- Ngân hàng đã duyệt: **7 câu nguồn**; **5 biến thể** đã phát hành an toàn cho học sinh.
- Câu có hình, công thức chưa rõ, ranh giới câu nghi ngờ hoặc thiếu lời giải đều bị **khóa khỏi học sinh**.

## Đã hoàn thành

1. Nhập kho Word/PDF, phân loại khối lớp, chương, bài học, chuyên đề và loại đề.
2. Parser hậu OCR: tách câu, đáp án/lời giải, phát hiện câu dính trang hoặc thiếu ranh giới.
3. Luồng kiểm duyệt: chỉ câu đầy đủ dữ kiện mới được duyệt, đóng gói thành biến thể và phát hành cho học sinh.
4. Render công thức bằng LaTeX/MathJax trong giao diện; xuất đề PDF có giới hạn kích thước công thức để tránh lỗi bố cục.
5. Luyện tập theo bài/chương/chuyên đề/kỳ thi; đồng hồ 45 phút cho ôn chương và 90 phút cho các đề còn lại.
6. Theo dõi tiến độ học sinh, nhận diện chủ đề yếu theo kết quả làm bài.
7. Kiểm tra chất lượng bản nháp AI: chặn `null`/`None`, thiếu đáp án, thiếu lời giải, ghi chú OCR lẫn vào đề, nhãn ý lặp và công thức không chắc chắn.
8. MathType cũ: đọc từng mảnh ở 600 DPI; công thức hỏng được đánh dấu thay vì để AI suy đoán.
9. Cho phép giáo viên chép lại riêng công thức bị hỏng; bản chép được lưu tách khỏi tệp gốc và dùng làm dữ kiện ưu tiên khi tái dựng câu.
10. Lưu kết quả làm bài theo **từng chủ đề**; học sinh và giáo viên thấy bản đồ kiến thức thay vì chỉ có điểm tổng.
11. Lượt luyện đã duyệt tự điều chỉnh mức ưu tiên: dưới 60% củng cố nền tảng, 60–79% luyện chắc, từ 80% mới tăng độ khó. Kho nhỏ vẫn có cơ chế dự phòng, không loại nhầm câu.
12. Kiểm tra phát hành biến thể thống nhất ở mọi đường đi (xem trước, duyệt, xuất PDF và luyện): bắt buộc đủ đề, lời giải, đáp án, bốn lựa chọn không rỗng/trùng; đối chiếu nhãn đáp án được lời giải ghi rõ.
13. Thêm màn độ phủ chương trình lớp 10–12 và hàng đợi phát triển kho: ưu tiên câu đã duyệt chưa phát hành, rồi câu chữ đủ dữ kiện; không tự gọi Gemini hay phát hành.
14. Đồng bộ Math Document Converter: Parser/OCR được ghép với câu nguồn trong hàng duyệt có nhật ký; ảnh/công thức chỉ được liên kết bổ sung, không tự biến thành câu hỏi hay phát hành.

## Việc đang làm

- Kiểm duyệt các câu có MathType/hình để bổ sung công thức chính xác.
- Phân loại sâu hơn số câu Word đã tách để gắn đúng bài học/chuyên đề.
- Tạo bản nháp lời giải cho nhóm có đề và đáp số nhưng thiếu cách làm; mọi bản nháp vẫn cần duyệt.
- Lấp dần các bài còn thiếu biến thể đã duyệt, theo hàng đợi phát triển trong **An toàn & chất lượng**.

## Quy tắc an toàn dữ liệu

- Không đưa tệp nguồn, ảnh đề, cơ sở dữ liệu học sinh, khóa Gemini hoặc dữ liệu đăng nhập lên GitHub.
- Mã nguồn, test, tài liệu vận hành và file này có thể đưa lên GitHub.
- Các tệp dữ liệu cục bộ được giữ trong máy và cần được sao lưu riêng.

## Mốc tiếp theo

1. Hoàn thiện kiểm duyệt công thức cho một nhóm mẫu nhỏ.
2. Duyệt/phát hành các biến thể an toàn đầu tiên cho học sinh.
3. Kiểm thử luồng học sinh từ chọn bài → làm bài → nộp tự động → xem chẩn đoán điểm yếu.
4. Sau khi ổn định, chuẩn hóa triển khai cloud với tách riêng kho dữ liệu và API key.

## Nhật ký phiên gần nhất — 13/09/2026

- Đã rà lại đường đi từ biến thể tới học sinh để không có màn nào bỏ qua kiểm tra dữ liệu.
- Đã phát hiện và sửa lỗi chuẩn hóa nhãn tiếng Việt của mức độ nhận thức: `Vận dụng cao`, `Vận dụng`, `Thông hiểu`, `Nhận biết` nay được nhận diện đúng cả khi so khớp không dấu.
- Đã phát hiện kiểm tra độc lập chưa tạo bảng lưu kết quả theo chủ đề; bổ sung khởi tạo cơ sở dữ liệu trong `self_check.py`, không thay đổi dữ liệu học sinh có sẵn.
- Đã xử lý lỗi giao diện: các câu có cùng nhãn trong danh sách tạo bản nháp không còn bị ghi đè lựa chọn.
- Các kiểm tra đã chạy: biên dịch `app.py`/`self_check.py`, self-check toàn kho, kiểm tra liên kết dữ liệu, kiểm tra cấu trúc biến thể, kiểm tra parser và kiểm tra diff Git.

## Giới hạn đang biết

- App chỉ có thể kiểm tra **cấu trúc** và một số mâu thuẫn đáp án rõ ràng; tính đúng đắn Toán học của mọi lời giải vẫn phải do giáo viên đối chiếu với nguồn hoặc duyệt AI có kiểm soát.
- Công thức MathType/WMF bị hỏng ngay từ tài liệu gốc không thể được làm rõ chỉ bằng OCR; cần bản Word/PDF rõ hơn hoặc giáo viên chép lại công thức.
- Số câu sẵn sàng hiện còn nhỏ, vì vậy chưa nên coi đây là ngân hàng đủ để tạo nhiều đề kiểm tra dài, dù luồng tạo/luyện đề đã hoạt động.
