# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Phùng Đức Đăng
- **MSSV:** 2A202602956
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/dawnmoriaty/K4-L3-DAY13-PhungDucDang-2A202602956-Monitoring-LLMOps
- **Commit SHA cuối:** (Cập nhật sau commit cuối cùng)
- **Challenge ID:** (Cập nhật khi nhận challenge ở CP3)
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602956`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | | Starter code chưa gắn correlation_id và enrichment context |
| `validate_dashboard.py` | 6/6 panel hợp lệ | | Hợp lệ 6/6 panels theo specification contract |
| `pytest` | 22/22 passed | | 22/22 unit tests baseline pass |
| Số traces hợp lệ | 10 traces | | 10 traces được gửi lên project Langfuse cá nhân |
| Số PII leak | 0 | | Không phát hiện rò rỉ PII nguyên văn ở log mẫu |
| Latency P95 / TTFT P95 | 586.5 ms / 50.0 ms | | Đo từ 10 request baseline mẫu |
| Retrieval success rate | 100% | | 10/10 retrieval tool call thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `app/middleware.py`, `CorrelationIdMiddleware` gọi `clear_contextvars()` để dọn sạch context của request trước, sau đó trích xuất header `x-request-id` từ client gửi lên; nếu không có header này thì tự sinh ID định dạng `req-<8-hex>` bằng `f"req-{uuid.uuid4().hex[:8]}"`. Correlation ID sau đó được bind vào structlog qua `bind_contextvars(correlation_id=correlation_id)` và gán vào `request.state.correlation_id`. Khi kết thúc request, middleware trả lại `x-request-id` và `x-response-time-ms` trong response headers.
- **Các metadata được ghi vào structured log:** Gồm các trường định danh và ngữ cảnh request: `ts` (ISO timestamp UTC), `level` (info/error), `service` ("api"), `event` (`request_received`, `response_sent`, `request_failed`), `correlation_id`, `user_id_hash` (băm sha256 12 ký tự hex), `session_id`, `feature` (`qa`/`summary`), `model` (`claude-sonnet-4-5`), `env` (`dev`), cùng các metrics vận hành (`latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`) và sanitized message/answer preview.
- **Cách bảo đảm PII được scrub trước khi ghi:** Xây dựng danh sách regex pattern trong `app/pii.py` nhận diện email, điện thoại VN các định dạng, CCCD 12 số, thẻ tín dụng 16 số, hộ chiếu, và địa chỉ Việt Nam (từ khóa số nhà, đường/phố, ngõ/ngách, phường/xã, quận/huyện, TP/tỉnh) hỗ trợ cả có dấu, không dấu, chữ thường, chữ HOA, viết tắt (p., q., tp., đ/c), và tiền tố địa chỉ (`địa chỉ:`, `nơi ở:`, `đ/c:`, `DC:`). Hàm `scrub_text` chạy với cờ `re.IGNORECASE` để chuyển mọi thông tin nhạy cảm thành `[REDACTED_<TYPE>]`. Trong `app/logging_config.py`, bộ xử lý `scrub_event` được đưa vào pipeline cấu hình của `structlog` ngay trước `JsonlFileProcessor` và `JSONRenderer`, bảo đảm toàn bộ nội dung trong `payload` và `event` đều được scrub sạch trước khi render JSON hoặc ghi xuống file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/load_test.py` để gửi batch 10 requests mẫu (có chứa email, SĐT, số thẻ tín dụng giả lập). Chạy `python scripts/validate_logs.py` đạt **100/100 điểm** (0 missing required fields, 0 missing enrichment fields, 10 unique correlation IDs, 0 PII leaks). Toàn bộ 29/29 tests trong `pytest` chạy pass, bao gồm các bài test PII chuyên biệt cho email (cả lowercase/UPPERCASE), số điện thoại, CCCD, thẻ tín dụng, hộ chiếu, và đầy đủ các biến thể địa chỉ Việt Nam (không dấu, viết hoa, viết tắt, tiền tố địa chỉ) cùng test kiểm tra header / log propagation.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
