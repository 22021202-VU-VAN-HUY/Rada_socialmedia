# Talent Radar - Plan MVP 4 tuần cho VSF

> **Phiên bản:** 4.0
> **Ngày cập nhật:** 17/07/2026  
> **Đối tượng:** VSF - VinSmart Future
> **Mục tiêu:** Theo dõi người bên ngoài nói gì về VSF, gồm nguồn public và nhóm kín/cộng đồng đóng có quyền truy cập hợp lệ, sau đó chuyển thành chỉ số, cảnh báo và insight phục vụ ra quyết định.

---

## 1. Tóm tắt cho khách hàng

Talent Radar là hệ thống social listening và external voice intelligence cho VSF. Hệ thống không chỉ đếm số bài nhắc tới VSF, mà trả lời bốn câu hỏi thực dụng:

1. Ai đang nói gì về VSF?
2. Họ nói ở đâu: báo chí, mạng xã hội public, nhóm kín có cấp quyền, đối tác hay kênh owned?
3. Nội dung đó tích cực, tiêu cực, trung lập, đang nói về chủ đề nào và có rủi ro không?
4. VSF nên làm gì tiếp theo: điều chỉnh thông điệp, phản hồi, chuẩn bị nội dung, xử lý rủi ro hay theo dõi thêm?

MVP 4 tuần tập trung vào một bản chạy được, có dữ liệu thật hoặc dữ liệu import hợp lệ, dashboard, chỉ số đánh giá, cảnh báo rủi ro và báo cáo tuần.

---

## 2. Phạm vi dữ liệu

| Nhóm nguồn | Ví dụ | Cách dùng |
|---|---|---|
| Public earned voice | Báo chí, bài public, comment public, forum public | Tính vào chỉ số dư luận public |
| Restricted authorized voice | Comment từ nhóm kín/cộng đồng đóng có quyền truy cập hợp lệ | Báo cáo riêng, không gộp thành dư luận public |
| Partner voice | Đối tác, diễn giả, tổ chức liên quan nói về VSF | Báo cáo riêng để hiểu hệ sinh thái |
| Sponsored voice | Nội dung booking, tài trợ, hợp tác truyền thông | Báo cáo riêng, không gọi là earned |
| Owned voice | Website, fanpage, kênh chính thức VSF | Làm mốc đối chiếu thông điệp, không tính là dư luận tự nhiên |

Điều kiện với nhóm kín:

- Chỉ xử lý khi có nguồn được duyệt, người cung cấp có thẩm quyền và mục đích sử dụng rõ ràng.
- Ưu tiên import/export hợp lệ từ admin/moderator hoặc API được cấp quyền.
- Không dùng cookie/session cá nhân, không bypass login/CAPTCHA/access control.
- Không thu inbox, private profile hoặc dữ liệu cá nhân ngoài mục đích đã duyệt.
- Dashboard phải gắn nhãn `restricted source`, hiển thị sample size và không suy rộng thành "dư luận chung".

---

## 3. Mục tiêu sử dụng

| Mục tiêu | Khách hàng nhận được gì | Chỉ số chính |
|---|---|---|
| Danh tiếng và niềm tin | Biết VSF đang được nhìn nhận thế nào | Net sentiment, negative rate, topic share |
| Chiến dịch/chương trình | Biết chiến dịch có được nhắc tới và hiểu đúng không | Mention lift, message pull-through, engagement |
| Rủi ro và vấn đề nổi lên | Phát hiện sớm nội dung tiêu cực, hiểu sai, tranh luận nhạy cảm | Time to detect, negative velocity, issue severity |
| Nhu cầu và insight công chúng | Biết người ngoài đang hỏi gì, kỳ vọng gì, chưa hiểu gì | Question volume, unmet need recurrence, insight usefulness |

MVP ưu tiên 3 mục tiêu đầu: danh tiếng, chiến dịch và rủi ro. Mục tiêu nhu cầu/insight công chúng được triển khai ở mức phân loại chủ đề và câu hỏi lặp lại.

---

## 4. Chỉ số đánh giá

### 4.1 Chỉ số khách hàng nhìn thấy

| Chỉ số | Ý nghĩa |
|---|---|
| External mention volume | Có bao nhiêu nội dung bên ngoài nhắc tới VSF |
| Public vs restricted split | Tỷ trọng nguồn public và nhóm kín có quyền |
| Sentiment mix | Tích cực, tiêu cực, trung lập, mixed |
| Net sentiment | `(positive - negative) / valid sentiment items * 100` |
| Topic share | Chủ đề nào đang chiếm nhiều thảo luận |
| Message pull-through | Người ngoài có nhắc đúng thông điệp VSF muốn truyền tải không |
| Negative velocity | Tốc độ tăng của nội dung tiêu cực |
| Time to detect | Hệ thống mất bao lâu để phát hiện tín hiệu rủi ro |
| Insight-to-action rate | Bao nhiêu insight được chuyển thành hành động có owner |

### 4.2 Chỉ số kỹ thuật bắt buộc

| Chỉ số | Mục tiêu MVP |
|---|---:|
| Provenance completeness | 100% item có source, timestamp, reference/permalink |
| Source authorization completeness | 100% nguồn active có trạng thái quyền truy cập |
| Restricted source authorization | 100% nguồn nhóm kín có access basis, approved_by, retention, allowed_fields |
| Parser success | >= 95% với dữ liệu import hợp lệ |
| Relevance precision | >= 85% trên sample review |
| Voice type accuracy | >= 90% trên sample review |
| Dashboard traceability | 100% insight truy ngược được về item gốc |

---

## 5. Sản phẩm bàn giao sau 4 tuần

1. Dashboard Streamlit cho VSF:
   - KPI tổng quan.
   - Bộ lọc theo thời gian, nguồn, public/restricted, sentiment, topic, risk.
   - Danh sách mention/comment có evidence.
   - Màn hình issue/risk queue.

2. Pipeline dữ liệu:
   - Import CSV/JSON cho dữ liệu public và nhóm kín được cấp quyền.
   - Một collector public đơn giản nếu nguồn được duyệt sẵn.
   - Chuẩn hóa dữ liệu về cùng schema.
   - Dedup theo URL/content hash/thread reference.

3. Lớp phân tích:
   - Relevance: nội dung có thật sự nói về VSF không.
   - Voice type: public earned, restricted authorized, partner, sponsored, owned, unknown.
   - Sentiment: positive, neutral, negative, mixed.
   - Topic/risk: chủ đề và mức độ rủi ro.

4. Báo cáo:
   - Daily digest ngắn.
   - Weekly reputation brief.
   - Campaign/risk snapshot khi có sự kiện.

5. Tài liệu vận hành:
   - Source registry.
   - Metric definition.
   - Quy tắc dùng dữ liệu nhóm kín.
   - Hướng dẫn chạy local/deploy MVP.

---

## 6. Roadmap 4 tuần

### Tuần 1 - Chốt phạm vi và nền dữ liệu

Mục tiêu: thống nhất khách hàng cần theo dõi gì, nguồn nào được dùng và KPI nào được tính.

Việc cần làm:

- Chốt 3 mục tiêu pilot: danh tiếng, chiến dịch, rủi ro.
- Lập danh sách từ khóa VSF, alias, chương trình, đối tác, loại trừ.
- Lập Source Registry: public, owned, partner, sponsored, restricted.
- Chốt quy tắc nhóm kín: ai cung cấp, quyền gì, lưu bao lâu, trường nào được lưu.
- Thiết kế schema dữ liệu và file import mẫu.
- Chuẩn bị dashboard skeleton.

Kết quả cuối tuần:

- Source Registry v1.
- Query Pack v1.
- Metric Contract v1.
- Import CSV/JSON chạy được với dữ liệu mẫu.

### Tuần 2 - Ingestion và phân loại cơ bản

Mục tiêu: đưa dữ liệu vào hệ thống, chuẩn hóa, dedup và phân loại bước đầu.

Việc cần làm:

- Xây importer cho CSV/JSON.
- Chuẩn hóa item: source, author hash, content, timestamp, engagement, permalink/reference.
- Dedup theo URL/hash/thread reference.
- Gắn nhãn relevance, voice type, sentiment, topic bằng rule + model nhẹ.
- Thêm review queue để người dùng sửa nhãn.
- Lưu audit log cho thay đổi nhãn.

Kết quả cuối tuần:

- Pipeline import end-to-end.
- Dữ liệu public và restricted được tách rõ.
- Review queue hoạt động.
- Có sample đánh giá precision/accuracy.

### Tuần 3 - Dashboard, KPI và cảnh báo

Mục tiêu: biến dữ liệu thành màn hình khách hàng dùng được.

Việc cần làm:

- Xây KPI overview.
- Xây biểu đồ sentiment, topic, source split, negative velocity.
- Xây bảng mention/comment có filter và evidence.
- Xây issue/risk queue với severity.
- Tạo daily digest và weekly brief dạng export.
- Gắn nhãn `restricted source` rõ trên dashboard.

Kết quả cuối tuần:

- Dashboard MVP có thể demo.
- KPI được tính đúng theo source/public/restricted.
- Alert rủi ro có human confirmation.

### Tuần 4 - UAT, chỉnh chất lượng và bàn giao

Mục tiêu: chạy thử với dữ liệu thật hoặc dữ liệu import hợp lệ, sửa lỗi và bàn giao.

Việc cần làm:

- UAT với stakeholder.
- Rà lại false positive, false negative, sentiment sai, topic sai.
- Chỉnh query pack, rule, threshold.
- Kiểm tra dữ liệu nhóm kín: quyền, retention, ẩn thông tin cá nhân, quote policy.
- Viết tài liệu chạy hệ thống và quy trình vận hành.
- Chốt baseline đầu tiên và báo cáo tuần mẫu.

Kết quả cuối tuần:

- MVP chạy được.
- Có báo cáo baseline.
- Có checklist vận hành.
- Có backlog cho giai đoạn sau.

---

## 7. Thiết kế kỹ thuật

### 7.1 Stack đề xuất

| Thành phần | MVP 4 tuần |
|---|---|
| UI | Streamlit |
| Backend logic | Python |
| Storage | SQLite cho MVP local; PostgreSQL nếu deploy server |
| Data import | CSV/JSON importer |
| Scheduler | Manual run hoặc lightweight scheduler |
| AI/rule layer | Rule-based trước, model/LLM hỗ trợ khi có API key |
| Export | CSV/Markdown/HTML report |

### 7.2 Data flow

```text
Source Registry
      ↓
CSV/JSON import hoặc public collector được duyệt
      ↓
Raw item store
      ↓
Normalize + dedup
      ↓
Relevance + voice type + sentiment + topic + risk
      ↓
Human review queue
      ↓
Metric snapshots + dashboard + reports
```

### 7.3 Bảng dữ liệu lõi

| Bảng | Mục đích |
|---|---|
| `sources` | Danh sách nguồn, loại nguồn, quyền truy cập, trạng thái |
| `raw_items` | Dữ liệu gốc đã import, immutable |
| `normalized_items` | Nội dung đã chuẩn hóa |
| `annotations` | Relevance, sentiment, topic, risk, voice type |
| `reviews` | Lịch sử người dùng sửa/duyệt nhãn |
| `metric_snapshots` | KPI theo ngày/tuần/source/purpose |
| `issues` | Cảnh báo rủi ro và trạng thái xử lý |
| `actions` | Insight được chuyển thành hành động |

### 7.4 Quy tắc với nhóm kín

Mỗi nguồn nhóm kín phải có metadata:

```yaml
source_type: restricted_community
access_basis: group_admin_export | platform_api_permission | authorized_manual_upload
approved_by: data_owner
business_purpose: reputation | campaign | risk | insight
retention_days: 90
allowed_fields: [content_text, created_at, engagement_counts, thread_reference]
pii_policy: hash_author_id
quote_policy: paraphrase_by_default
status: approved | pending | disabled
```

Không có đủ metadata trên thì nguồn chỉ được để `pending`, không đưa vào dashboard chính.

---

## 8. Không làm trong 4 tuần

- Không xây hệ thống crawling lén hoặc bypass nền tảng.
- Không tự động thu thập group kín nếu chưa có quyền và retention policy.
- Không xử lý inbox, private profile hoặc dữ liệu cá nhân ngoài mục đích đã duyệt.
- Không làm cross-platform identity resolution.
- Không làm realtime toàn diện.
- Không làm influence score hộp đen.
- Không cam kết sentiment hoàn hảo; sentiment cần review và đo chất lượng.

---

## 9. Definition of Done

MVP được xem là hoàn thành khi:

- Có ít nhất một nguồn public/import chạy được.
- Nếu dùng nhóm kín, nguồn đó có approval metadata đầy đủ.
- 100% item có provenance: source, timestamp, reference/permalink hoặc file import.
- Dashboard tách rõ public, restricted, owned, partner, sponsored.
- KPI chính hiển thị đúng theo data window và sample size.
- Review queue cho phép sửa nhãn relevance/sentiment/topic/risk.
- Báo cáo weekly brief truy ngược được về item gốc.
- Có checklist tuân thủ dữ liệu nhóm kín.
- Có tài liệu chạy hệ thống và backlog sau MVP.

---

## 10. Cần khách hàng chốt ngay

1. Danh sách nguồn public muốn theo dõi.
2. Danh sách nhóm kín/cộng đồng đóng có thể cung cấp dữ liệu hợp lệ.
3. Người chịu trách nhiệm phê duyệt nguồn và retention.
4. Bộ từ khóa chính xác của VSF, chương trình, đối tác, alias và từ khóa loại trừ.
5. Chiến dịch hoặc sự kiện muốn đo trong 4 tuần.
6. Mẫu báo cáo khách hàng muốn nhận: daily digest, weekly brief hay dashboard-only.
7. Quy định nội bộ về việc trích dẫn nguyên văn comment từ nhóm kín.

Nếu 7 điểm này được chốt trong tuần 1, MVP 4 tuần có thể đi theo hướng demo được với dữ liệu thật, có KPI và có quy trình vận hành rõ ràng.
