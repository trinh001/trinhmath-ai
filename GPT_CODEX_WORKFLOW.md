# Workflow GPT–Codex cho TrinhMath AI

_Thiết lập: 14/09/2026 · Phạm vi: `toan-ai-local` và `math-document-converter`_

## Chế độ khuyến nghị: GPT điều phối → Codex thực thi

Bạn trao đổi tự do với một chat GPT riêng; chat đó giữ toàn bộ ngữ cảnh về ý tưởng, lựa chọn và thay đổi yêu cầu. Khi đã chốt một việc, GPT tạo một **gói bàn giao ngắn** cho Codex. Codex chỉ đọc gói này và repository, sau đó thực thi, test và báo lại.

Đây là cách giảm context/token ở Codex mà vẫn để GPT là nơi bạn trao đổi. Nó không phải liên kết tự động giữa hai chat: một chat không thể âm thầm theo dõi hoặc tự gửi lệnh sang chat khác. Mỗi việc cần một lần chuyển gói bàn giao vào chat Codex.

### Thiết lập một lần trong chat GPT điều phối

Dán nguyên khối sau vào chat GPT bạn dùng để trao đổi:

```text
Bạn là GPT điều phối cho project TrinhMath AI. Tôi trao đổi ý tưởng với bạn;
không tự viết code hoặc giả định rằng bạn có quyền sửa repository.

Khi tôi nói “chuyển cho Codex”, hãy chỉ xuất một khối CODEX_HANDOFF tối đa
180 từ, không giải thích thêm. Khối phải gồm: mục tiêu; phạm vi; điều không
được đổi; tiêu chí hoàn thành; kiểm tra cần chạy; rủi ro/quyết định còn mở.
Không đưa khóa API, OCR nguồn, database, dữ liệu học sinh, nội dung câu hỏi
chưa duyệt hoặc lời giải tự suy đoán vào khối. Nếu dữ liệu/công thức mơ hồ,
nêu rõ BLOCK + REQUIRE TEACHER REVIEW.
```

Sau đó bạn chỉ cần copy khối `CODEX_HANDOFF` GPT trả ra và gửi vào chat Codex. Codex nhận ít context hơn nhiều so với toàn bộ đoạn brainstorm nhưng vẫn có lệnh thực thi rõ ràng.

### Cách Codex nhận lệnh

Gửi gói từ GPT kèm đúng một câu:

```text
Đây là CODEX_HANDOFF từ GPT điều phối. Hãy thực thi đúng phạm vi; không mở
rộng yêu cầu. Nếu thiếu quyết định an toàn, dừng ở kế hoạch/rủi ro thay vì đoán.
```

Codex phản hồi theo định dạng: file đã đổi, kiểm tra đã chạy, kết quả, rủi ro còn lại và bước cần giáo viên/người dùng quyết định. Mỗi tin nhắn ở GPT vẫn dùng token GPT; phía Codex chỉ dùng token cho gói bàn giao và công việc kỹ thuật, thay vì toàn bộ lịch sử trao đổi.

## Mục tiêu

GPT giúp làm rõ yêu cầu, nêu rủi ro và duyệt kết quả. Codex làm việc trực tiếp trong repository: đọc ngữ cảnh, sửa nhỏ nhất cần thiết, kiểm tra và báo cáo diff. Giáo viên vẫn là người ra quyết định duyệt nội dung Toán và phát hành cho học sinh.

```
Trao đổi ý tưởng / sự cố với GPT
        │
        ▼
GPT: làm rõ mục tiêu, tiêu chí xong, rủi ro → CODEX_HANDOFF ngắn
        │
        ▼
Codex: đọc gói → khảo sát → kế hoạch/sửa có kiểm soát → test
        │
        ▼
GPT + người dùng: review diff, quyết định tiếp tục / điều chỉnh
        │
        ▼
Giáo viên: review nội dung → approved → release (nếu đủ điều kiện)
```

Không đưa khóa API, database, tài liệu nguồn, ảnh OCR hoặc dữ liệu học sinh vào chat. Không coi kết quả GPT/Codex là bằng chứng để tự duyệt hay tự phát hành câu hỏi.

## Phân vai rõ ràng

| Vai trò | Chịu trách nhiệm | Không được tự làm |
| --- | --- | --- |
| GPT | Chuyển ý tưởng thành yêu cầu rõ ràng; phân tích lựa chọn; review theo tiêu chí sản phẩm | Đoán dữ kiện OCR/MathType, phê duyệt nội dung Toán thay giáo viên |
| Codex | Đọc `AGENTS.md` và tài liệu dự án; thực hiện thay đổi nhỏ nhất; thêm/running test; báo cáo file, test, rủi ro | Gọi API mất phí, commit bí mật, ghi đè dữ liệu, tự phát hành nội dung |
| Giáo viên | Đối chiếu nguồn, công thức, lời giải và đáp án; quyết định review/approval/release | Ủy quyền bước duyệt cuối cho AI |

## Chu trình cho một thay đổi

### 1. Viết yêu cầu cho GPT

Dùng mẫu sau trước khi yêu cầu Codex sửa code:

```text
Mục tiêu: <hành vi cần có hoặc lỗi cần sửa>.
Phạm vi: <app/module/màn hình liên quan>.
Không được: <dữ liệu/luồng không được đổi>.
Hoàn thành khi: <kết quả quan sát được + test cần chạy>.
Rủi ro dữ liệu/nội dung: <nếu có>.
```

Với việc lớn, yêu cầu GPT/Codex lập kế hoạch trước, gồm: file dự kiến đổi, tương thích ngược, test, rollback và điểm cần người dùng quyết định. Không yêu cầu viết code trong bước này.

### 2. Giao việc cho Codex

Mẫu thực thi:

```text
Đọc AGENTS.md, PROJECT_REPORT_2026-09-13.md, PROGRESS.md và test liên quan.
Hãy <thay đổi cụ thể> trong <phạm vi>.
Giữ nguyên dữ liệu nguồn, raw OCR, history review và API public hiện có.
Không gọi dịch vụ trả phí hoặc phát hành nội dung.
Xong khi: <tiêu chí>.
Hãy chạy <lệnh test> và trả về file đã đổi, kết quả test, rủi ro còn lại.
```

Ví dụ sửa logic thuần:

```text
Đọc AGENTS.md và test liên quan. Sửa lỗi <mô tả tái hiện> trong
toan-ai-local/<module>. Giữ tương thích API. Thêm regression test không dùng
dữ liệu riêng tư, chạy pytest cho file test đó và git diff --check. Không sửa
question_bank.json, results.db hoặc thay đổi trạng thái phát hành.
```

### 3. Kiểm tra bắt buộc của Codex

Codex phải làm theo thứ tự: tái hiện/đọc log → xác định nguyên nhân → sửa tối thiểu → thêm regression test (nếu là lỗi) → chạy kiểm tra liên quan → rà diff.

Mức kiểm tra tối thiểu:

| Loại thay đổi | Kiểm tra tối thiểu |
| --- | --- |
| Module thuần ở `toan-ai-local` | `pytest` cho test liên quan, sau đó `git diff --check` |
| Luồng app/SQLite/dữ liệu | test liên quan + `self_check.py` khi an toàn trên bản sao/dữ liệu cục bộ đã được phép |
| `math-document-converter` | test script liên quan, không OCR lại kho chỉ để test |
| Chỉ tài liệu/workflow | đọc lại file thay đổi + `git diff --check` |

Không coi `INCONCLUSIVE` hoặc `UNSUPPORTED` từ Math Verifier là đã kiểm chứng. Dữ liệu mơ hồ luôn ở trạng thái `BLOCK + REQUIRE TEACHER REVIEW`.

### 4. Review trước khi chấp nhận

Yêu cầu GPT/Codex trả lời ngắn theo checklist này:

- Hành vi nào đã đổi và file nào tạo/sửa?
- Có kiểm tra nào đã chạy, kết quả là gì?
- Có thay đổi schema, dữ liệu, API public, trạng thái review/release hay không?
- Có đường nào đưa OCR/draft chưa duyệt tới học sinh không?
- Rủi ro còn lại và bước con người cần làm là gì?

Chỉ sau review mới commit. Giữ mỗi commit một mục đích; không trộn refactor, migration và thay đổi nội dung trong cùng một commit.

## Luồng riêng cho dữ liệu câu hỏi

GPT/Codex chỉ có thể hỗ trợ tạo bản dẫn xuất hoặc kiểm tra cấu trúc. Luồng bắt buộc vẫn là:

```
Nguồn → Parser/OCR → Candidate → Draft → Structural validation
      → Math verification → Teacher review → Approved question
      → Student variant → Release validation → Luyện tập
```

Các điều kiện dừng ngay:

- thiếu đề, lời giải hoặc đáp án; `None`/`null`; ghi chú OCR;
- công thức/hình/rìa câu không rõ; phương án trống, trùng hoặc không đủ bốn;
- nhãn đáp án sai hoặc mâu thuẫn với lời giải;
- kết quả Math Verifier không phải `VERIFIED` khi câu đã có verifier result.

Trong các trường hợp trên, Codex chỉ được ghi nhận cờ/rủi ro hoặc tạo đường review; không sửa ngầm dữ liệu nguồn và không phát hành.

## Nhịp làm việc khuyến nghị

- Một chat Codex cho một mục tiêu kết thúc rõ ràng: một bug, một lát refactor, một review hoặc một tài liệu.
- Việc phức tạp: dùng Plan trước, rồi thực thi theo từng lát nhỏ có test.
- Khi cùng một prompt/checklist lặp lại nhiều lần: đóng gói thành skill; khi workflow đã ổn định và thực sự cần theo lịch: mới tạo automation.
- Với việc chạm dữ liệu thật hoặc cùng file đang sửa: làm tuần tự. Chỉ tách song song các việc độc lập như khảo sát, test hoặc review.

## Lệnh bắt đầu phiên

```text
Hãy bắt đầu bằng cách tóm tắt pipeline, quy tắc an toàn và trạng thái Git hiện tại.
Không sửa gì trước khi nêu file/test liên quan. Nếu yêu cầu có thể làm thay đổi
dữ liệu, phát hành câu hỏi, API trả phí hoặc triển khai công khai, dừng và nêu
quyết định cần người dùng/giáo viên xác nhận.
```

## Giới hạn hiện tại

Workflow này điều phối công việc, không thay thế quyền truy cập hay phê duyệt. `AGENTS.md` là quy tắc bền vững của repository; file này là playbook để người dùng giao việc nhất quán. Nếu có mâu thuẫn, ưu tiên `AGENTS.md` và quy tắc an toàn của pipeline.
