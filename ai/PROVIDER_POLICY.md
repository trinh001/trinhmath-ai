# Provider activation policy

Chính sách này áp dụng cho DeepSeek đang được chuẩn bị và mọi provider ngoài có thể được xem xét trong tương lai. Qwen không phải provider active.

## Trạng thái mặc định

DeepSeek **OFF**. Không có HTTP client mặc định hay external run trong CI/repository. `UrllibDeepSeekTransport` chỉ được inject rõ ràng qua interface; chỉ đọc key từ `DEEPSEEK_API_KEY` khi người dùng cấp key và ủy quyền run thật.

Logical profiles:

- `deepseek-fast`: `FAST` -> `deepseek-flash` mặc định.
- `deepseek-pro`: `PRO` -> `deepseek-v4-pro` mặc định.

Mapping được cấu hình tập trung; không hard-code một tên V4.1 Pro chưa có xác nhận.

## Điều kiện trước external run

Phải chốt use case/model, data scope/consent/retention, budget theo batch/ngày/tháng, output schema, validation/fallback và golden-set/acceptance threshold. Trước các điều kiện này chỉ dùng local deterministic, mock/fake hoặc dry-run.

Mỗi external run bắt buộc có task id, provider, logical/actual model, timestamp, dry-run, timeout, max retries, max items, request metadata đã redaction, result/error category và estimated/actual usage/cost nếu provider trả về. Chỉ task class nằm trong allow-list, giới hạn số lượng/payload hợp lệ và response JSON schema hợp lệ mới được chạm transport.

## Không được gửi mặc định

- Student database/PII, API key/token, login state;
- whole private source bank, raw OCR hàng loạt, ảnh/tài liệu nguồn chưa được phép;
- backup ZIP, câu chưa rõ quyền, hoặc dữ liệu được giáo viên đánh dấu chặn.

## Failure policy

Missing key, disabled flag, malformed result, timeout/rate limit hoặc provider disagreement đều fail closed: không đổi candidate thành approved/released, không tự đoán/normalize thành fact và đưa item vào review khi cần. Không log secret.

## Cost guard

Không gửi mặc định 11k trang. Luồng luôn là local deterministic -> local OCR/parser -> FAST khi thật sự cần -> PRO chỉ theo router. Pilot sau này chỉ 5–20 task sanitized và phải đo quality, failure, retries, latency, usage/cost trước khi mở rộng.
