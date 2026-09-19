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
- Có **36 bản nháp** đang chờ kiểm duyệt. Trong đó có 21 bản do parser cục bộ tạo (20 câu trả lời ngắn và 1 trắc nghiệm cũ); tất cả đều đã được chuyển về trạng thái **bắt buộc đối chiếu nguồn bởi giáo viên**. Chúng chưa được đưa vào ngân hàng đã duyệt hoặc phát hành cho học sinh.

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
- Data audit cũng dùng chính hàng rào phát hành này, nên phát hiện cả biến thể đã gắn trạng thái sẵn sàng nhưng có lựa chọn trùng hoặc Math Verifier chưa `VERIFIED`.
- Hàng rào kiểm tra biến thể, chấm bài và lộ trình thích ứng đã được tách thành các module thuần, giữ API cũ của app để không làm vỡ màn hình hiện có.
- Math Verifier V1 chỉ kiểm tra các khẳng định có cấu trúc bằng SymPy: thế nghiệm phương trình, đạo hàm, nguyên hàm, tích phân xác định và đồng nhất thức. Kết quả luôn là `VERIFIED`, `CONTRADICTED`, `INCONCLUSIVE` hoặc `UNSUPPORTED`.
- Trước khi SymPy nhận payload, Math Verifier chỉ chấp nhận cú pháp đại số và các hàm Toán được cho phép; chuỗi giống mã lệnh hoặc hàm chưa hỗ trợ trả `INCONCLUSIVE`.
- Nếu một biến thể đã có kết quả Math Verifier mà là `CONTRADICTED`, `INCONCLUSIVE` hoặc `UNSUPPORTED`, app chặn phát hành; biến thể lịch sử chưa có kết quả này không bị tự thay đổi.

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
- Candidate hiện được phân nhóm A–D chỉ để xử lý theo lô an toàn: A (chữ/đáp án/lời giải rõ), B (thiếu lời giải), C (hình/MathType cần xác minh), D (nguồn hoặc ranh giới chưa đủ). Màn chất lượng hiển thị hàng này và hàng tạo nháp ưu tiên A trước.
- Màn duyệt bản nháp nay đặt nguồn thô và bản nháp cạnh nhau, liệt kê từng mảnh ảnh/MathType, trạng thái OCR và các cờ mất dữ kiện. Với bản nháp cục bộ, giáo viên phải tích xác nhận đã so đề, đáp án và lời giải trước khi bước duyệt ngân hàng có thể mở khóa.
- Hàng đối chiếu nguồn phân loại riêng bản nháp cục bộ: có thể đối chiếu ngay, cần ảnh/MathType, bị chặn do nguồn hoặc đã được giáo viên gắn cờ. Quyết định gắn cờ có thể khôi phục, lưu thời gian/lý do và không xóa dữ liệu.
- Giáo viên có thể chạy Math Verifier trên một biến thể nháp bằng biểu thức SymPy có cấu trúc. Claim, kết quả, thời gian và lịch sử được lưu riêng; biến thể đã phát hành không thể bị sửa âm thầm qua thao tác này.
- Đã chạy một lô cục bộ 20 câu trả lời ngắn nhóm A sau khi sao lưu dữ liệu trong ngày. Lô trắc nghiệm cùng tiêu chuẩn không tạo thêm bản nháp vì mẫu khớp duy nhất đã tồn tại; hệ thống không tạo trùng để tăng số lượng giả tạo. Việc xem mẫu sau đó phát hiện nguồn có thể mất công thức hoặc sai đáp số dù bề ngoài đủ trường, nên không được xem lô này là nguồn đã xác minh.
- Tính độ phủ chương trình và hàng đợi phát triển kho đã được tách khỏi `app.py` thành module thuần. App chỉ cung cấp metadata/cờ an toàn; module không đọc hoặc sửa file dữ liệu.
- Sau lượt đề mẫu hoặc “Luyện câu AI đã duyệt”, học sinh nhận cùng một chẩn đoán theo chủ đề và mức luyện tiếp; phần này chỉ đọc kết quả đã chấm, không tự đổi ngân hàng hay phát hành câu.
- Khi kết quả đọc MathType xác nhận mảnh ảnh bị chồng nét/méo/lỗi và không thể đọc, app chặn theo lô các nháp cục bộ của cùng tệp nguồn. Lô chỉ quay lại hàng đối chiếu khi có công thức giáo viên chép lại hoặc nguồn rõ hơn.
- Danh sách chọn bản nháp ưu tiên câu có thể đối chiếu nguồn, nên không mở mặc định một câu thiếu dữ kiện khi vẫn còn câu sạch hơn trong hàng.
- Giáo viên có thể xem các nháp cục bộ được gom theo tệp nguồn. Sau khi kiểm tra lỗi đại diện và tích xác nhận, họ có thể gắn cờ cả lô để chặn duyệt; thao tác bỏ qua câu đã duyệt/cờ cũ, không xóa nguồn, OCR hay bản nháp, và không có đường duyệt/phát hành hàng loạt.
- Sửa renderer trang nguồn: một số Poppler trên Windows tạo tệp `-01.png` thay vì `-001.png`; app nay nhận cả hai hậu tố (chỉ khi tệp ảnh đủ kích thước), nên không còn báo render PDF thất bại khi ảnh đã được tạo. Tổng pytest hiện là **49 test đạt**.

## 4. Lỗi đáng chú ý đã xử lý

| Vấn đề | Cách xử lý |
| --- | --- |
| Thiếu hàm `has_ooxml_math`, `progress_stats`, `parsed_summary` | Khôi phục/đồng bộ API giữa app và module nguồn; thêm kiểm tra tự động. |
| Gemini trả JSON dạng danh sách hoặc cờ boolean dạng chuỗi | Chuẩn hóa dữ liệu AI trước khi dùng; không tự coi dữ liệu mơ hồ là an toàn. |
| Slider Streamlit lỗi khi chỉ còn 1 ảnh | Thay điều kiện biên để không tạo slider có min=max. |
| ReportLab `LayoutError` với công thức dài | Điều chỉnh render PDF và chia bố cục an toàn hơn. |
| Đề hiển thị `None`/thiếu công thức | Chặn bản nháp thiếu dữ kiện; công thức MathType hỏng phải được đọc lại hoặc chép tay. |
| Parser cục bộ nhầm câu có văn bản đủ trường là nguồn đáng tin | Thêm `source_quality.py` phát hiện dấu mất biến/công thức, LaTeX không cân và lời giải rỗng; các parser cục bộ từ nay luôn cần giáo viên đối chiếu. Đã di trú 21 bản nháp cục bộ cũ về trạng thái khóa, không xóa dữ liệu. |
| Nhãn “Vận dụng cao” không được phân mức | Sửa chuẩn hóa tiếng Việt có dấu/không dấu. |
| Hai câu cùng nhãn trong lựa chọn duyệt bị mất một câu | Thêm hậu tố mã câu để giữ mọi lựa chọn. |
| Biến thể cũ có thể lọt qua lượt luyện dù thiếu dữ liệu | Dùng chung hàm kiểm tra phát hành ở mọi luồng. |
| Converter không mở nếu ổ E: tồn tại nhưng không ghi được | Thử quyền ghi trước và tự dùng thư mục dữ liệu cục bộ khi cần. |

## 5. Kiểm tra đã chạy

- Biên dịch Python cho `toan-ai-local/app.py` và `self_check.py`.
- `toan-ai-local/self_check.py`: kiểm tra ngân hàng, chấm điểm, parser, công thức MathType, cấu trúc biến thể, lộ trình thích nghi, độ phủ chương trình và liên kết dữ liệu.
- Các test của Math Document Converter: lõi lưu trữ, Parser, matching và nhật ký quyết định duyệt.
- `git diff --check` để kiểm tra khoảng trắng/lỗi định dạng patch.
- Pytest không phụ thuộc kho dữ liệu riêng: kiểm tra validation biến thể, lộ trình thích ứng, chấm bài và Math Verifier V1. Kết quả gần nhất: **18 passed**.
- Bộ pytest hiện có **36 test đạt**, bao gồm audit trail Math Verifier, phân nhóm A–D, độ phủ chương trình, quy tắc chất lượng nguồn, snapshot đối chiếu và các chuyển trạng thái gắn cờ/khôi phục; self-check cũng xác nhận tổng các nhóm A–D bằng đúng số candidate.
- Bổ sung regression test cho data audit và parser an toàn của Math Verifier; tổng pytest hiện là **40 test đạt**.
- Bổ sung regression test ghép kết quả chấm với lộ trình theo chủ đề để hai luồng làm bài không bị lệch hướng dẫn; tổng pytest hiện là **41 test đạt**.
- Bổ sung kiểm tra hồi quy cho cờ MathType chồng nét, chặn theo lô nguồn, import màn kiểm duyệt và thứ tự chọn bản nháp; tổng pytest hiện là **45 test đạt**.
- Bổ sung kiểm tra hồi quy cho việc gom theo tệp nguồn và gắn cờ cả lô có xác nhận giáo viên; câu đã duyệt/cờ cũ không bị ghi đè. App cũng nạp lại module kiểm duyệt khi Streamlit rerun để tránh giữ API cũ. Tổng pytest hiện là **47 test đạt**; self-check toàn kho tiếp tục đạt `candidates=4843, ready_multiple_choice=4`.
- Đã thêm GitHub Actions chỉ chạy compile và test không cần khóa API, database, OCR image hay tài liệu nguồn.

Kết quả self-check gần nhất: `OK: candidates=4843, ready_multiple_choice=4`.

## 6. Giới hạn và rủi ro còn lại

- Kiểm tra cục bộ có thể phát hiện lỗi cấu trúc và mâu thuẫn đáp án rõ ràng, nhưng không thể chứng minh mọi lời giải Toán phức tạp là đúng. Giáo viên vẫn cần duyệt cuối, đặc biệt với hình học và câu có MathType.
- MathType/WMF bị chồng nét ngay từ file gốc cần nguồn rõ hơn hoặc chép lại thủ công; OCR không nên đoán.
- 5 biến thể sẵn sàng chưa đủ để tạo ngân hàng đề dài, đa dạng và cân bằng cho tất cả bài/chuyên đề.
- Math Verifier V1 chưa đọc LaTeX hay văn bản đề tự do. Nó chỉ nhận payload biểu thức SymPy do service/giáo viên cung cấp rõ ràng; hình học, chứng minh và dữ kiện mơ hồ luôn cần giáo viên duyệt.
- Chưa triển khai cloud/public. Khi triển khai phải tách kho đề, cơ sở dữ liệu, tài khoản người dùng và API key ra khỏi repository.

## 7. Kế hoạch phiên tiếp theo

1. Bổ sung service/phiên kiểm duyệt để giáo viên gắn một payload Math Verifier có cấu trúc vào câu phù hợp; không tự suy diễn từ văn bản tự do.
2. Trong “An toàn & chất lượng”, giáo viên đối chiếu lần lượt các bản nháp cục bộ với tệp gốc; chỉ các bản không có cờ mất dữ kiện mới được mở khóa cho bước duyệt riêng biệt.
3. Duyệt một nhóm MathType/hình mẫu để kiểm tra quy trình ảnh → công thức → bản nháp → phát hành.
4. Khi có đủ câu đã duyệt theo từng bài, kiểm thử một lượt học sinh hoàn chỉnh: chọn bài → làm → tự nộp → bản đồ kiến thức → lượt luyện tiếp.
5. Chỉ sau khi kho nội dung ổn định mới thiết kế triển khai cloud, phân quyền lớp học và quản lý chi phí API.

## 8. Quy tắc làm việc cần giữ

- Không tự hỏi lại các lựa chọn kỹ thuật nhỏ.
- Không ghi đè dữ liệu/câu đã duyệt hoặc thay đổi người dùng mà không có quyền rõ ràng.
- Không gọi API tính phí, triển khai công khai hoặc thay đổi tài khoản khi chưa được yêu cầu.
- Khi gặp lỗi: đọc log, xác định nguyên nhân, sửa và chạy kiểm tra lại.
- Sau mỗi thay đổi: kiểm tra đúng chức năng liên quan và cập nhật tài liệu tiến độ.
- `AGENTS.md` ở gốc repository là bản hướng dẫn bền vững cho các phiên Codex sau: đọc trước khi sửa và không bỏ qua pipeline kiểm duyệt.

## 9. Tích hợp quy trình GPT → Codex — 19/09/2026

- Đã kiểm kê riêng gói “GPT nghĩ – Codex làm” tại `E:\skill\codex-with-chatgpt-main\codex-with-chatgpt-main`. Đây là một ứng dụng Node/TypeScript độc lập: bridge MCP chỉ-đọc, OAuth/pairing và Cloudflare tunnel; không phải thành phần của hai app TrinhMath.
- Không sao chép source, config, script, dependency, test, tunnel hay OAuth của gói vào repository. Chỉ tiếp nhận mô hình bàn giao có kiểm soát bằng các tài liệu `ai/PROJECT_STATE.md`, `ai/TASK_QUEUE.md`, `ai/GPT_TO_CODEX.md`, `ai/CHANGELOG_AI.md` và mẫu handoff.
- Giữ nguyên `ai/ARCHITECTURE.md` và `ai/AI_RULES.md` đã có vì chúng phản ánh đúng kiến trúc/giới hạn hiện tại. Bổ sung ignore cho `toan-ai-local/question_candidates_triaged.json`, dữ liệu dẫn xuất cục bộ không phù hợp GitHub.
- Kiểm tra 19/09/2026: self-check chạy trên bản sao tạm cô lập PASS (`candidates=4843, ready_multiple_choice=4`); 49 pytest của `toan-ai-local`, bốn script test của `math-document-converter` và compile/import Python đều PASS. Không dùng API trả phí và không sửa database, raw OCR, nguồn hoặc dữ liệu học sinh.

## 10. Checkpoint provider offline — 20/09/2026

- Workflow active được chuẩn hóa thành GPT → Codex → DeepSeek FAST/PRO. Qwen không nằm trong roadmap/provider active; không có Qwen adapter hay task phụ thuộc nó.
- Bổ sung hai module thuần `toan-ai-local/ai_provider.py` và `toan-ai-local/model_router.py`, tách khỏi `app.py`. Provider có feature flag OFF mặc định, aliases FAST/PRO có mapping cấu hình, Fake provider, dry-run/cost guard metadata và fail-closed khi disabled/missing key/malformed output.
- Không có HTTP client, API key, API call, C2C, model install hoặc thay đổi dữ liệu/content pipeline. Vì vậy app hiện hữu giữ nguyên hành vi khi provider OFF.
- Thêm 10 test offline. Toàn bộ `toan-ai-local` đạt **59 pytest**; self-check staging cô lập đạt `candidates=4843, ready_multiple_choice=4`; converter core/parser/matching/review-storage và compile/import đều PASS.
- Bước sau cần review PR/CI. Bất kỳ transport, key, pilot hoặc external data transfer nào đều dừng xin quyền riêng.
