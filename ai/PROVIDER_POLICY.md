# Provider activation policy

Tài liệu này áp dụng cho DeepSeek, Qwen và mọi provider AI bên ngoài sau này.

## Trạng thái mặc định

Mọi provider ngoài hiện là **OFF** cho tới khi người dùng bật rõ ràng. Repository không chứa API key thật.

## Trước khi bật một provider

Phải chốt đủ:

1. Use case cụ thể.
2. Model cụ thể hoặc tiêu chí chọn model.
3. Dữ liệu nào được phép gửi ra ngoài.
4. Dữ liệu nào tuyệt đối không được gửi.
5. Retention/privacy đã chấp nhận.
6. Budget cho một batch và budget ngày/tháng.
7. Timeout/retry/rate-limit policy.
8. Schema output.
9. Validation + fallback.
10. Golden set / acceptance threshold.

## Secret

- Chỉ đọc từ environment hoặc secret store cục bộ.
- Không ghi API key vào Markdown, JSON tracked, source code, log hoặc GitHub issue/PR.
- Tên biến môi trường được phép commit; giá trị thật thì không.
- Nếu phát hiện secret bị track: dừng integration, rotate key rồi mới làm tiếp.

## Data classes

### Có thể gửi sau khi được duyệt
- prompt kỹ thuật không chứa dữ liệu riêng;
- source code công khai/được phép;
- candidate đã được sanitize;
- ảnh/công thức trong golden set được giáo viên cho phép.

### Không gửi mặc định
- database học sinh;
- thông tin cá nhân;
- toàn bộ kho tài liệu nguồn;
- raw OCR hàng loạt;
- API key/token;
- file backup;
- dữ liệu chưa rõ quyền sử dụng.

## Cost guard

Provider adapter sau này phải hỗ trợ tối thiểu:
- max items;
- max retries;
- timeout;
- dry-run;
- estimate/log usage;
- kill switch;
- feature flag per task class.

## Failure policy

- API lỗi/rate limit: không đổi trạng thái candidate sang approved.
- JSON sai: reject/normalize theo schema; không đoán.
- confidence cao không thay thế validation.
- provider disagreement: chuyển review queue.
- model/version thay đổi: benchmark lại trước batch lớn.
