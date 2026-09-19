# Test status

_Checkpoint: 20/09/2026, Phase 1 offline provider/router. Các kết quả dưới đây không gọi API, không dùng key và không sửa database/source thật._

## PASS

| Check | Result |
| --- | --- |
| Provider/router unit tests | 10 passed |
| `toan-ai-local` full pytest | 59 passed in 3.60s |
| TrinhMath module syntax/import | PASS (`py_compile`, gồm `ai_provider.py`, `model_router.py`) |
| Isolated `self_check.py` | PASS: `candidates=4843, ready_multiple_choice=4` |
| Converter syntax/import | PASS |
| Converter tests | `CONVERTER_CORE`, `QUESTION_PARSER`, `MATCHING`, `REVIEW_STORAGE` all PASS |

`self_check.py` chạy trong thư mục tạm với database mới và junction chỉ-đọc tới `sources`; database, raw OCR và dữ liệu học sinh thực không bị thay đổi. Cảnh báo Streamlit bare-mode chỉ là cảnh báo runtime dự kiến, không phải lỗi check.

## Final local gate

PASS: `git diff --check`, Git status review và quét Git-tracked text không thấy secret/token/key có độ tin cậy cao; không có `.env`, database, ZIP, key/pem hay secret-named file bị track. CI trên PR vẫn cần chạy sau push và chỉ được cài dependencies công khai/chạy offline tests.

## Future expectations

- Transport/provider run thật: thêm contract test nhưng không có API key/network trong CI.
- Pilot: chỉ golden set sanitized được phê duyệt, 5–20 items, có cost/usage guard.
- Content/OCR changes: phải giữ teacher-review/release gate và test bằng fixture không riêng tư.
