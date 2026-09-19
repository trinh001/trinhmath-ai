# TrinhMath AI — Master Execution Plan

_Cập nhật: 19/09/2026_

Mục tiêu của tài liệu này là để Codex có thể làm việc liên tục theo từng pha, không cần người dùng nhắc lại bối cảnh sau mỗi phiên.

## Nguyên tắc vận hành

1. Luôn đọc trước: AGENTS.md, ai/PROJECT_STATE.md, ai/ARCHITECTURE.md, ai/AI_RULES.md, ai/MULTI_AI_WORKFLOW.md, ai/PROVIDER_POLICY.md.
2. Luôn làm trên branch riêng, không push thẳng main.
3. Mỗi pha phải có acceptance criteria, test, commit, push, PR hoặc checkpoint rõ ràng.
4. Chỉ hỏi người dùng khi cần:
   - API key/account thật;
   - chi phí trả phí;
   - thay đổi dữ liệu khó rollback;
   - quyền riêng tư/dữ liệu bên ngoài;
   - thay đổi lớn về product/architecture;
   - teacher approval cho nội dung Toán.
5. Các quyết định kỹ thuật nhỏ, reversible và trong scope thì Codex tự quyết.
6. Khi lỗi: reproduce -> log -> root cause -> minimal fix -> regression test -> rerun.
7. Không coi model confidence là correctness.
8. Không model nào được tự approve/release câu hỏi.

---

# Phase 0 — Đồng bộ local với main

## Mục tiêu
Đảm bảo máy local đang dựa trên main mới nhất trước khi triển khai provider.

## Codex làm
- git fetch
- xác định branch hiện tại
- kiểm tra working tree
- nếu có thay đổi local chưa commit: không ghi đè, báo và tạo backup branch nếu cần
- cập nhật main từ origin/main theo fast-forward an toàn
- tạo branch triển khai mới từ main

## Hoàn thành khi
- local main trùng origin/main
- working tree sạch hoặc mọi thay đổi đã được backup
- branch triển khai riêng đã tạo

---

# Phase 1 — Provider abstraction, chưa gọi mạng

## Mục tiêu
Tạo một interface chung cho AI provider mà không cắm API thật.

## Codex làm
- tạo package/module provider adapter riêng, không nhúng logic provider vào app.py
- định nghĩa interface tối thiểu:
  - provider name
  - model
  - task class
  - request payload
  - timeout
  - max retries
  - max items
  - dry_run
  - usage metadata
  - result status
- tạo mock provider/offline fake provider để test
- feature flag mặc định OFF
- không thêm API key thật
- không gọi network trong test

## Test bắt buộc
- provider OFF không gọi network
- dry-run không gọi network
- malformed response bị reject
- timeout/retry policy được test bằng mock
- không có secret trong log

## Hoàn thành khi
- tất cả test local PASS
- CI PASS
- app hiện tại vẫn chạy bình thường khi provider OFF

---

# Phase 2 — DeepSeek adapter an toàn

## Mục tiêu
Thêm DeepSeek làm coder phụ/reviewer/batch helper nhưng mặc định OFF.

## Codex làm
- tạo DeepSeek adapter qua interface Phase 1
- chỉ đọc API key từ environment
- thêm config ví dụ, không chứa value thật
- thêm task classes ban đầu:
  1. code_review
  2. structured_text_review
  3. bounded_batch_transform
- không cho adapter tự merge/push/main
- không cho adapter quyết định teacher approval

## Guardrails
- max items mặc định nhỏ
- max retries thấp
- timeout rõ ràng
- response schema validation
- kill switch
- usage/cost logging
- fail closed

## Chỉ hỏi người dùng khi
- cần API key thật
- cần chọn model cụ thể
- cần chấp nhận budget/batch thật

## Hoàn thành khi
- mock tests PASS
- integration test có thể skip nếu không có key
- không test bằng dữ liệu riêng tư
- provider OFF vẫn là default

---

# Phase 3 — DeepSeek pilot

## Mục tiêu
Chạy một pilot nhỏ để đo chất lượng/chi phí.

## Dữ liệu
- chỉ dùng sample/sanitized/golden test đã cho phép
- tuyệt đối không dùng toàn bộ source/OCR/database

## Pilot
- 5-20 task nhỏ
- đo:
  - schema pass rate
  - error rate
  - latency
  - retries
  - token/usage nếu có
  - estimated cost
  - review usefulness

## Quyết định
- nếu không đủ tốt: giữ OFF hoặc chỉ dùng một use case cụ thể
- nếu tốt: mở rộng theo task class, không mở toàn cục

---

# Phase 4 — Qwen benchmark

## Mục tiêu
Đánh giá Qwen cho Toán/tài liệu/vision, không đưa production ngay.

## Codex làm
- tạo golden set cấu trúc, không chứa dữ liệu nhạy cảm
- benchmark Qwen theo cùng interface
- so với local OCR/parser và DeepSeek nếu relevant

## Metric
- formula preservation
- missing evidence rate
- hallucination/block rate
- schema pass rate
- latency
- cost per 100 items/pages

## Hoàn thành khi
- có báo cáo benchmark
- chỉ bật task class nơi Qwen thực sự tốt hơn

---

# Phase 5 — Routing engine

## Mục tiêu
Tự chọn công cụ rẻ nhất mà vẫn đủ chất lượng.

## Routing nguyên tắc
- deterministic/local first
- local OCR/parser trước
- cheap external provider cho batch rõ ràng
- model mạnh chỉ cho hard cases
- ambiguous -> teacher review
- disagreement -> review queue

## Routing output
Mọi route phải ghi:
- why selected
- provider/model
- cost class
- confidence/evidence
- fallback
- review requirement

---

# Phase 6 — Content safety pipeline

## Mục tiêu
Không để AI tạo câu sai đi thẳng đến học sinh.

## Pipeline
source -> OCR/parser -> candidate -> AI draft -> structural validator -> math verifier -> teacher review -> approved -> variant -> release validator

## Codex làm
- củng cố queue
- reason code cho block
- audit log
- provenance
- versioning
- teacher decision record
- không cho AI tự approve/release

---

# Phase 7 — Teacher review efficiency

## Mục tiêu
Giảm việc giáo viên phải duyệt bằng tay.

## Codex làm
- ưu tiên hàng review theo risk
- auto-pass chỉ với rule deterministic an toàn
- gom nhóm lỗi giống nhau
- filter theo:
  - missing formula
  - bad OCR
  - answer conflict
  - duplicate option
  - boundary ambiguity
  - image mapping uncertainty
- bulk action chỉ cho thao tác reversible
- teacher final approval vẫn bắt buộc

---

# Phase 8 — End-to-end student flow

## Mục tiêu
Kiểm thử một lượt học sinh hoàn chỉnh.

## Luồng
scope -> quiz -> timer -> submit -> grading -> topic map -> next practice

## Test
- no unsafe question leaks
- release validator enforced
- grading stable
- adaptive suggestion deterministic enough
- restart/reload does not corrupt state

---

# Phase 9 — Observability & AI audit

## Mục tiêu
Biết AI nào đã làm gì.

## Codex làm
- ai_runs metadata
- provider/model/version
- task class
- prompt version
- artifact refs
- test result
- usage/cost
- human decision
- no secret/raw private dump

## Dashboard/report
- success/fail
- spend estimate
- blocked items
- provider quality
- retries
- human override

---

# Phase 10 — Cloud readiness, chưa deploy nếu chưa được duyệt

## Mục tiêu
Chuẩn bị, không tự triển khai.

## Codex làm
- tách config
- secret handling
- DB boundary
- auth boundary
- storage boundary
- deployment checklist
- privacy checklist
- cost estimate

## Dừng và hỏi người dùng trước
- deploy public
- migration production
- paid infra
- domain/account change
- external data transfer

---

# Phase 11 — PDF/Word export

## Mục tiêu
Tạo đề/phiếu học từ dữ liệu đã approved.

## Codex làm
- export service tách riêng
- templates
- Times New Roman
- equation rendering
- images
- answer/solution variants
- layout test
- no unapproved draft in export

---

# Phase 12 — Continuous improvement

## Codex mỗi phiên
1. đọc current state
2. chọn task đầu tiên đủ điều kiện
3. tạo/checkout branch
4. implement minimal slice
5. test
6. update ai/TASK_QUEUE.md
7. update ai/TEST_STATUS.md nếu cần
8. commit
9. push
10. tạo PR hoặc để checkpoint
11. báo ngắn:
   - done
   - files changed
   - tests
   - risks
   - next task

## Điều kiện dừng
- cần user decision
- cần secret/payment
- test fail chưa root-cause
- data safety risk
- architecture decision khó rollback
- teacher approval cần thiết
