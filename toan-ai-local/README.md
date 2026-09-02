# TrinhMath AI

Ứng dụng học và quản lý ngân hàng câu hỏi Toán THPT, chạy trên chính laptop.

## Mở ứng dụng

1. Bấm đúp `MO_APP_TOAN.bat`.
2. Mở `http://localhost:8501` nếu trình duyệt chưa tự mở.
3. Khi không dùng nữa, đóng cửa sổ lệnh màu đen.

Không cần cài lại Python cho lần sử dụng bình thường. Thư mục `.venv` đã chứa môi trường chạy riêng của app.

## Đưa app sang máy khác

1. Chép **toàn bộ** thư mục `toan-ai-local` vào ổ cứng/USB (gồm cả `sources`, các tệp JSON và `results.db`).
2. Trên máy mới, bấm đúp `CAI_DAT_MAY_MOI.bat` **một lần**. Máy cần có Internet và Python 3.11 trở lên; nếu chưa có, file này sẽ báo rõ cách cài Python.
3. Khi hiện “CÀI ĐẶT XONG”, bấm `MO_APP_TOAN.bat` để mở app, rồi vào `http://localhost:8501`.

Không chỉ chép riêng file `MO_APP_TOAN.bat`: máy mới phải tạo môi trường chạy riêng ở bước 2.

## Quét OCR cục bộ trên máy mạnh (không dùng Gemini)

Chỉ thực hiện trên máy bạn được phép dùng và có dung lượng trống/mạng ổn định. Sau khi đã cài app trên máy đó, bấm `CAI_DAT_OCR_CUC_BO.bat` một lần. Script cài Pix2Text và kiểm tra xem PyTorch có nhìn thấy GPU CUDA hay không.

Sau đó mở app, vào **Góc cùng suy nghĩ AI** → **Quét OCR cục bộ bằng máy này** → **Bắt đầu OCR cục bộ toàn kho (Word + PDF)**. App đọc ảnh câu hỏi trong Word và PDF scan; kết quả được lưu sau từng ảnh/tệp trong chính thư mục app, không gửi lên Gemini. Kết quả OCR cục bộ luôn bị chặn khỏi đề học sinh cho đến khi được duyệt.

## Giáo viên làm gì?

1. Đăng nhập tài khoản Giáo viên.
2. Vào **Nhập kho đề** để thêm nhiều Word/PDF hoặc cả thư mục.
3. Vào **Phân tích kho đề** để tách câu, gắn nhãn và duyệt nội dung AI. PDF có chữ được đọc ngay tại máy; PDF chỉ gồm ảnh/quét sẽ được đánh dấu chờ OCR/AI để không đưa dữ liệu sai vào kho.
4. Vào **Kiểm tra chất lượng** để biết câu nào đang chờ OCR/AI, câu nào bị chặn và bao nhiêu câu đã được phép phát hành.
5. Chỉ câu đã duyệt mới được chuyển thành trắc nghiệm/trả lời ngắn và cho học sinh làm.
6. Vào **Ngân hàng đề** để xuất PDF; chọn **Kho câu đã duyệt** để không dùng đề mẫu.

## AI và dữ liệu

- Gemini chỉ được dùng khi giáo viên tự kết nối trong app; không dán khóa vào chat.
- Câu thiếu công thức/hình hoặc AI không chắc sẽ bị chặn, không tự đưa cho học sinh.
- Tài liệu nguồn và cơ sở dữ liệu nằm trên laptop. App tự sao lưu hằng ngày vào thư mục `backups`.
- Ở **Góc cùng suy nghĩ AI**, mục **Tự quét công thức còn thiếu** chạy nền: chỉ cần bấm một lần, app tự quét liên tục từng nhóm 3 ảnh và lưu tiến độ sau mỗi ảnh. Laptop cần còn bật và có Internet; có thể bấm dừng an toàn hoặc tiếp tục sau khi Gemini hết quota.

## Học sinh làm gì?

- Đăng nhập tài khoản Học sinh.
- Vào **Góc giải bài** khi cần học một bài riêng: nhập đề hoặc đọc từ ảnh, kiểm tra lại văn bản/công thức rồi mới xác nhận để nhận gợi ý. App không lấy kết quả OCR chưa được xác nhận để đưa cho AI giải.
- Trong Góc giải bài, **Gợi ý** chỉ mở từng gợi ý. Khi Gemini đã được kết nối, học sinh có thể nhập một bước đang làm để **Thầy AI kiểm tra bước này**; lời giải đầy đủ chỉ hiện khi chủ động bấm xem.
- Vào **Làm bài** để làm đề mẫu hoặc luyện các câu đã duyệt.
- Sau khi nộp, xem điểm, lời giải và gợi ý chủ đề cần ôn.

## Các giới hạn an toàn hiện tại

- Lời giải do Gemini hỗ trợ chưa phải là bằng chứng toán học tuyệt đối. Với hình học, bài thiếu hình/dữ kiện hoặc câu có kết quả bất thường, app luôn nhắc người học đối chiếu với giáo viên/lời giải chuẩn.
- Bộ kiểm chứng đại số bằng SymPy và nhiều cách giải sẽ là giai đoạn tiếp theo; app hiện không giả vờ đã kiểm chứng những nội dung chưa thể kiểm chứng.

## Khi cần cài lại môi trường

Chỉ dùng khi máy báo lỗi thiếu thư viện:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
