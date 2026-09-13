# Báo cáo kỹ thuật TrinhMath AI

_Ngày cập nhật: 13/09/2026_  
_Phạm vi: `toan-ai-local` và `math-document-converter`_

## 1. Mục tiêu sản phẩm

TrinhMath AI là hệ thống biến tài liệu Word/PDF thành kho câu hỏi Toán có kiểm duyệt, sau đó tạo lượt luyện và theo dõi phần kiến thức mỗi học sinh cần bồi dưỡng.  Nguyên tắc xuyên suốt là **không đưa dữ liệu OCR, công thức hoặc đáp án chưa đủ tin cậy cho học sinh**.

Math Document Converter là công cụ cục bộ hỗ trợ OCR/Pix2Text và Parser. Nó không tự phát hành câu sang TrinhMath AI; mọi liên kết hoặc quyết định duyệt đều có nhật ký và phải qua bước phát hành riêng.

## 2. Dữ liệu hiện có

- 387 tài liệu Word/PDF đã lập chỉ mục.
- 4.843 câu ứng viên đã tách từ nguồn.
- 2.192 kết quả đọc ảnh/công thức được lưu cục bộ để tái sử dụng.
- 7 câu nguồn đã được duyệt.
- 5 biến thể hiện sẵn sàng cho học sinh.

Các số liệu này là ảnh chụp tại thời điểm báo cáo. Dữ liệu nguồn, ảnh, cơ sở dữ liệu học sinh và khóa API chỉ nằm cục bộ, không đưa lên GitHub.

## 3. Những phần đã hoàn thành

### Kho đề và Parser

- Nhập Word/PDF, phân lớp 10–12, chương, bài học, chuyên đề và loại đề.
- Parser hậu OCR nhận dạng ranh giới câu, đáp án/lời giải, câu dính trang và một số câu thiếu số thứ tự.
- Bảo toàn văn bản/công thức nguồn; luôn lưu OCR thô để có thể đối chiếu hoặc xử lý lại.
- Nhận diện MathType cũ trong Word qua ảnh WMF/OLE, render ở độ phân giải cao để đọc lại.

### Kiểm duyệt và an toàn

- Câu có hình/công thức thiếu tin cậy, ranh giới nghi ngờ hoặc chỉ có đáp số đều bị chặn khỏi học sinh.
- Bản nháp AI bị chặn khi có `None`, thiếu đề, đáp án, lời giải; khi lẫn ghi chú OCR; hoặc khi có nhãn ý trùng.
- Biến thể cho học sinh phải có cấu trúc chấm hợp lệ: đề, lời giải, đáp án; trắc nghiệm phải đủ 4 lựa chọn không trống/trùng và đáp án A–D.
- Khi lời giải ghi rõ `Đáp án: X` nhưng khóa đáp án là nhãn khác, app chặn phát hành.
- Cùng một hàng rào kiểm tra được dùng ở xem trước, duyệt, xuất đề và lượt học đã duyệt.

### Học sinh và giáo viên

- Luyện theo bài/chương/chuyên đề, giữa kỳ, cuối kỳ và thi thử THPT; thời lượng 45 hoặc 90 phút theo phạm vi.
- Hết giờ tự nộp bài.
- Công thức render bằng LaTeX/MathJax; PDF dùng Times New Roman và đã giới hạn bố cục để tránh lỗi ReportLab.
- Sau lượt làm, app phân tích theo chủ đề: dưới 60% củng cố nền tảng; 60–79% luyện chắc; từ 80% chuyển mức vận dụng/dạng khác.
- Kết quả theo chủ đề được lưu cho các lượt mới; học sinh có bản đồ kiến thức, giáo viên có tổng hợp theo học sinh/lớp.

### Điều hành kho

- Màn “An toàn & chất lượng” cho biết số lượng câu bị chặn theo nguyên nhân, các biến thể lỗi cụ thể, tình trạng liên kết dữ liệu và độ phủ chương trình.
- Độ phủ theo từng bài học lớp 10–12 phân biệt câu nguồn, câu đã duyệt, câu sẵn sàng.
- Hàng đợi phát triển ưu tiên: câu đã duyệt nhưng chưa phát hành → câu chữ đủ dữ kiện → câu cần xác minh hình/công thức → bài chưa có nguồn.
- Hàng tạo bản nháp trong “Kiểm duyệt kho đề” đã dùng thứ tự ưu tiên này thay vì thứ tự tệp.

## 4. Lỗi đáng chú ý đã xử lý

| Vấn đề | Cách xử lý |
| --- | --- |
| Thiếu hàm `has_ooxml_math`, `progress_stats`, `parsed_summary` | Khôi phục/đồng bộ API giữa app và module nguồn; thêm kiểm tra tự động. |
| Gemini trả JSON dạng danh sách hoặc cờ boolean dạng chuỗi | Chuẩn hóa dữ liệu AI trước khi dùng; không tự coi dữ liệu mơ hồ là an toàn. |
| Slider Streamlit lỗi khi chỉ còn 1 ảnh | Thay điều kiện biên để không tạo slider có min=max. |
| ReportLab `LayoutError` với công thức dài | Điều chỉnh render PDF và chia bố cục an toàn hơn. |
| Đề hiển thị `None`/thiếu công thức | Chặn bản nháp thiếu dữ kiện; công thức MathType hỏng phải được đọc lại hoặc chép tay. |
| Nhãn “Vận dụng cao” không được phân mức | Sửa chuẩn hóa tiếng Việt có dấu/không dấu. |
| Hai câu cùng nhãn trong lựa chọn duyệt bị mất một câu | Thêm hậu tố mã câu để giữ mọi lựa chọn. |
| Biến thể cũ có thể lọt qua lượt luyện dù thiếu dữ liệu | Dùng chung hàm kiểm tra phát hành ở mọi luồng. |
| Converter không mở nếu ổ E: tồn tại nhưng không ghi được | Thử quyền ghi trước và tự dùng thư mục dữ liệu cục bộ khi cần. |

## 5. Kiểm tra đã chạy

- Biên dịch Python cho `toan-ai-local/app.py` và `self_check.py`.
- `toan-ai-local/self_check.py`: kiểm tra ngân hàng, chấm điểm, parser, công thức MathType, cấu trúc biến thể, lộ trình thích nghi, độ phủ chương trình và liên kết dữ liệu.
- Các test của Math Document Converter: lõi lưu trữ, Parser, matching và nhật ký quyết định duyệt.
- `git diff --check` để kiểm tra khoảng trắng/lỗi định dạng patch.

Kết quả self-check gần nhất: `OK: candidates=4843, ready_multiple_choice=4`.

## 6. Giới hạn và rủi ro còn lại

- Kiểm tra cục bộ có thể phát hiện lỗi cấu trúc và mâu thuẫn đáp án rõ ràng, nhưng không thể chứng minh mọi lời giải Toán phức tạp là đúng. Giáo viên vẫn cần duyệt cuối, đặc biệt với hình học và câu có MathType.
- MathType/WMF bị chồng nét ngay từ file gốc cần nguồn rõ hơn hoặc chép lại thủ công; OCR không nên đoán.
- 5 biến thể sẵn sàng chưa đủ để tạo ngân hàng đề dài, đa dạng và cân bằng cho tất cả bài/chuyên đề.
- Chưa triển khai cloud/public. Khi triển khai phải tách kho đề, cơ sở dữ liệu, tài khoản người dùng và API key ra khỏi repository.

## 7. Kế hoạch phiên tiếp theo

1. Trong “An toàn & chất lượng”, xem hàng đợi phát triển và xử lý nhóm ưu tiên có dữ liệu chữ rõ trước.
2. Tạo bản nháp theo lô nhỏ, kiểm tra từng bản và phát hành dần biến thể an toàn.
3. Duyệt một nhóm MathType/hình mẫu để kiểm tra quy trình ảnh → công thức → bản nháp → phát hành.
4. Khi có đủ câu đã duyệt theo từng bài, kiểm thử một lượt học sinh hoàn chỉnh: chọn bài → làm → tự nộp → bản đồ kiến thức → lượt luyện tiếp.
5. Chỉ sau khi kho nội dung ổn định mới thiết kế triển khai cloud, phân quyền lớp học và quản lý chi phí API.

## 8. Quy tắc làm việc cần giữ

- Không tự hỏi lại các lựa chọn kỹ thuật nhỏ.
- Không ghi đè dữ liệu/câu đã duyệt hoặc thay đổi người dùng mà không có quyền rõ ràng.
- Không gọi API tính phí, triển khai công khai hoặc thay đổi tài khoản khi chưa được yêu cầu.
- Khi gặp lỗi: đọc log, xác định nguyên nhân, sửa và chạy kiểm tra lại.
- Sau mỗi thay đổi: kiểm tra đúng chức năng liên quan và cập nhật tài liệu tiến độ.
