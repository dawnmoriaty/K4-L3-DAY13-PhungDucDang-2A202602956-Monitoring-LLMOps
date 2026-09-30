# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms` (ngưỡng SLO $\le$ 3000ms)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` kéo dài trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn đáng kể (> 3s) trước khi nhận được phản hồi
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel **Latency** trên dashboard để xác định P95/P99 tăng vọt từ thời điểm nào.
  2. **Logs:** Lọc `data/logs.jsonl` trong khoảng thời gian xảy ra độ trễ cao, tìm log event `response_sent` có `latency_ms > 3000` và trích xuất `correlation_id`.
  3. **Traces:** Tìm trace trên Langfuse theo `correlation_id`, kiểm tra xem span `retrieval` (RAG vector store) hay `generation` (LLM) là nguyên nhân gây chậm.
- Mitigation tạm thời: Nếu do prompt mới làm response dài thì rollback prompt về version trước; nếu do vector store quá tải thì bật cache retrieval hoặc tắt practice scenario `rag_slow`.
- Owner: `student-2A202602956`

## Alert 2

- Tên: `ElevatedErrorRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Error rate của API và tỉ lệ retrieval success (ngưỡng guardrail $\le$ 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2.0%` hoặc `retrieval_success_rate < 90%` trong 3 phút liên tục
- Ảnh hưởng tới người dùng: Người dùng nhận thông báo lỗi (500 hoặc thất bại khi gọi công cụ), không nhận được câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel **Errors** trên dashboard để xác nhận error rate và tỉ lệ retrieval success.
  2. **Logs:** Lọc `data/logs.jsonl` tìm các event `request_failed`, xem `error_type` (ví dụ `RuntimeError: Vector store timeout`), ghi nhận `correlation_id`.
  3. **Traces:** Mở trace tương ứng trên Langfuse để xem stack trace và observation con `retrieval` bị fail ra sao.
- Mitigation tạm thời: Kiểm tra trạng thái service phụ thuộc (database/vector store); chuyển sang fallback static retrieval nếu tool fail kéo dài; tắt practice scenario `tool_fail`.
- Owner: `student-2A202602956`

## Alert 3

- Tên: `CostSpikeAnomaly`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tổng chi phí USD tích lũy (`daily_cost_usd_max: 2.5`) và token output
- Điều kiện và thời gian duy trì: `sum(cost_usd) > 2.5` hoặc `tokens_out` trung bình tăng đột biến gấp 4 lần trong 5 phút
- Ảnh hưởng tới người dùng: Hệ thống có nguy cơ cạn kiệt ngân sách/quota API của LLM, dẫn đến gián đoạn dịch vụ diện rộng
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel **Cost** và **Tokens** trên dashboard để kiểm tra xu hướng tích luỹ chi phí và token output.
  2. **Logs:** Lọc `data/logs.jsonl` tìm các request có `tokens_out` hoặc `cost_usd` cao bất thường, lấy `correlation_id` và `prompt_label`.
  3. **Traces:** Mở trace trên Langfuse, kiểm tra prompt template đang dùng có bị lặp từ (looping) hoặc system prompt thiếu ràng buộc độ dài hay không.
- Mitigation tạm thời: Rollback prompt về version baseline ổn định (`baseline`/v1); giới hạn `max_tokens` ở LLM client; tắt practice scenario `cost_spike`.
- Owner: `student-2A202602956`
