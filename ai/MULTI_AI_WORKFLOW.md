# TrinhMath AI — Multi-AI workflow

## Vai trò active

| Thành phần | Vai trò | Không được làm |
| --- | --- | --- |
| GPT | Lập kế hoạch, kiến trúc, review quan trọng | Tự phát hành nội dung hoặc coi suy luận là bằng chứng |
| Codex | Coder chính: inspect, sửa tối thiểu, test, branch/PR | Gọi API tính phí, commit secret, ghi đè data, push thẳng main |
| DeepSeek FAST | Coder dự phòng/batch/vision khi provider được bật và scope cho phép | Merge main, quyết định teacher approval/release |
| DeepSeek PRO | Escalation cho architecture, debug khó, review rủi ro | Vision hoặc escalation không có reason code |
| OCR local / Math Verifier | Pipeline deterministic trước external AI | Suy đoán công thức mơ hồ hoặc coi INCONCLUSIVE là PASS |
| Giáo viên | Quyết định nguồn, công thức, đáp án và phát hành | Bị thay thế bởi model |

## Luồng code

```text
GPT handoff -> Codex branch -> local tests
  -> DeepSeek FAST (chỉ khi enabled và task phù hợp)
  -> DeepSeek PRO (chỉ escalation rõ ràng)
  -> PR + CI -> human review -> main
```

Mọi phiên bắt đầu bằng `AGENTS.md`, `ai/PROJECT_STATE.md`, `ai/CURRENT_TASK.md`, `ai/TASK_QUEUE.md`, `ai/DECISIONS.md`, `ai/TEST_STATUS.md`, `ai/HANDOFF.md` và Git state. Handoff chỉ chứa scope, acceptance criteria, test, risk; không chứa credential hoặc dữ liệu riêng.

## Router bắt buộc

| Điều kiện | Model | Reason code |
| --- | --- | --- |
| Routine/default | FAST HIGH | `ROUTE_FAST_DEFAULT` |
| Image/vision | FAST HIGH | `ROUTE_VISION_FAST` |
| Architecture/refactor/debug/invariant/security/data integrity khó | PRO HIGH | `ROUTE_COMPLEX_PRO` |
| FAST thất bại ít nhất hai lượt hợp lý | PRO MAX | `ROUTE_FAST_FAILED_TWICE` |
| Final review rủi ro | PRO MAX | `ROUTE_CRITICAL_REVIEW_PRO` |

Không escalation theo cảm giác. PRO hiện không được route cho vision.

## Luồng nội dung Toán

```text
Nguồn -> OCR/local parser -> candidate -> optional DeepSeek assistance
-> structural validation -> Math Verifier -> teacher review -> approved
-> student variant -> release validation
```

External AI chỉ có thể tạo candidate/draft/review suggestion. Không model nào tạo transition `approved`/`released`. Cả kho tài liệu, raw OCR, student database, backup và secret không được gửi mặc định.

## Qwen

Qwen không nằm trong active architecture, roadmap hay provider code. Nếu sau này nghiên cứu lại, cần một quyết định mới và benchmark độc lập trên golden set được phép trước mọi implementation.
