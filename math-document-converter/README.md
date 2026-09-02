# Math Document Converter

Converter cục bộ dành cho kho tài liệu Toán. Đây là project độc lập với TrinhMath AI để việc OCR hàng loạt không làm ảnh hưởng app học sinh.

## Milestone 1–2 đã có

- Nhận PDF, DOCX và ảnh; hỗ trợ nhiều tệp hoặc quét cả thư mục qua đường dẫn cục bộ.
- PDF có chữ được trích trước và đánh dấu `SKIPPED`, không rasterize/OCR lại.
- Ảnh và PDF scan được đưa vào SQLite queue theo **từng trang**.
- Trạng thái `WAITING`, `PROCESSING`, `SUCCESS`, `FAILED`, `RETRY`; dừng app rồi mở lại vẫn tiếp tục được.
- Cache theo hash trang + thiết lập OCR: không OCR lại trang đã thành công.
- Pix2Text là provider mặc định. `AUTO` ưu tiên CUDA, 4GB VRAM mặc định chỉ xử lý 1 trang; nếu CUDA thiếu bộ nhớ, worker thử lại trang đó bằng CPU.
- Lưu Markdown, danh sách LaTeX và JSON phiên bản `1.0` vào `data/converter.db`.
- **Post-OCR Question Parser** đọc lại Markdown/LaTeX/direct text đã lưu, tách bản nháp câu hỏi theo từng tài liệu và không thay đổi OCR gốc.
- Bảo toàn raw OCR, LaTeX, trang nguồn và tham chiếu ảnh; hỗ trợ trắc nghiệm A/B/C/D, đúng/sai, trả lời ngắn, tự luận, đáp án công thức và câu nối qua trang.
- Lưu confidence, cờ cần xem lại và các đoạn OCR chưa gắn vào câu trong bảng SQLite riêng để có thể debug/reprocess.

## Cài và mở

1. Bấm đúp `CAI_DAT_CONVERTER.bat` một lần. Script tạo môi trường Python riêng, cài PyTorch CUDA và Pix2Text.
2. Bấm đúp `MO_CONVERTER.bat`.
3. Mở `http://localhost:8502` nếu trình duyệt không tự mở.

Lần OCR đầu tiên Pix2Text có thể tải model về máy; hãy dùng mạng ổn định và chờ quá trình này hoàn tất.

## Dùng với GTX 1650 4GB

1. Chọn 5–10 trang/ảnh để benchmark trước.
2. Ở **Hàng đợi OCR**, chọn `AUTO` và để **1 trang mỗi lượt**.
3. Nếu có lỗi CUDA, chọn `CPU` cho trang đó. Kết quả và trạng thái đã lưu trong SQLite nên không bị mất.
4. Chỉ sau khi đo được tốc độ/độ ổn định mới tăng số trang mỗi lượt.

Converter không gửi tài liệu tới Gemini hoặc bất cứ API nào. Mục tiêu của Milestone 1 là tạo dữ liệu cục bộ để TrinhMath AI dùng lại sau này, không OCR hai lần.

## Dùng Post-OCR Parser

Mở tab **Parser câu hỏi** rồi bấm **Chạy / chạy lại Parser cho OCR hiện có**. Parser luôn có thể chạy lại sau khi cải thiện luật nhận diện; nó thay thế bản nháp parser của cùng tài liệu, nhưng không sửa `ocr_results`.

Đặc biệt với ảnh chỉ là công thức hoặc hình rời không có đề bài, parser sẽ lưu chúng là **đoạn chưa gắn** thay vì tự đoán thành một câu hỏi. Các câu có confidence thấp, thiếu A/B/C/D, nghi nối trang hoặc có số câu bị nhảy đều được gắn cờ để duyệt.

## Chưa làm

- Trích DOCX/OMML hoàn chỉnh (Milestone 2).
- Chuyển LaTeX sang Word Equation/OMML.
- Liên kết ngữ nghĩa tự động giữa ảnh/công thức rời và câu Word đã tách trong TrinhMath; hiện phần này vẫn cần lớp bridge/duyệt kế tiếp để tránh gắn nhầm hình.
- Bounding box cho từng dòng/câu và trình chỉnh sửa trực quan kéo-thả.
- Hiển thị chỉ số CPU/RAM/VRAM theo thời gian thực.

## Kiểm tra lõi

```powershell
.venv\Scripts\python.exe test_core.py
```
