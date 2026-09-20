# TrinhMath AI — Tiến độ phát triển

_Cập nhật: 13/09/2026_

## Trạng thái hiện tại

- Kho đã lập chỉ mục: **387 tài liệu** Word/PDF.
- Câu ứng viên đã tách từ nguồn: **4.843 câu**.
- Kết quả đọc ảnh/công thức đã lưu cục bộ: **2.192 ảnh**; kết quả được tái sử dụng, không gửi lại AI khi không cần thiết.
- Ngân hàng đã duyệt: **7 câu nguồn**; **5 biến thể** đã phát hành an toàn cho học sinh.
- Bản nháp chờ kiểm duyệt: **36**, gồm **21 bản nháp cục bộ** (20 đáp số mới và 1 trắc nghiệm cũ). Tất cả bản nháp cục bộ đều bắt buộc được giáo viên đối chiếu với nguồn trước khi mở khóa bước duyệt; chưa có bản nào trong lô này được tự duyệt hoặc phát hành.
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
15. Tách các logic có rủi ro cao khỏi `app.py` thành module thuần có thể test độc lập: validation biến thể, chấm bài và học thích ứng. Hàm public cũ vẫn là lớp tương thích nên giao diện hiện tại không đổi hành vi.
16. Math Verifier V1 đã có cho phương trình, đạo hàm, nguyên hàm, tích phân xác định và đồng nhất thức khi dữ liệu đầu vào là biểu thức SymPy rõ ràng. Kết quả không chắc/hình học/chứng minh luôn là `INCONCLUSIVE` hoặc `UNSUPPORTED`, không được xem là đúng.
17. Đã thêm `AGENTS.md`, pytest và GitHub Actions không dùng dữ liệu riêng tư để các phiên tiếp theo có quy tắc làm việc và kiểm tra lặp lại được.
18. Đã đưa Math Verifier vào màn duyệt biến thể dưới dạng thao tác giáo viên có cấu trúc. Mỗi lần kiểm tra có audit trail; biến thể đã phát hành bị khóa không cho sửa âm thầm.
19. Đã thêm hàng xử lý A–D cho 4.843 candidate và dùng nhóm này để ưu tiên tạo bản nháp: A trước, sau đó B, C, D. Việc phân nhóm không thay nội dung hoặc trạng thái phát hành của câu.
20. Đã chạy lô cục bộ 20 câu trả lời ngắn thuộc nhóm A sau khi sao lưu dữ liệu. Parser trắc nghiệm cùng tiêu chuẩn không tạo trùng; tất cả bản nháp mới vẫn ở hàng giáo viên duyệt.
21. Đã tách `curriculum_coverage.py`: tính độ phủ bài học và hàng ưu tiên phát triển kho có 3 test độc lập; `app.py` giữ hàm tương thích để giao diện không đổi.
22. Rà mẫu lô cục bộ phát hiện việc “đủ trường” không đồng nghĩa nguồn còn đủ công thức/dữ kiện; một số nguồn có mất biến, LaTeX lệch hoặc đáp số không khớp với đề.
23. Thêm `source_quality.py` để phát hiện các cờ trên trước khi parser tạo bản nháp; nhóm A có cờ chất lượng nguồn được hạ về D. Hai parser cục bộ nay luôn yêu cầu đối chiếu giáo viên. Đã di trú an toàn 21 bản nháp cục bộ có sẵn về trạng thái cần đối chiếu, không xóa hay sửa nội dung gốc.
24. Thêm `source_review.py` và màn “Đối chiếu trước khi duyệt”: nguồn thô, bản nháp, trạng thái từng ảnh/MathType và các cờ chất lượng cùng hiện trong một lượt. Bản nháp cục bộ chỉ có thể mở khóa bước duyệt sau checkbox xác nhận đối chiếu; đó vẫn chưa phải phát hành cho học sinh.
25. Thêm hàng điều phối 21 nháp cục bộ và `local_review_workflow.py`: giáo viên có thể gắn cờ thiếu dữ kiện, công thức/hình không khớp hoặc sai lệch Toán kèm ghi chú; quyết định được lưu, có thể khôi phục và không đụng tệp nguồn/bản nháp gốc.
26. Đồng bộ `health_checks.audit_data_links()` với release validation: audit nay phát hiện biến thể được gắn trạng thái sẵn sàng nhưng có cấu trúc không hợp lệ hoặc kết quả Math Verifier không `VERIFIED`.
27. Math Verifier kiểm tra cú pháp đại số trước khi gọi SymPy: chỉ hàm Toán cho phép mới được parse; payload giống mã lệnh hoặc hàm lạ luôn trở thành `INCONCLUSIVE`.
28. Sau mỗi lượt “Luyện câu AI đã duyệt”, học sinh nay thấy ngay lộ trình theo chủ đề và mức luyện tiếp, dùng cùng quy tắc với luồng đề mẫu; thao tác này chỉ đọc kết quả vừa chấm, không đổi ngân hàng câu hỏi hay trạng thái phát hành.
29. Nháp cục bộ cùng một tệp nguồn nay được chặn theo lô khi kết quả đọc MathType đã xác nhận ảnh bị chồng nét/méo/lỗi và không thể đọc. Cờ này là dữ liệu dẫn xuất, tự bỏ qua mảnh đã được giáo viên chép lại và không sửa nguồn, OCR hay quyết định duyệt.
30. Màn chọn bản nháp ưu tiên câu cục bộ có thể đối chiếu nguồn trước, rồi mới đến nháp đủ điều kiện duyệt và các câu cần hình/công thức; câu bị chặn không còn là lựa chọn mở đầu của phiên mới.
31. Hàng đối chiếu nay gom nháp cục bộ theo tệp nguồn và cho phép giáo viên, sau khi xác nhận một lỗi đại diện, **gắn cờ cả lô**. Thao tác bỏ qua câu đã duyệt/cờ cũ, giữ nguyên nguồn/OCR/bản nháp và chỉ chặn duyệt — không có duyệt hay phát hành hàng loạt.

## Việc đang làm

- Dùng màn đối chiếu mới để kiểm duyệt từng bản nháp cục bộ an toàn, bắt đầu từ câu không có cờ nguồn và không cần ảnh.
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
5. Tạo bước review có kiểm soát để giáo viên gắn payload Math Verifier vào các câu có biểu thức rõ; chỉ khi xác minh được mới lưu `VERIFIED`.

## Nhật ký phiên gần nhất — 13/09/2026

- Đã rà lại đường đi từ biến thể tới học sinh để không có màn nào bỏ qua kiểm tra dữ liệu.
- Đã phát hiện và sửa lỗi chuẩn hóa nhãn tiếng Việt của mức độ nhận thức: `Vận dụng cao`, `Vận dụng`, `Thông hiểu`, `Nhận biết` nay được nhận diện đúng cả khi so khớp không dấu.
- Đã phát hiện kiểm tra độc lập chưa tạo bảng lưu kết quả theo chủ đề; bổ sung khởi tạo cơ sở dữ liệu trong `self_check.py`, không thay đổi dữ liệu học sinh có sẵn.
- Đã xử lý lỗi giao diện: các câu có cùng nhãn trong danh sách tạo bản nháp không còn bị ghi đè lựa chọn.
- Các kiểm tra đã chạy: biên dịch `app.py`/`self_check.py`, self-check toàn kho, kiểm tra liên kết dữ liệu, kiểm tra cấu trúc biến thể, kiểm tra parser và kiểm tra diff Git.
- Đợt kiến trúc tiếp theo: tạo `variant_validation.py`, `grading.py`, `adaptive_learning.py`, `math_verifier.py`; thêm 18 pytest độc lập và workflow CI. Self-check toàn kho tiếp tục đạt `candidates=4843, ready_multiple_choice=4`.
- Mở rộng đợt này: thêm `variant_review_service.py` với audit trail verifier và `candidate_triage.py` với A–D; bộ pytest tăng lên 26 test. Đã bắt một lỗi ghép triage sai vị trí trong `app.py` trước khi ảnh hưởng UI và thêm assertion chống tái phát vào self-check.
- Đợt tiếp theo: `curriculum_coverage.py` được tách và tổng pytest đạt 29. Tập trung lại vào kiểm duyệt 20 bản nháp nhóm A trước khi tạo thêm lô hoặc dùng AI trả phí.
- Bổ sung sau khi rà mẫu thực tế: tổng pytest đạt 31; không còn lối duyệt trực tiếp cho bản nháp parser cục bộ. Giáo viên cần đối chiếu nguồn, sau đó mới mở khóa nút duyệt ngân hàng ở bước kế tiếp.
- Màn đối chiếu nguồn–bản nháp, hàng điều phối và quyết định gắn cờ/khôi phục đã hoàn thành; tổng pytest đạt **36**. CI cũng biên dịch các module mới trước khi chạy test.
- Bổ sung regression test cho data audit và parser an toàn Math Verifier; tổng pytest đạt **40**. Không thay đổi dữ liệu nguồn, bản nháp hoặc trạng thái phát hành hiện có.
- Đồng bộ phần chẩn đoán sau lượt đề mẫu và lượt “Luyện câu AI đã duyệt”; thêm kiểm tra luồng chấm → lộ trình theo chủ đề; tổng pytest hiện là **41 test đạt**. Không thay đổi dữ liệu nguồn, bản nháp hoặc trạng thái phát hành.
- Thêm hàng rào chặn theo lô cho lỗi MathType đã được xác nhận không thể đọc; thêm kiểm tra snapshot, phân loại cả lô nguồn, import màn kiểm duyệt và thứ tự chọn bản nháp; tổng pytest hiện là **45 test đạt**. Không thay đổi dữ liệu nguồn, bản nháp hoặc trạng thái phát hành.
- Bổ sung bảng gom nháp cục bộ theo tệp nguồn và thao tác gắn cờ cả lô có xác nhận giáo viên; câu đã duyệt/cờ cũ được bỏ qua, không có duyệt hàng loạt. Cơ chế nạp lại mô-đun khi Streamlit rerun cũng được bổ sung để không giữ API cũ. Tổng pytest hiện là **47 test đạt**; self-check tiếp tục `candidates=4843, ready_multiple_choice=4`.
- Sửa lỗi Poppler đặt ảnh trang theo hậu tố hai chữ số (`-01.png`) trong khi app chỉ nhận ba chữ số (`-001.png`), dẫn tới thông báo render thất bại dù ảnh đã được tạo. App nay nhận cả hai tên tệp (và chỉ nhận ảnh đủ kích thước); thêm regression test trước khi hiển thị lại ảnh trang nguồn. Tổng pytest hiện là **49 test đạt**.

## Giới hạn đang biết

- App chỉ có thể kiểm tra **cấu trúc** và một số mâu thuẫn đáp án rõ ràng; tính đúng đắn Toán học của mọi lời giải vẫn phải do giáo viên đối chiếu với nguồn hoặc duyệt AI có kiểm soát.
- Công thức MathType/WMF bị hỏng ngay từ tài liệu gốc không thể được làm rõ chỉ bằng OCR; cần bản Word/PDF rõ hơn hoặc giáo viên chép lại công thức.
- Số câu sẵn sàng hiện còn nhỏ, vì vậy chưa nên coi đây là ngân hàng đủ để tạo nhiều đề kiểm tra dài, dù luồng tạo/luyện đề đã hoạt động.
- Math Verifier V1 không nhận LaTeX/raw OCR hoặc đề tự do làm bằng chứng. Cần một bước chuyển cấu trúc có review; không tự dùng AI để lấp phần dữ kiện thiếu.

## Nhật ký tích hợp workflow — 19/09/2026

- Đã đánh giá gói ngoài “GPT nghĩ – Codex làm” như công cụ Node/TypeScript có bridge MCP, OAuth và Cloudflare tunnel. Không tích hợp source, dependency, script hay cấu hình của gói vào app.
- Chỉ chuẩn hóa quy ước bàn giao và bộ nhớ dự án tại `ai/`; không thay đổi code, database, raw OCR, nguồn, dữ liệu học sinh hoặc trạng thái review/phát hành.
- Bổ sung ignore cho `question_candidates_triaged.json` vì đây là dữ liệu kho đề dẫn xuất cục bộ, không phù hợp GitHub.
- Xác minh lại an toàn: self-check trong bản sao tạm cô lập đạt `candidates=4843, ready_multiple_choice=4`; 49 pytest của `toan-ai-local` và bốn test của Converter đều PASS.

## Nhật ký provider offline — 20/09/2026

- Thêm `ai_provider.py` và `model_router.py` độc lập; không sửa `app.py`, database, raw OCR, nguồn, question bank hay trạng thái review/phát hành.
- DeepSeek mặc định OFF; hợp đồng có FAST/PRO logical aliases, guard dry-run/timeout/retry/max-items/task id/usage metadata, Fake provider và fail-closed khi disabled, thiếu key hoặc output không hợp lệ. Chưa có HTTP transport, API key hay API call.
- Router chỉ chọn PRO theo reason code rõ ràng (complex, hai lần FAST fail, critical review); vision đi FAST theo capability hiện tại.
- Đã thêm 10 regression tests offline. Full suite đạt **59 pytest**; self-check chạy trong staging database riêng đạt `candidates=4843, ready_multiple_choice=4`; bốn converter checks và compile/import đều PASS.
- Rủi ro/bước kế tiếp: chưa được bật provider hay chạy pilot. Chỉ sau review PR, user authorization về key/budget/data scope và golden set sanitized mới được thiết kế transport/pilot.

## Nhật ký transport guardrails — 20/09/2026

- Mở rộng `ai_provider.py` bằng injected transport contract, Fake transport thuần in-memory và `UrllibDeepSeekTransport` explicit. Không có default transport/dependency mới, không gọi mạng, không dùng key thật và không nối vào `app.py`.
- Mọi request chạy ngoài trong tương lai phải qua allow-list task class, mapping FAST/PRO, max timeout/retry/item/payload, redaction metadata và chặn payload có khóa nhạy cảm. HTTP/response lỗi hoặc JSON hỏng đều fail closed; retry bị giới hạn.
- Bổ sung regression tests; tổng **64 pytest** PASS (15 test provider/router/transport). Self-check staging cô lập và bốn converter checks cũng PASS; không sửa database, OCR, nguồn hay trạng thái duyệt/phát hành.

## Nhật ký pilot preparation — 20/09/2026

- Thêm `deepseek_pilot.py` riêng khỏi `app.py`: policy OFF/kill switch ON, max task/item/retry/timeout/payload/token budget, router FAST/PRO reason code và audit record không dump input nguồn.
- Fixture test chỉ gồm hai prompt synthetic vô danh. Runner không đọc source/OCR/database/question bank, không đọc key thật và không mở network trong CI.
- Thêm test cho pilot OFF/dry-run/config thiếu/budget/item/payload/token/secret/malformed response/usage/routing/fake transport. Tổng **72 pytest** PASS (23 test provider/router/transport/pilot); self-check staging và converter suite PASS.
- Chỉ sau PR/CI xanh và branch sạch mới dừng xin key/data scope/budget cho request thật đầu tiên.

## Nhật ký M2 Data Factory Slice 1 — 20/09/2026

- Thêm `candidate_classification.py` và launcher báo cáo chỉ đọc: mỗi candidate nhận đúng một trong ba kết quả `MATCHED`, `REVIEW_REQUIRED`, `INVALID`, kèm evidence source-match, structural/source-quality, duplicate và confidence/reason code. Không có nhánh nào tự chuyển `APPROVED` hoặc `RELEASED`.
- Source match dùng trọng số công khai, có kiểm thử cho source trùng/không rõ, xung đột đáp án, duplicate, dữ kiện thiếu, hình/công thức cần đối chiếu và Math Verifier chưa kết luận. Mọi mơ hồ đi về `REVIEW_REQUIRED`; lỗi cấu trúc thiết yếu/parse không khôi phục/mâu thuẫn Toán là `INVALID`.
- Report chỉ nhận JSON candidate/source metadata được chỉ định rõ và fixture test hoàn toàn synthetic; không đọc DB, OCR/source gốc hay dữ liệu học sinh, không ghi đè input và không gọi API. Full suite hiện đạt **87 pytest PASS**.
- Đồng thời sửa guardrail injection môi trường: `{}` trong test/runner nay là môi trường rỗng thực sự, không kế thừa key/feature flag từ PowerShell đang chạy.

## Nhật ký M2 Integration Pack — 20/09/2026

- Thêm adapter schema local, aggregate runner và hàng kiểm duyệt M2 trên đúng màn kiểm duyệt hiện có. Lô local 4.843 candidate chỉ được đọc; mọi candidate nhận outcome và không có candidate nào được duyệt/phát hành tự động.
- Catalog nguồn hiện chỉ có metadata cấp tệp nên 4.843 candidate được giữ ở `REVIEW_REQUIRED` thay vì suy diễn khớp câu. Báo cáo Git chỉ lưu aggregate không chứa nội dung nguồn/OCR/dữ liệu học sinh.
- Hàng M2 tái dùng source snapshot và workflow gắn cờ nháp cục bộ; giáo viên có thể lọc outcome/lý do/nguồn/bài, xem provenance/evidence và chỉ gắn cờ có thể khôi phục.
