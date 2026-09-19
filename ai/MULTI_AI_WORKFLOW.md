# TrinhMath AI — Multi-AI workflow

## Mục tiêu

Tối ưu ba thứ cùng lúc: **chất lượng, chi phí và khả năng kiểm soát**. Không dùng một model cho mọi việc.

## Vai trò mặc định

| Thành phần | Vai trò chính | Không được làm |
| --- | --- | --- |
| GPT | Lập kế hoạch, kiến trúc, review thay đổi quan trọng | Không tự phát hành câu hỏi hoặc coi suy luận là bằng chứng |
| Codex | Coder chính: đọc repo, sửa code, test, tạo branch/PR | Không gọi API trả phí hoặc đẩy thẳng thay đổi rủi ro vào main |
| DeepSeek | Coder phụ / reviewer / batch task giá rẻ khi đã bật provider | Không tự merge main, không tự duyệt nội dung Toán |
| Qwen | Batch text/vision/Toán sau benchmark, dùng cho khối lượng lớn | Không thay thế OCR evidence, verifier hoặc giáo viên |
| OCR local | Trích xuất khối lượng lớn trước tiên | Không tự suy đoán công thức mơ hồ |
| Math Verifier | Kiểm tra cấu trúc/toán trong phạm vi hỗ trợ | INCONCLUSIVE/UNSUPPORTED không phải PASS |
| Giáo viên | Quyết định cuối với nguồn, công thức, lời giải, đáp án và phát hành | Không bị thay thế bởi model |

## Luồng code

```text
GPT plan
  -> ai/TASK_QUEUE.md / handoff
  -> Codex làm branch riêng
  -> test local
  -> DeepSeek review/fallback (chỉ khi provider đã bật)
  -> GitHub PR + CI
  -> review
  -> main
```

DeepSeek không cần chạy thường trực. Khi Codex hết lượt hoặc có task review/batch phù hợp, một handoff nhỏ được tạo từ repo hiện tại và model chỉ làm trên branch/task đã giới hạn.

## Luồng nội dung Toán

```text
Nguồn
 -> OCR/local parser
 -> candidate
 -> AI batch hỗ trợ (Qwen/DeepSeek nếu được bật)
 -> structural validation
 -> Math Verifier
 -> teacher review
 -> approved
 -> student variant
 -> release validation
```

AI chỉ được tạo **candidate/draft/review suggestion**. Không model nào được tự tạo trạng thái approved/released.

## Chính sách chi phí

1. **Local-first** cho OCR, parsing, matching và các bước có thể làm deterministically.
2. **Model rẻ/batch** cho phân loại, chuẩn hóa, review số lượng lớn.
3. **Model mạnh** chỉ dùng cho kiến trúc, lỗi khó, review quan trọng hoặc mẫu benchmark.
4. Cache mọi output hợp lệ theo hash của input + provider + model + prompt version để tránh trả tiền lại.
5. Không gửi toàn bộ 11k trang lên API chỉ vì tiện. Chỉ gửi phần local không giải quyết đủ tốt.
6. Mọi batch phải có giới hạn số item/token/chi phí trước khi chạy.

## Fallback Codex -> DeepSeek

DeepSeek chỉ nhận task khi:
- task được mô tả rõ trong handoff;
- branch/worktree tách biệt;
- không có secret/dữ liệu riêng trong input;
- có test hoặc acceptance criteria;
- output cuối vẫn qua Git diff + test + PR.

Nếu DeepSeek sửa code, commit phải ghi rõ provider/task id trong changelog hoặc PR description.

## Qwen cho tài liệu/Toán

Qwen chỉ được đưa vào production sau khi benchmark trên golden set do giáo viên cho phép. So sánh ít nhất:
- tỷ lệ giữ đúng công thức;
- tỷ lệ bỏ sót hình/dữ kiện;
- JSON/schema compliance;
- hallucination/block rate;
- thời gian;
- chi phí trên 100 trang/câu.

Nếu không thắng pipeline local hiện có ở một use case cụ thể thì không đưa vào use case đó.

## Log tối thiểu

Mỗi lần dùng model ngoài cần lưu metadata, không lưu secret:

```text
provider
model
task_class
prompt_version
input_artifact_refs
timestamp
result_status
estimated_usage/cost nếu có
review_state
human_decision nếu có
```

## Nguyên tắc rollout

- Bước 1: workflow/docs + test gate.
- Bước 2: benchmark provider bằng dữ liệu an toàn.
- Bước 3: provider adapter có feature flag, mặc định OFF.
- Bước 4: batch nhỏ, kiểm tra chi phí/chất lượng.
- Bước 5: mới tăng quy mô.

Không nhảy thẳng từ “có API key” sang “cho chạy toàn kho”.
