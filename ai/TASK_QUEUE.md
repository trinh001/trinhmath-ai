# Hàng đợi công việc TrinhMath AI

_Cập nhật checkpoint: 20/09/2026. Trạng thái Git thật phải lấy bằng Git, không suy ra từ file này._

## Đang thực hiện

- Phase 1 provider abstraction/router offline đã được dựng, local verification và CI implementation checkpoint đã PASS. PR #3 chờ human review; không auto-merge.
- Provider chưa được tích hợp vào `app.py`, chưa gọi mạng và không có key/API thật.

## Việc tiếp theo đủ điều kiện (sau checkpoint sạch)

1. Review diff/CI của Phase 1. Chỉ khi PR được review, tiếp tục thiết kế transport adapter qua interface hiện có; không gọi mạng.
2. Soạn schema/acceptance cho golden-set DeepSeek sanitized. Không tạo/import dữ liệu riêng hoặc cài model.
3. Giáo viên đối chiếu draft parser cục bộ với nguồn; công thức/hình chưa rõ vẫn `BLOCK + REQUIRE TEACHER REVIEW`.
4. Khi có đủ câu approved theo bài, kiểm thử end-to-end student flow không đổi trạng thái phát hành tự động.

## Chưa được tự triển khai

- Không cài/vận hành C2C, Cloudflare tunnel, OAuth hoặc Node bridge.
- Không cài/vận hành DeepSeek/Qwen, không gọi paid API và không đặt key/budget.
- Không deploy cloud, migration database, thay đổi quyền, hay phát hành nội dung.

## Quy tắc xếp hàng

Ưu tiên task reversible, local-first, có test độc lập và không đụng source/OCR/student data. Dừng khi chạm stop condition trong `AGENTS.md` hoặc `ai/PROVIDER_POLICY.md`.
