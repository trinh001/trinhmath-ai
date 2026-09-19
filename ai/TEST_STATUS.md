# Test status

_Checkpoint: 20/09/2026, Phase 3 pilot preparation. Các kết quả dưới đây không gọi API, không dùng key thật và không sửa database/source thật._

## PASS

| Check | Result |
| --- | --- |
| Provider/router/transport/pilot unit tests | 23 passed |
| `toan-ai-local` full pytest | 72 passed in 1.70s |
| TrinhMath module syntax/import | PASS (`py_compile`, gồm `deepseek_pilot.py`) |
| Isolated `self_check.py` | PASS: `candidates=4843, ready_multiple_choice=4` |
| Converter syntax/import | PASS |
| Converter tests | `CONVERTER_CORE`, `QUESTION_PARSER`, `MATCHING`, `REVIEW_STORAGE` all PASS |

`self_check.py` chạy trong thư mục tạm với database mới và junction chỉ-đọc tới `sources`; database, raw OCR và dữ liệu học sinh thực không bị thay đổi. Cảnh báo Streamlit bare-mode chỉ là cảnh báo runtime dự kiến, không phải lỗi check.

## Phase 3 local gate

PASS: final `git diff --check`, Git status review và quét Git-tracked text không thấy secret/token/key có độ tin cậy cao trước commit Phase 3. Earlier CI PASS; Phase 3 CI phải chạy sau push và chỉ cài dependencies công khai/chạy offline tests.

## Future expectations

- HTTP transport/provider run thật: phải qua review riêng; không có API key/network trong CI.
- Pilot: chỉ golden set sanitized được phê duyệt, 5–20 items, có cost/usage guard.
- Content/OCR changes: phải giữ teacher-review/release gate và test bằng fixture không riêng tư.
