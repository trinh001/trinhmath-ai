# Qwen math/document batch template

Chỉ dùng sau benchmark và khi provider đã được bật.

## Mục đích

Hỗ trợ phân loại/chuẩn hóa/đọc dữ kiện hoặc tạo draft, không tự duyệt.

## Output bắt buộc

Trả JSON theo schema khái niệm:

```json
{
  "artifact_id": "...",
  "task": "...",
  "result": {},
  "uncertainty": [],
  "missing_evidence": [],
  "requires_teacher_review": true,
  "reason": "..."
}
```

## Quy tắc

- Không bịa công thức bị mờ/cắt.
- Không tự nối phần hình với câu nếu mapping không chắc.
- Không đổi đáp án chỉ để khớp lời giải.
- Không dùng kiến thức suy đoán để thay raw source.
- Nếu ảnh/công thức không rõ: `requires_teacher_review=true`.
- Giữ nguyên provenance/id để đối chiếu.
- Không đưa trạng thái approved/released.

## Benchmark

Mọi prompt/model version mới phải thử golden set trước batch lớn và lưu:
- exact/formula accuracy;
- schema pass rate;
- hallucination/block rate;
- latency;
- usage/cost.
