# Talent Radar — Kế hoạch phát triển hệ thống External Voice Intelligence cho VSF

> **Phiên bản:** 3.0  
> **Ngày cập nhật:** 17/07/2026  
> **Đối tượng trung tâm:** VSF — VinSmart Future  
> **Mục tiêu:** Theo dõi có hệ thống những gì người bên ngoài nói về VSF, chuyển dữ liệu thành insight phục vụ nhiều mục đích và đo được cả chất lượng hệ thống lẫn tác động tới quyết định.  
> **Hiện trạng:** Đã có prototype Streamlit, mock data, Facebook OAuth skeleton và thử nghiệm đọc nguồn public; chưa có database, collector production, AI pipeline hay scheduler hoàn chỉnh.  
> **Nguồn lực giả định:** 1 full-stack developer, có stakeholder nghiệp vụ tham gia duyệt dữ liệu và UAT.  
> **Thời gian MVP pilot:** 8 tuần.

---

## 1. Quyết định sản phẩm

### 1.1 North Star

Talent Radar phải giúp người dùng trả lời được năm câu hỏi theo thứ tự:

1. **Ai ở bên ngoài đang nói gì về VSF?**
2. **Họ nói ở đâu, trong bối cảnh nào và mức độ lan truyền ra sao?**
3. **Đâu là tín hiệu đáng chú ý, đâu chỉ là nhiễu?**
4. **Tín hiệu đó ảnh hưởng tới mục tiêu nào của VSF?**
5. **Đội ngũ cần làm gì và hành động đó có tạo chuyển biến không?**

North Star Metric của sản phẩm là:

> **Tỷ lệ insight đủ bằng chứng được người dùng chuyển thành hành động hoặc quyết định.**

Không dùng tổng số bài thu thập làm chỉ số thành công chính vì volume thị trường không nằm trong quyền kiểm soát của hệ thống.

### 1.2 Định nghĩa “người ngoài”

Một nội dung được tính là **External Voice** khi tác giả hoặc kênh xuất bản không do VSF sở hữu, quản trị hoặc đặt nội dung trực tiếp.

| Loại tiếng nói | Ví dụ | Dùng trong KPI nhận thức/danh tiếng |
|---|---|---:|
| `external_earned` | Báo chí độc lập, bài viết hoặc bình luận tự phát, cộng đồng public | Có |
| `external_partner` | Đối tác, diễn giả, tổ chức liên quan nói bằng tiếng nói của họ | Có, nhưng tách riêng |
| `external_sponsored` | Nội dung có tài trợ, booking hoặc hợp tác truyền thông | Không gộp với earned; báo cáo riêng |
| `owned` | Website, fanpage, tài khoản chính thức của VSF | Không; chỉ làm mốc đối chiếu |
| `internal` | Kênh nội bộ, tài liệu không công khai | Ngoài phạm vi |
| `unknown` | Chưa xác định được quan hệ sở hữu/tài trợ | Đưa vào hàng chờ rà soát |

Nguyên tắc bắt buộc: dashboard không được gọi nội dung `owned` hoặc `sponsored` là “dư luận tự nhiên”.

### 1.3 Phạm vi VSF-first

- Chỉ giữ nội dung trực tiếp nói về VSF hoặc có quan hệ VSF rõ ràng và có bằng chứng.
- VinFast, Vingroup, VinSmart cũ và các đơn vị trong hệ sinh thái chỉ là ngữ cảnh; không tự động tính là nội dung VSF.
- Không thu thập group kín, tài khoản private hoặc dữ liệu phải vượt login wall/CAPTCHA/access control.
- Không lập hồ sơ cá nhân xuyên nền tảng và không suy đoán thông tin nhạy cảm.
- Không tự động đăng bài, bình luận hoặc tương tác thay người dùng.

---

## 2. Các mục đích sử dụng

Mỗi insight phải gắn ít nhất một `purpose_id`. Không xây một dashboard chung chung rồi kỳ vọng mọi đội tự diễn giải.

| Mục đích | Câu hỏi nghiệp vụ | Đầu ra cần có | Hành động được hỗ trợ | KPI chính |
|---|---|---|---|---|
| **P1. Danh tiếng & niềm tin** | Công chúng đang nhìn nhận VSF như thế nào? | Xu hướng sentiment, chủ đề tạo thiện cảm/lo ngại, nguồn dẫn dắt | Điều chỉnh thông điệp, nội dung giải thích, ưu tiên chủ đề | Net sentiment, tỷ lệ tiêu cực, message pull-through, trust-topic share |
| **P2. Chiến dịch/chương trình** | Một hoạt động của VSF có được bên ngoài nhắc đến và hiểu đúng không? | Mention lift, earned engagement, thông điệp được nhắc lại, phản hồi theo giai đoạn | Tối ưu nội dung/kênh/đối tác trong chiến dịch | Earned mention lift, unique voices, engagement rate, message pull-through |
| **P3. Rủi ro & vấn đề nổi lên** | Có tín hiệu tiêu cực hoặc thông tin sai lệch nào cần xử lý? | Cảnh báo, cụm narrative, nguồn khởi phát, tốc độ tăng, mức nghiêm trọng | Triage, xác minh, chuẩn bị phản hồi, theo dõi sau xử lý | Time to detect, time to triage, negative velocity, false-alert rate |
| **P4. Nhu cầu & insight công chúng** | Người ngoài quan tâm, kỳ vọng hoặc chưa hiểu điều gì? | Topic/intent, câu hỏi lặp lại, unmet needs, pain points | Lập kế hoạch nội dung, chương trình, FAQ, nghiên cứu sâu | Topic share, question volume, unmet-need recurrence, insight usefulness |
| **P5. Stakeholder/đối tác/tiếng nói ảnh hưởng** | Những nguồn nào đang định hình thảo luận về VSF? | Danh sách nguồn/tác giả public, network theo nội dung, chất lượng tương tác | Quan hệ báo chí/đối tác, mời cộng tác, theo dõi nguồn rủi ro | Relevant influence, amplification rate, source diversity, response rate |
| **P6. Employer/talent brand** | Bên ngoài nói gì về cơ hội, con người và môi trường liên quan VSF? | Chủ đề nghề nghiệp, câu hỏi ứng viên, tín hiệu tích cực/tiêu cực | Nội dung tuyển dụng, candidate FAQ, cải thiện trải nghiệm | Talent-topic sentiment, qualified interest proxy, recurring concerns |

P6 chỉ bật khi stakeholder xác nhận đây là mục tiêu thật và cung cấp taxonomy tương ứng. Không tự suy diễn VSF là một employer brand nếu chưa có business owner.

### 2.1 Purpose Registry

Mỗi mục đích cần một bản ghi được phê duyệt:

```yaml
purpose_id: P1
name: reputation_and_trust
business_owner: communications
decision_supported: "Điều chỉnh ưu tiên thông điệp theo tuần"
audience: [public, media, partner]
included_topics: []
excluded_topics: []
primary_metrics: [net_sentiment, negative_rate, message_pull_through]
reporting_cadence: weekly
alert_policy: reputation-v1
active: true
```

Nếu một dashboard hoặc metric không hỗ trợ quyết định đã khai báo, hạng mục đó không thuộc MVP.

---

## 3. Phạm vi dữ liệu và taxonomy

### 3.1 Relevance tier

| Tier | Định nghĩa | Xử lý |
|---|---|---|
| `core` | Nói trực tiếp, chắc chắn về VSF | Tính vào KPI chính |
| `contextual` | Nói về chương trình, con người hoặc đối tác có quan hệ VSF rõ ràng | Tính riêng và cho phép gộp có kiểm soát |
| `watchlist` | Có khả năng ảnh hưởng tới VSF nhưng bằng chứng gián tiếp | Review; không tự động tính KPI |
| `irrelevant` | Trùng từ khóa nhưng không nói về VSF | Loại khỏi phân tích |

Mỗi kết quả relevance phải có `evidence_span`, `matched_entity`, `rule_version` và `confidence`.

### 3.2 Voice type

Sau relevance, hệ thống phân loại tiếp:

```text
core/contextual item
        ↓
source ownership registry
        ↓
owned | external_earned | external_partner | external_sponsored | unknown
        ↓
unknown → human review
```

Không suy luận sponsored chỉ bằng sentiment tích cực. Quan hệ sở hữu, tài trợ và đối tác phải đến từ registry có người duyệt.

### 3.3 Taxonomy phân tích

Mỗi item có thể mang nhiều nhãn nhưng phải phân biệt rõ:

- `topic`: nội dung đang nói về vấn đề gì.
- `sentiment`: sắc thái tích cực/trung lập/tiêu cực/mixed.
- `sentiment_target`: thái độ nhắm tới VSF, chương trình, con người hay sự việc khác.
- `intent`: khen ngợi, hỏi thông tin, góp ý, phàn nàn, chia sẻ trải nghiệm, đưa tin, kêu gọi hành động, đùa/mỉa mai.
- `narrative`: mệnh đề hoặc câu chuyện đang được lặp lại.
- `purpose_id`: mục đích nghiệp vụ mà item có thể phục vụ.
- `risk_category`: misinformation, safety, legal, ethics, service, people, partner, operational hoặc `none`.
- `journey_stage`: awareness, consideration, participation, advocacy nếu use case yêu cầu.

### 3.4 Entity & Query Pack

Không dùng một danh sách keyword phẳng. Mỗi mục đích dùng một Query Pack có version:

```yaml
query_pack_id: vsf-core-v1
direct_terms:
  - VinSmart Future
  - Vin Smart Future
  - VinSmartFuture
ambiguous_terms:
  - VSF
  - VinSmart
required_context: []
exclusions:
  - legacy_vinsmart_phone
program_entities: []
people_entities: []
partner_entities: []
valid_from: 2026-07-17
owner: communications
```

`VSF`, `VinSmart`, `smart future` và các từ ngắn không được tự match nếu thiếu anchor đã phê duyệt.

### 3.5 Nguồn dữ liệu

| Ưu tiên | Nhóm nguồn | Vai trò | Điều kiện |
|---|---|---|---|
| P0 | CSV/JSON/export được cấp quyền | Backfill, benchmark, fallback | Có provenance và schema hợp lệ |
| P0 | Public news/web/RSS được phép | External earned, ổn định để pilot | Terms và robots/access được kiểm tra |
| P0 | Kênh official VSF | Mốc thời gian chiến dịch và thông điệp gốc | Không tính vào external voice KPI |
| P1 | Public social mention/comment qua API hợp lệ | Phản hồi tự nhiên và engagement | Có credential, scope và quota phù hợp |
| P1 | Kênh đối tác/diễn giả public | External partner voice | Có entity relationship record |
| P2 | Forum/community public được phép | Thảo luận chuyên sâu | Đánh giá pháp lý, chất lượng và độ nhiễu |
| Loại | Group kín, private profile, nguồn cần bypass | Không triển khai | Ngoài phạm vi |

MVP chỉ cam kết một luồng dữ liệu tự động P0 đã được phê duyệt và importer P0. Mở thêm nền tảng sau khi connector trước đạt KPI vận hành.

---

## 4. Khung chỉ số đánh giá

### 4.1 Nguyên tắc đo lường

1. Tách **KPI hệ thống**, **KPI chất lượng phân tích**, **KPI dư luận** và **KPI tác động nghiệp vụ**.
2. Báo cáo số tuyệt đối cùng mẫu số, data window, source coverage và mức độ tin cậy.
3. Không cộng sentiment, reach và engagement thành một “điểm danh tiếng” duy nhất trong MVP.
4. Không đặt target dư luận khi chưa có baseline đủ dài. Pilot dùng 30 ngày đầu để tạo baseline theo từng nguồn/chủ đề.
5. So sánh trước–trong–sau chiến dịch phải dùng cùng tập nguồn và cùng phiên bản rule/model.
6. Reach và influence chỉ là ước tính; luôn hiển thị nhãn `estimated` và phương pháp tính.

### 4.2 KPI dữ liệu và vận hành

| Chỉ số | Công thức | Mục tiêu MVP |
|---|---|---:|
| Approved source coverage | Nguồn P0 active / nguồn P0 đã duyệt | 100% |
| Scheduled run success | Job thành công / job đã lên lịch | `>= 95%` trong soak test 7 ngày |
| Data freshness P95 | P95 thời gian từ published/available tới ingested | `< 6 giờ` với nguồn batch |
| Provenance completeness | Item có source, timestamp, run ID, permalink/reference / item được giữ | 100% |
| Idempotency | Duplicate mới khi chạy lại cùng input | 0 |
| Parser success | Item chuẩn hóa thành công / item raw hợp lệ | `>= 98%` |
| Source health visibility | Nguồn có trạng thái, lần chạy cuối và lỗi có thể hành động / nguồn active | 100% |

### 4.3 KPI relevance và AI

| Chỉ số | Công thức/điều kiện | Mục tiêu MVP |
|---|---|---:|
| Relevance precision | True relevant / predicted relevant | `>= 90%` |
| Relevance recall | True relevant found / all true relevant trong golden set | `>= 80%` |
| Ambiguous-term false positive | False positive trong tập `VSF`/`VinSmart` mơ hồ | `<= 5%` |
| Voice-type accuracy | Phân loại đúng earned/partner/sponsored/owned | `>= 95%` trên mẫu đã duyệt |
| Sentiment macro-F1 | Macro-F1 trên mẫu tiếng Việt có nhãn | `>= 0.70`; không đạt thì chỉ hiển thị hỗ trợ review |
| Topic macro-F1 | Macro-F1 cho taxonomy chủ đề đã duyệt | `>= 0.75` với topic đủ mẫu |
| Structured output validity | Output đúng schema sau retry / tổng output | `>= 99%` |
| Evidence traceability | Insight có supporting item IDs và evidence / tổng insight | 100% |
| Human-review agreement | Quyết định model trùng reviewer trên mẫu audit | Theo dõi hàng tuần; target sau baseline |

Golden set tối thiểu 300 item, gồm positive, hard negative, bài ngắn, tiếng Việt không dấu, mỉa mai và nội dung mixed. Ít nhất 20% là hard negative.

### 4.4 KPI dư luận bên ngoài

| Chỉ số | Công thức |
|---|---|
| External mention volume | Số item `external_*` relevant trong kỳ |
| Unique voices | Số tác giả/kênh public duy nhất sau dedup trong kỳ |
| Source diversity | Số nhóm nguồn có external mention; hiển thị cả phân bổ % |
| Earned share | External earned / toàn bộ relevant mentions; không tính unknown |
| Negative rate | External negative / external items có sentiment hợp lệ |
| Positive rate | External positive / external items có sentiment hợp lệ |
| Net sentiment | `(positive - negative) / items có sentiment hợp lệ × 100` |
| Topic share | External items của topic / toàn bộ external items |
| Message pull-through | External items lặp đúng key message / external items relevant trong campaign window |
| Engagement rate | Tổng interaction / mẫu số nền tảng phù hợp; không gộp thô giữa các nền tảng |
| Amplification rate | Share/repost/quote / external item hoặc follower/impression nếu có dữ liệu hợp lệ |
| Mention velocity | Mentions trong cửa sổ hiện tại / độ dài cửa sổ |
| Campaign lift | `(giá trị campaign - baseline trung bình) / baseline trung bình × 100` |
| Share of Voice | VSF external mentions / tổng mentions của tập so sánh đã duyệt |

`Share of Voice` chỉ bật sau khi có danh sách đối tượng so sánh và query pack tương đương; không tự chọn “đối thủ”.

### 4.5 KPI rủi ro và phản ứng

| Chỉ số | Cách đo |
|---|---|
| Time to detect | `detected_at - first_seen_at` |
| Time to triage | `triaged_at - detected_at` |
| Time to acknowledge | `acknowledged_at - alert_sent_at` |
| Negative velocity | Số external negative item mỗi giờ/ngày theo rolling window |
| Issue recurrence | Số lần narrative đã đóng xuất hiện lại trong kỳ |
| False-alert rate | Alert bị reviewer đánh dấu false / tổng alert đã review |
| Missed-critical rate | Issue nghiêm trọng do người dùng phát hiện nhưng hệ thống không cảnh báo / tổng issue nghiêm trọng |
| Post-response change | Thay đổi negative rate/velocity trước và sau mốc phản ứng, có ghi rõ đây là tương quan chứ không khẳng định nhân quả |

Mục tiêu pilot: cảnh báo mức Critical phải có người xác nhận; không cho AI tự kết luận khủng hoảng hoặc tự gửi phản hồi ra bên ngoài.

### 4.6 KPI tác động nghiệp vụ

| Chỉ số | Công thức | Mục tiêu pilot |
|---|---|---:|
| Insight-to-action rate | Insight được gắn action/decision / insight đã publish | Tạo baseline trong 4 tuần pilot |
| Action completion rate | Action hoàn tất / action được tạo từ insight | Tạo baseline |
| Insight usefulness | Điểm người dùng 1–5 sau khi xem insight | `>= 4.0/5` |
| Report adoption | Người nhận mở/xác nhận báo cáo / người nhận mục tiêu | `>= 70%` nếu kênh đo được |
| Decision traceability | Action có owner, due date và supporting insight / action từ hệ thống | 100% |
| Time saved | Thời gian quy trình thủ công trước - sau, đo trên cùng nhiệm vụ | Đo sau 4 tuần |

### 4.7 Scorecard theo mục đích

Mỗi mục đích chỉ có 3–5 KPI chính để tránh dashboard “rừng số”.

| Purpose | Primary KPI | Guardrail | Nhịp báo cáo |
|---|---|---|---|
| P1 Danh tiếng | Net sentiment, negative rate, trust-topic share | Coverage, confidence, earned share | Tuần/tháng |
| P2 Chiến dịch | Earned mention lift, unique voices, message pull-through | Source mix, sponsored tách riêng | Ngày trong chiến dịch + tổng kết |
| P3 Rủi ro | Time to detect, negative velocity, issue recurrence | False-alert và missed-critical rate | Gần thời gian thực theo khả năng nguồn |
| P4 Insight | Topic share, recurring questions, usefulness score | Sample size, review agreement | Tuần/tháng |
| P5 Stakeholder | Relevant influence, amplification, source diversity | Không dùng follower count đơn độc | Tuần/tháng |
| P6 Talent | Talent-topic sentiment, recurring concerns, interest proxy | Không suy đoán đặc điểm ứng viên | Tháng |

---

## 5. Cảnh báo và mức độ nghiêm trọng

### 5.1 Risk score

Không dùng sentiment đơn lẻ để phát cảnh báo. Risk score dựa trên:

- `relevance_confidence`
- `negative_confidence`
- tốc độ tăng so với baseline cùng nguồn/chủ đề
- reach/influence ước tính
- mức độ lặp lại giữa nhiều nguồn độc lập
- risk category và mức thiệt hại tiềm năng
- độ tin cậy của bằng chứng

### 5.2 Mức cảnh báo

| Mức | Điều kiện gợi ý | Workflow |
|---|---|---|
| Info | Tín hiệu mới nhưng chưa tăng nhanh | Đưa vào digest |
| Watch | Vượt baseline hoặc xuất hiện narrative đáng chú ý | Review trong ngày |
| High | Tăng nhanh, nhiều nguồn hoặc nguồn có ảnh hưởng cao | Gửi alert, owner triage |
| Critical | Nguy cơ an toàn/pháp lý/danh tiếng nghiêm trọng và có bằng chứng | Xác nhận con người ngay, kích hoạt runbook |

Threshold cụ thể được hiệu chỉnh sau 30 ngày baseline. Khi chưa đủ mẫu, hệ thống chạy `review-only mode`.

### 5.3 Vòng đời issue

```text
detected → needs_review → confirmed → assigned → monitoring → resolved → closed
                         ↘ false_positive
```

Mỗi issue lưu owner, SLA, supporting items, decision log, action, kết quả và nguyên nhân đóng.

---

## 6. Kiến trúc MVP

```text
Authorized sources / imports
            ↓
      Collector layer
            ↓
 Immutable raw + provenance
            ↓
 Normalize → deduplicate → thread
            ↓
 Relevance → voice type → purpose routing
            ↓
 Sentiment / topic / intent / narrative / risk
            ↓
 PostgreSQL + metric snapshots + audit log
            ↓
 Dashboard / digest / alert / CSV export
            ↓
 Human review → action → outcome feedback
```

### 6.1 Tech stack đề xuất

- Python 3.11+
- Streamlit cho MVP hiện tại; chưa cần viết lại frontend trước khi UAT xác nhận workflow
- FastAPI cho API nội bộ khi cần tách UI và worker
- PostgreSQL; SQLite chỉ dùng local demo
- SQLAlchemy + Alembic
- APScheduler cho MVP; chuyển Celery/Redis khi workload thực tế yêu cầu
- Pydantic cho schema dữ liệu và AI output
- Pandas/Polars cho tổng hợp dữ liệu
- Provider abstraction cho AI; không khóa cứng một model
- Docker Compose cho local/pilot deployment

### 6.2 Các bảng lõi

| Bảng | Vai trò |
|---|---|
| `sources` | Registry nguồn, quyền truy cập, ownership, health |
| `collection_runs` | Lịch sử job, cursor, lỗi, quota |
| `raw_items` | Payload bất biến và content hash |
| `content_items` | Dữ liệu chuẩn hóa, permalink, tác giả public/pseudonymous |
| `entities` / `relationships` | VSF, chương trình, người, đối tác và quan hệ đã duyệt |
| `query_packs` | Keyword/rule/version theo mục đích |
| `classifications` | Relevance, voice type, topic, intent, sentiment, evidence |
| `metric_snapshots` | Metric theo window/source/purpose/version |
| `issues` / `alerts` | Tín hiệu, severity, owner, SLA, trạng thái |
| `insights` | Nhận định có supporting item IDs |
| `actions` | Hành động/quyết định sinh từ insight |
| `reviews` | Human label, lý do, reviewer và audit trail |
| `digests` | Báo cáo theo data window và purpose |

### 6.3 Yêu cầu chất lượng pipeline

- Collector idempotent, checkpoint sau khi commit thành công.
- Raw data không bị ghi đè; normalized/classification có version riêng.
- Dedup trong nguồn và cross-source bằng canonical URL/content hash/similarity có kiểm soát.
- Mọi metric lưu `data_window`, `source_set_version`, `query_pack_version`, `model_version`.
- Item lỗi vào quarantine, không bị mất im lặng.
- Có kill switch theo nguồn và theo connector.

---

## 7. Trải nghiệm sản phẩm

### 7.1 Các màn hình MVP

1. **Executive Overview**  
   3–5 KPI theo purpose, thay đổi so với baseline, dữ liệu mới tới đâu và ba insight quan trọng nhất.

2. **External Voice Feed**  
   Chỉ hiển thị external by default; lọc theo thời gian, source, voice type, topic, sentiment, intent, purpose, relevance và confidence.

3. **Topics & Narratives**  
   Chủ đề tăng/giảm, câu hỏi lặp lại, narrative cluster và bài nguồn đại diện.

4. **Campaign/Program Tracker**  
   Timeline owned message so với external response, earned/sponsored split, message pull-through và campaign lift.

5. **Issues & Alerts**  
   Severity, velocity, nguồn khởi phát, supporting evidence, owner, SLA và action log.

6. **Voices & Sources**  
   Nguồn/tác giả public nổi bật theo relevance và amplification; không biến thành hồ sơ cá nhân nhạy cảm.

7. **Review Queue**  
   Duyệt relevance, voice type, sentiment, topic, issue và keyword/entity suggestion.

8. **Reports**  
   Daily risk digest, weekly reputation brief, campaign report và CSV export đúng bộ lọc.

9. **Source & Measurement Health**  
   Coverage, freshness, job errors, quota, model KPI, sample size và version.

### 7.2 Quy tắc trình bày metric

Mọi card/chart phải hiển thị hoặc cho phép xem:

- định nghĩa metric;
- khoảng thời gian và timezone;
- source set;
- số mẫu;
- owned/earned/partner/sponsored split;
- phần trăm unknown;
- confidence hoặc cảnh báo mẫu nhỏ;
- baseline và kỳ so sánh;
- link về item nguồn.

---

## 8. Workflow con người trong vòng lặp

### 8.1 Review ưu tiên

Đưa vào review queue khi:

- relevance hoặc voice type có confidence thấp;
- alias mơ hồ như `VSF` hoặc `VinSmart`;
- nội dung mixed/mỉa mai;
- alert High/Critical;
- model và rule xung đột;
- item có reach cao nhưng nhãn chưa chắc chắn;
- AI đề xuất entity, topic hoặc keyword mới.

### 8.2 Từ insight tới hành động

```text
Item → Signal → Insight → Decision/Action → Owner/Due date → Outcome → Feedback
```

Insight chưa có supporting item không được publish. Action không có owner và trạng thái không được tính vào KPI tác động.

### 8.3 Báo cáo chuẩn

- **Daily risk digest:** tín hiệu mới, issue mở, alert cần xử lý, freshness.
- **Weekly reputation brief:** KPI P1, chủ đề/narrative, nguồn dẫn dắt, thay đổi so với baseline, đề xuất hành động.
- **Campaign report:** pre/during/post, earned–partner–sponsored split, message pull-through, lift và bài học.
- **Monthly insight review:** xu hướng dài hơn, action outcome, model quality và đề xuất cập nhật taxonomy.

---

## 9. Kế hoạch triển khai 8 tuần

### Tuần 1 — Chốt bài toán và measurement contract

- Duyệt định nghĩa external/owned/partner/sponsored.
- Chọn tối đa ba purpose đầu tiên cho pilot; khuyến nghị P1, P2 và P3.
- Hoàn thành Source & Entity Inventory.
- Viết measurement dictionary và danh sách key message/topic/risk category.
- Chọn một nguồn tự động P0 và chuẩn import P0.

**Gate:** business owner ký scope, purpose, source, metric và quyền truy cập.

### Tuần 2 — Data foundation

- PostgreSQL schema và migration.
- Importer CSV/JSON idempotent.
- Raw/normalized/provenance/quarantine.
- Source registry, collection run và health status.
- Seed dữ liệu evaluation.

**Gate:** rerun cùng input tạo 0 duplicate; 100% item có provenance.

### Tuần 3 — Collector và relevance

- Một connector P0 được cấp quyền.
- Normalize tiếng Việt, canonical URL, dedup.
- Query Pack, entity/exclusion rule có version.
- Relevance tier và evidence extraction.
- Tạo golden set vòng 1.

**Gate:** relevance precision `>= 90%`, recall `>= 80%` trên tập có nhãn tạm thời hoặc có kế hoạch sửa cụ thể.

### Tuần 4 — External voice và phân tích

- Ownership/relationship registry.
- Voice-type classifier.
- Sentiment target-aware, topic, intent, purpose routing.
- Structured output validation, retry và review queue.
- Evaluation report theo từng label.

**Gate:** owned không bị gộp vào external KPI; mọi AI insight có evidence.

### Tuần 5 — Metric engine và dashboard

- Metric dictionary trong code/config.
- Snapshot theo time window/source/purpose/version.
- Executive Overview, External Voice Feed, Topics & Narratives.
- Source/Measurement Health và CSV export.
- Sample-size/confidence warning.

**Gate:** metric được đối soát bằng truy vấn độc lập trên sample dataset.

### Tuần 6 — Campaign, issue và báo cáo

- Campaign timeline và message pull-through.
- Baseline engine, velocity/anomaly ở review-only mode.
- Issue lifecycle, severity và alert log.
- Daily/weekly/campaign digest có supporting IDs.
- Action tracking cơ bản.

**Gate:** test scenario từ item → alert/insight → action hoàn chỉnh.

### Tuần 7 — UAT, an toàn và vận hành

- UAT theo ba purpose pilot.
- Sửa lỗi metric, filter, review và export.
- Retention/deletion, access control, audit log, secret handling.
- Runbook, backup/restore, connector kill switch.
- Soak test 7 ngày.

**Gate:** không còn lỗi P0; lỗi P1 có owner và deadline.

### Tuần 8 — Pilot và baseline

- Chạy pilot với người dùng thật.
- Thu usefulness score và action feedback.
- Chốt baseline ban đầu, alert threshold tạm thời.
- Đánh giá KPI hệ thống/AI/adoption.
- Quyết định nguồn và purpose mở rộng cho phase 2.

**Gate:** stakeholder chấp nhận báo cáo pilot và ký backlog phase 2.

---

## 10. Ưu tiên backlog

### Must have cho MVP

- External voice definition và ownership registry.
- Importer + một collector được cấp quyền.
- Provenance, dedup, relevance và evidence.
- Voice type, sentiment, topic, intent và purpose routing.
- Feed/filter, KPI overview, review queue, health, digest, export.
- Issue/alert ở human-confirmed mode.
- Metric dictionary, golden set và evaluation report.
- Insight → action tracking.

### Should have

- Narrative clustering.
- Campaign pre/during/post comparison.
- Message pull-through.
- Email/Slack alert sau khi workflow được duyệt.
- Scheduled weekly report.

### Could have sau MVP

- Semantic search/RAG.
- Multi-language.
- Share of Voice với tập so sánh được duyệt.
- Network visualization.
- Predictive trend.
- Nhiều worker và near-real-time ingestion.

### Không làm trong MVP

- Bypass platform control, stealth scraping, cookie/session harvesting.
- Group/private profile không có quyền.
- Auto-response hoặc auto-publishing.
- Cross-platform identity resolution.
- “Influence score” hộp đen hoặc xếp hạng con người chỉ bằng follower count.
- Một composite reputation score không giải thích được.

---

## 11. Vai trò và trách nhiệm

| Vai trò | Trách nhiệm |
|---|---|
| Product/business owner | Chọn purpose, quyết định được hỗ trợ, ưu tiên backlog |
| Communications owner | Duyệt key message, topic, issue severity và action workflow |
| Data owner/legal | Phê duyệt nguồn, purpose, retention và quyền truy cập |
| Developer | Pipeline, database, dashboard, test, deployment, observability |
| Reviewer/analyst | Gắn nhãn golden set, duyệt alert/insight, phản hồi chất lượng |
| Executive consumer | Xác nhận report hữu ích và quyết định từ insight |

Không có reviewer nghiệp vụ thì AI analytics chỉ được coi là prototype, chưa đủ điều kiện production.

---

## 12. Tuân thủ, quyền riêng tư và bảo mật

- Chỉ dùng API/export/RSS/public web được phép và nằm trong source allowlist.
- Không thu thập nhiều hơn mục đích đã khai báo.
- Hạn chế lưu display name/avatar; ưu tiên platform ID hash khi không cần nhận diện public source.
- Không suy đoán tuổi, giới tính, dân tộc, tôn giáo, sức khỏe, chính trị hoặc thuộc tính nhạy cảm.
- Lưu permalink và metadata; không sao chép media nếu không có quyền.
- Có retention, deletion, source deactivation và audit trail.
- Secret chỉ nằm trong environment/secret store; log không chứa token hoặc PII không cần thiết.
- Trước production cần người có thẩm quyền xác nhận điều khoản từng nguồn, cơ sở xử lý dữ liệu và việc gửi dữ liệu tới AI provider.

---

## 13. Rủi ro và phương án

| Rủi ro | Mức | Phương án |
|---|---:|---|
| Không có quyền API/social search | Cao | Access spike tuần 1; importer và public web/RSS hợp lệ làm fallback |
| Nhầm owned/sponsored thành earned | Cao | Ownership registry, unknown review, KPI split bắt buộc |
| Alias VSF gây false positive | Cao | Context gate, hard negatives, không fuzzy-match token ngắn |
| Volume thấp làm metric dao động | Cao | Minimum sample, rolling window dài hơn, confidence warning |
| Sentiment tiếng Việt/mỉa mai sai | Cao | Golden set, target-aware labels, human review, không hiển thị tự động nếu dưới ngưỡng |
| Alert quá nhiều | Cao | Baseline theo topic/source, cooldown, human-confirmed mode, false-alert KPI |
| Insight không dẫn tới hành động | Cao | Purpose/decision contract và action tracking từ đầu |
| Reach/influence gây hiểu lầm | Trung bình | Gắn nhãn estimate, công khai công thức, không dùng follower đơn độc |
| Scope phình thành theo dõi toàn hệ sinh thái Vin | Cao | VSF-first query pack và backlog riêng cho scope mới |
| Một developer quá tải | Cao | Tối đa 3 purpose, 1 live source, giữ Streamlit trong MVP |
| Không tái lập được báo cáo | Cao | Version source/query/model/metric và immutable raw |

---

## 14. Definition of Done

MVP chỉ hoàn thành khi:

- [ ] Ba purpose pilot, decision owner và metric contract được duyệt.
- [ ] External/owned/partner/sponsored được định nghĩa và kiểm thử.
- [ ] Source & Entity Inventory có owner và authorization status.
- [ ] Một nguồn P0 tự động và CSV/JSON importer chạy idempotent.
- [ ] 100% item được giữ có provenance và link/reference nguồn.
- [ ] Relevance và voice type đạt KPI trên golden set.
- [ ] Sentiment/topic chỉ được đưa vào báo cáo khi đạt ngưỡng hoặc có nhãn “cần rà soát”.
- [ ] Dashboard tách external khỏi owned và hiển thị sample size/coverage/version.
- [ ] Daily digest, weekly brief và campaign report truy ngược được về supporting items.
- [ ] Alert High/Critical bắt buộc human confirmation và có audit log.
- [ ] Insight có thể tạo action với owner, due date và outcome.
- [ ] UAT không còn lỗi P0; soak test đạt scheduled run success `>= 95%`.
- [ ] Retention, deletion, secret handling, kill switch và runbook được kiểm thử.
- [ ] Pilot tạo được baseline và báo cáo KPI hệ thống, AI, dư luận và adoption.

---

## 15. Việc cần chốt ngay với stakeholder

1. Ba mục đích ưu tiên trong P1–P6; mặc định đề xuất P1, P2, P3.
2. Danh sách chính xác tài khoản/kênh owned của VSF.
3. Danh sách chương trình, chiến dịch, key message, người và đối tác active.
4. Nguồn nào đã có quyền truy cập và nguồn nào chỉ được import.
5. Ai duyệt alert, ai nhận daily/weekly report và SLA phản hồi.
6. Baseline window mong muốn và các mốc chiến dịch cần so sánh.
7. Quy tắc lưu/xóa dữ liệu và mức nhận diện tác giả cần thiết.
8. Một tập 300 item để tạo golden set và ít nhất hai reviewer nghiệp vụ cho mẫu tranh chấp.

Khi tám đầu vào này chưa hoàn tất, đội phát triển vẫn có thể làm data foundation và importer, nhưng không nên khóa taxonomy, alert threshold hoặc KPI business outcome.

---

> **Tóm tắt:** Talent Radar 3.0 không chỉ “đếm bài nhắc VSF”. Hệ thống tách rõ tiếng nói bên ngoài với nội dung owned/sponsored, định tuyến dữ liệu theo mục đích, đo chất lượng bằng golden set, phát hiện rủi ro có human-in-the-loop và nối insight với hành động. Thành công của MVP được đánh giá bằng độ tin cậy, khả năng truy nguyên và mức độ hỗ trợ quyết định — không phải số lượng nền tảng hay tổng volume thu thập.
