# DeepSeek pilot contract (offline preparation)

Pilot chỉ gồm 5–20 task **sanitized**, có ID riêng, không lấy trực tiếp từ student data, database, raw OCR hàng loạt, private source bank, backup ZIP, credential hoặc login state. Runner mặc định từ chối dưới 5 hoặc trên 20 task.

## Input record

| Field | Rule |
| --- | --- |
| `task_id` | ID ổn định, không mang PII |
| `task_class` | Phải nằm trong allow-list provider |
| `prompt_version` | Phiên bản prompt có thể audit |
| `sanitized_text` | Fixture/golden text được phép, không secret-like |
| `item_count` | Bị giới hạn bởi policy |
| routing flags | FAST default; PRO chỉ từ `ROUTE_*` hợp lệ |

## Audit record

Runner ghi timestamp, `task_id`, task class, logical/actual model, prompt version, route reason, timeout/retry/item limits, dry-run, estimated input token, provider usage, result/error status, latency và review outcome. Không ghi API key, header Authorization, raw private input hoặc output dump ngoài schema.

## Pre-flight gate

Pilot fail closed nếu policy thiếu/OFF, kill switch bật, provider OFF, task count/item/payload/token estimate vượt giới hạn, task chưa sanitize, secret-like payload hoặc route không hợp lệ. `dry_run` luôn tạo metadata nhưng phải có 0 transport call.

## First real run

Chỉ sau khi tests, PR/CI và branch sạch, cần explicit data scope/budget approval rồi mới xin `DEEPSEEK_API_KEY`. Golden fixture trong `toan-ai-local/tests/fixtures/deepseek_pilot_samples.json` chỉ dùng cho unit test, không phải dữ liệu để gọi API.
