# TrinhMath AI — Master Execution Plan

_Cập nhật: 20/09/2026. Đây là active roadmap; trạng thái branch/commit luôn lấy từ Git._

## Kiến trúc đã chốt

```text
GPT (planner / architecture / reviewer)
  -> Codex (coder chính)
  -> DeepSeek FAST (khi phù hợp hoặc Codex không khả dụng)
  -> DeepSeek PRO (chỉ escalation có reason code)
  -> tests -> PR / CI -> human review -> main
```

`FAST` ánh xạ mặc định tới `deepseek-flash`; `PRO` tới `deepseek-v4-pro`.
Tên thực có thể đổi qua cấu hình sau benchmark, nhưng source chỉ dùng alias.
Qwen không thuộc active architecture và không có adapter hay task phụ thuộc nó.

## Nguyên tắc xuyên suốt

1. Đọc `AGENTS.md`, bộ nhớ trong `ai/`, Git status/diff trước khi sửa.
2. Làm ở branch riêng, không push thẳng `main`, không auto-merge.
3. Thay đổi nhỏ, reversible: implement tối thiểu, thêm test, chạy test, cập nhật memory, commit/push.
4. Không gọi API tính phí, gửi dữ liệu riêng, deploy, migration/xóa dữ liệu, hoặc tự duyệt/phát hành nội dung.
5. Dừng xin quyết định khi cần key/budget, dữ liệu external/private, teacher approval, thay đổi kiến trúc lớn, secret leak hoặc test chưa tìm được nguyên nhân.

## Phase 0 — An toàn Git

- Fetch origin, kiểm tra branch/working tree/ahead-behind trước mọi thay đổi.
- Không reset, xóa hoặc ghi đè local work. Branch PR hiện có chỉ được tiếp tục khi sạch và base đã xác minh.
- Hoàn thành khi: diff rõ ràng, mọi thay đổi mới có thể rollback bằng commit/branch.

## Phase 1 — Provider abstraction và router offline (checkpoint hiện tại)

- Module riêng, không nhét logic provider vào `app.py`.
- Hợp đồng có provider, logical/actual model, task class, reasoning effort, timeout, retry, max items, dry-run, task id, request/usage metadata, result/error status.
- `DeepSeek` mặc định OFF. Mock/Fake, malformed response và missing key đều fail closed; không có HTTP client ở giai đoạn này.
- Router FAST/PRO deterministic, có reason code và không chọn PRO cho vision theo capability hiện tại.
- Hoàn thành khi: unit tests offline và app regression tests PASS; CI không cần key/network.

## Phase 2 — Chuẩn bị DeepSeek adapter, chưa gọi mạng

- Chỉ sau review Phase 1: thiết kế transport qua interface hiện có; key chỉ từ `DEEPSEEK_API_KEY`.
- Profiles logic: `deepseek-fast`, `deepseek-pro`; feature flag, dry-run, timeout, retries, max-items, task id và usage/cost guard bắt buộc.
- Không có key thật hay API call trong repository/CI. Khi cần API key hoặc test có chi phí, dừng xin phép.

## Phase 3 — Pilot có kiểm soát

- Chỉ 5–20 task sanitized/golden-set đã được phép, không student DB, whole source bank, raw OCR hàng loạt, backup ZIP hay login state.
- Đo schema pass rate, correctness/review usefulness, failure/retry, latency, token usage và estimated/actual cost.
- Chỉ mở từng task class nếu kết quả đạt tiêu chí được phê duyệt; nếu không giữ OFF.

## Phase 4 — Content integration sau pilot

```text
SOURCE -> local OCR/parser -> candidate -> optional DeepSeek assistance
-> structural validation -> Math Verifier -> teacher review -> approved
-> student variant -> release validation -> student
```

DeepSeek chỉ classify/normalize/suggest/create draft/flag inconsistency. Nó không được approve, release, sửa source evidence hoặc tự đổi đáp án để khớp lời giải. Dữ liệu/hình/công thức mơ hồ luôn `BLOCK + REQUIRE TEACHER REVIEW`.

## Phase tiếp theo

Sau provider pilot mới lần lượt xử lý hiệu quả teacher review, end-to-end student flow, audit/observability, cloud-readiness (không deploy tự động), và export. Mỗi phase phải giữ pipeline an toàn hiện có, không coi model confidence là correctness.
