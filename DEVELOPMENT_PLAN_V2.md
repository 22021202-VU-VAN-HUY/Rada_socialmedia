# Talent Radar — Development Plan v2 (Chi tiết kỹ thuật)

> **Phiên bản:** 2.0  
> **Ngày lập:** 20/07/2026  
> **Dựa trên:** DEVELOPMENT_PLAN.md v4.1  
> **Trạng thái hiện tại:** Prototype UI-only (Streamlit + mock data, ~1343 dòng app.py)

---

## 1. Tổng quan — Project làm gì?

Talent Radar là hệ thống **social listening & external voice intelligence** cho VSF (VinSmart Future).

**Luồng chính:**

```
🌐 Nguồn dữ liệu ──► ⚙️ Crawl & Ingest Pipeline ──► 🧠 AI Analysis Engine ──► 📊 Dashboard & Reports ──► 👤 Người dùng VSF
(Facebook, TikTok,       (thu thập, chuẩn hoá,          (Gemini 2.5 Flash)        (Next.js 15)              (ra quyết định)
 Threads, báo chí)        dedup, lưu trữ)
```

### Bài toán cốt lõi

| Câu hỏi | Hệ thống trả lời bằng cách nào |
|---|---|
| **Ai** đang nói gì về VSF? | Crawl → nhận diện tác giả, phân loại voice type |
| Họ nói **ở đâu**? | Source registry + platform tagging |
| Nội dung đó **tích cực hay tiêu cực**? | AI sentiment analysis + topic classification |
| VSF nên **làm gì tiếp**? | AI đề xuất hành động (action recommendation) |

---

## 2. Hiện trạng codebase (Baseline)

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Dashboard UI | ✅ Prototype Streamlit, 8 trang | app.py (~1343 dòng) |
| Mock data | ✅ 8 posts, 4 sources, 2 digests | dashboard_mock_data.json |
| Facebook OAuth | ✅ Skeleton hoạt động | Trong app.py |
| Public crawl | ✅ Fetch HTML cơ bản | Trong app.py |
| Database | ❌ Chưa có | — |
| AI/NLP pipeline | ❌ Chưa có | — |
| TikTok connector | ❌ Placeholder UI | — |
| Threads connector | ❌ Placeholder UI | — |
| Scheduler/Cron | ❌ Chưa có | — |
| Report generation | ❌ Chưa có | — |

---

## 3. Crawl từ đâu? — Chi tiết nguồn dữ liệu

### 3.1 Facebook (Ưu tiên P0)

**4 loại nguồn chính:**
- **Group public:** HTML crawl metadata + Graph API nếu có quyền
- **Group kín:** CSV/JSON import từ admin + Graph API nếu admin cấp app
- **Fanpage/Page public:** Graph API Page Feed + Page comment
- **Bài viết cá nhân public:** Graph API Search + Hashtag tracking

| Phương pháp | Khi nào dùng | Giới hạn |
|---|---|---|
| **Graph API** (`/group/feed`, `/page/feed`) | Có OAuth token + scope được Meta duyệt | Cần app review, advanced access |
| **CrowdTangle** (nếu còn) / Meta Content Library | Đối tác nghiên cứu | Cần đăng ký với Meta |
| **HTML public fetch** (đang có) | Đọc metadata group/page public | Không đọc được nội dung bài khi bị login wall |
| **CSV/JSON import** | Admin group export dữ liệu | Phụ thuộc người cung cấp |
| **Apify / Bright Data** (bên thứ 3) | Scraping có giấy phép, TOS-compliant | Chi phí, cần review TOS |

### 3.2 TikTok (Ưu tiên P1)

**3 loại nguồn:**
- **TikTok Research API:** Query videos by keyword + comment threads
- **TikTok Display API:** Embed video info + oEmbed metadata
- **Export/Import:** CSV từ creator tools + third-party analytics

| Phương pháp | Khi nào dùng | Giới hạn |
|---|---|---|
| **TikTok Research API** | Nghiên cứu học thuật/doanh nghiệp được duyệt | Cần apply, giới hạn rate |
| **TikTok Display API** | Lấy metadata video public | Chỉ embed, không full comment |
| **Apify TikTok Scraper** | Crawl comment/video public | TOS compliance cần review |
| **CSV/JSON import** | Export từ TikTok Analytics hoặc third-party | Phụ thuộc format |

### 3.3 Threads (Ưu tiên P1)

**3 loại nguồn:**
- **Threads API (Meta):** Public post search + reply/comment
- **HTML public fetch:** Metadata OG tags + limited content
- **CSV/JSON import:** Manual export + third-party tools

| Phương pháp | Khi nào dùng | Giới hạn |
|---|---|---|
| **Threads API** (Meta, mới ra) | Đọc public posts, replies | API mới, scope hạn chế |
| **HTML fetch + OG tags** | Metadata cơ bản | Nội dung thường bị JS render |
| **CSV/JSON import** | Dữ liệu từ admin/moderator export | Manual process |

### 3.4 Nguồn bổ sung (P2, sau MVP)

| Nguồn | Phương pháp | Ghi chú |
|---|---|---|
| Báo chí online | RSS feed + HTML scraping | Tuoitre, VnExpress, etc. |
| YouTube comments | YouTube Data API v3 | Comment dưới video liên quan |
| Reddit/Forum | Reddit API / HTML scraping | Nếu VSF được nhắc trên Reddit VN |
| Google Alerts | Email parsing / API | Thông báo khi có mention mới |

---

## 4. AI sẽ đề xuất như thế nào? — AI Analysis Pipeline

### 4.1 Kiến trúc AI Pipeline — 5 bước

```
Raw Item (text, metadata)
    │
    ▼
🔍 Step 1: Relevance Detection ── Query Pack + AI → Nội dung có nói về VSF không?
    │
    ▼
🏷️ Step 2: Entity & Alias Resolution ── Nhận diện VSF qua alias/slang
    │
    ▼
😊😡 Step 3: Sentiment Analysis ── Positive / Negative / Neutral / Mixed
    │
    ▼
📂 Step 4: Topic Classification + Risk Assessment ── Chủ đề + mức rủi ro
    │
    ▼
🎯 Step 5: Action Recommendation ── AI đề xuất VSF nên làm gì
    │
    ▼
Annotated Item → Dashboard + Report
```

### 4.2 Chi tiết từng bước AI

#### Step 1: Relevance Detection (Nội dung có nói về VSF không?)

**Phương pháp: Query Pack + LLM Relevance Scorer**

```
Input: "Có ai biết VSF là viết tắt của gì không? Mình thấy nhiều nhóm dùng acronym này."

Query Pack Match:
  - Keyword "VSF" → match, nhưng ambiguous (alias ngắn)
  - Context check: không có anchor "VinSmart Future", "chương trình", "workshop"

LLM Relevance Score: 0.45 → needs_review
Reason: "VSF là alias ngắn, không đủ ngữ cảnh để xác nhận VinSmart Future"
```

**Cấu hình Query Pack:**

```yaml
# query_pack_vsf.yaml
entity: VSF
version: "2.0"

exact_match:       # confidence cao, auto-accept
  - VinSmart Future
  - Vin Smart Future
  - vinsmart future

alias_match:       # confidence trung bình, cần context check
  - VSF
  - VFS
  - Vinfuture
  - VinFuture

slang_match:       # confidence thấp, cần AI review
  - V đỏ
  - nhà V
  - bên V
  - hệ V
  - công ty công nghệ V

indirect_match:    # watchlist, cần human review
  - chương trình công nghệ của V
  - quỹ tương lai của V
  - bên Vin làm về future

exclusion:         # loại bỏ
  - VinFast
  - Vingroup
  - VinSmart phone
  - VinFuture Prize
  - VSF FC            # đội bóng
  - VSF file format   # tech term
```

#### Step 2: Sentiment Analysis (Tích cực / Tiêu cực / Trung lập)

**Phương pháp: LLM-based Vietnamese Sentiment**

```
Input: "Form đăng ký chương trình VinSmart Future hơi khó dùng trên điện thoại"

AI Output:
{
  "sentiment": "negative",
  "confidence": 0.88,
  "target": "registration form UX",
  "aspect": "usability",
  "intensity": "mild",       // mild | moderate | strong
  "evidence": "hơi khó dùng trên điện thoại"
}
```

#### Step 3: Topic Classification

**Taxonomy chủ đề cố định:**

| Topic ID | Tên | Ví dụ |
|---|---|---|
| `program_update` | Cập nhật chương trình | Workshop mới, lịch mentor |
| `admission` | Đăng ký / tuyển sinh | Tiêu chí, hạn đăng ký |
| `quality` | Chất lượng chương trình | Chứng nhận, mentor, output |
| `ux_feedback` | UX/UI feedback | Form khó dùng, web chậm |
| `partnership` | Đối tác / hợp tác | Đối tác chia sẻ, MOU |
| `reputation` | Danh tiếng chung | Nhận xét tổng quan về VSF |
| `controversy` | Tranh cãi / nhạy cảm | Tin sai, so sánh tiêu cực |
| `question` | Câu hỏi từ công chúng | Hỏi thông tin, tìm hiểu |

#### Step 4: Risk Assessment

```
AI Risk Output:
{
  "risk_level": "medium",          // none | low | medium | high | critical
  "risk_type": "negative_ux",     // misinformation | negative_ux | controversy | data_leak | competitive
  "velocity": "stable",            // declining | stable | rising | spiking
  "recommended_response_time": "48h",
  "escalate_to": "product_owner"
}
```

#### Step 5: Action Recommendation (AI đề xuất VSF nên làm gì)

```
AI Action Output:
{
  "recommended_actions": [
    {
      "action": "Chuẩn bị FAQ ngắn về form đăng ký trên mobile",
      "priority": "medium",
      "owner_suggestion": "Product Team",
      "deadline_suggestion": "3 ngày",
      "type": "content_creation"     // content_creation | direct_response | monitoring | escalation | no_action
    },
    {
      "action": "Theo dõi thêm phản hồi tương tự trong 48h",
      "priority": "low",
      "owner_suggestion": "Monitoring Team",
      "type": "monitoring"
    }
  ]
}
```

### 4.3 LLM Provider & Model

| Thành phần | Lựa chọn đề xuất | Lý do |
|---|---|---|
| **Primary LLM** | Google Gemini 2.5 Flash | Nhanh, rẻ, hỗ trợ tiếng Việt tốt, structured output |
| **Fallback LLM** | OpenAI GPT-4o-mini | Backup khi Gemini gặp lỗi |
| **Embedding** | Gemini text-embedding-004 | Cho semantic search & similarity |
| **Local fallback** | Qwen 2.5 (7B) qua Ollama | Khi cần offline hoặc tiết kiệm cost |

**Chi phí ước tính:**

| Khối lượng | Gemini 2.5 Flash | GPT-4o-mini |
|---|---|---|
| 1,000 items/ngày | ~$0.50-1.00/ngày | ~$1.00-2.00/ngày |
| 5,000 items/ngày | ~$2.50-5.00/ngày | ~$5.00-10.00/ngày |

---

## 5. Công nghệ sử dụng — Tech Stack chi tiết

### 5.1 Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│  Next.js 15 (App Router) + React 19 + TypeScript            │
│  shadcn/ui + Radix UI │ Recharts │ NextAuth.js              │
└──────────────────────────┬──────────────────────────────────┘
                           │  REST API + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                      API Layer                              │
│  FastAPI (Python 3.12+) │ Celery + Redis (Task Queue)       │
└──────────┬───────────────┬──────────────┬───────────────────┘
           │               │              │
┌──────────▼───┐ ┌─────────▼────┐ ┌───────▼───────────────────┐
│   AI Layer   │ │  Data Layer  │ │      Crawl Layer          │
│ Gemini 2.5   │ │ PostgreSQL   │ │ Facebook Connector        │
│ Flash        │ │ 16 + Redis 7 │ │ TikTok Connector          │
│ Pipeline     │ │ + S3/Local   │ │ Threads Connector         │
│ (5 bước)     │ │              │ │ CSV/JSON Importer         │
└──────────────┘ └──────────────┘ │ Public HTML Crawler       │
                                  └───────────────────────────┘
```

### 5.2 Chi tiết từng công nghệ

| Layer | Công nghệ | Phiên bản | Lý do chọn |
|---|---|---|---|
| **Frontend** | Next.js | 15.x | App Router, SSR, API routes, React 19 |
| **UI Components** | shadcn/ui + Radix | latest | Customizable, accessible, modern |
| **Charts** | Recharts | 2.x | Dễ dùng với React, responsive |
| **Styling** | Tailwind CSS | 4.x | Rapid prototyping, dark mode, design tokens |
| **Auth** | NextAuth.js | 5.x | Facebook/TikTok OAuth built-in |
| **Backend API** | FastAPI | 0.115+ | Async, auto-docs, Python ecosystem |
| **Task Queue** | Celery | 5.4+ | Scheduled crawling, background AI tasks |
| **Message Broker** | Redis | 7.x | Queue + cache + pub/sub |
| **Database** | PostgreSQL | 16 | JSONB, full-text search Vietnamese, robust |
| **ORM** | SQLAlchemy | 2.0+ | Type-safe, async support |
| **Migration** | Alembic | 1.13+ | Schema versioning |
| **AI/LLM** | Google Gemini | 2.5 Flash | Nhanh, rẻ, structured output, tiếng Việt |
| **AI SDK** | Google GenAI SDK | latest | Official Python SDK |
| **Embedding** | text-embedding-004 | latest | Semantic search cho content similarity |
| **HTML Parsing** | BeautifulSoup4 | 4.12+ | Parse HTML từ crawl |
| **HTTP Client** | httpx | 0.27+ | Async HTTP requests |
| **Scheduler** | Celery Beat | 5.4+ | Cron-like scheduling |
| **Containerization** | Docker + Docker Compose | latest | Dev + deploy consistency |

### 5.3 Cấu trúc thư mục mới

```
Talent Radar/
├── frontend/                          # Next.js 15 app
│   ├── app/
│   │   ├── (auth)/                    # Auth pages
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/               # Dashboard pages
│   │   │   ├── overview/page.tsx
│   │   │   ├── feed/page.tsx
│   │   │   ├── analytics/page.tsx
│   │   │   ├── risk-alerts/page.tsx
│   │   │   ├── review-queue/page.tsx
│   │   │   ├── sources/page.tsx
│   │   │   ├── reports/page.tsx
│   │   │   └── settings/page.tsx
│   │   ├── api/                       # Next.js API routes (BFF)
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/                        # shadcn components
│   │   ├── charts/                    # Chart components
│   │   ├── dashboard/                 # Dashboard-specific
│   │   └── shared/                    # Shared components
│   ├── lib/
│   │   ├── api-client.ts              # FastAPI client
│   │   └── utils.ts
│   ├── package.json
│   └── tailwind.config.ts
│
├── backend/                           # FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── posts.py           # CRUD posts/items
│   │   │       ├── sources.py         # Source management
│   │   │       ├── analysis.py        # Trigger AI analysis
│   │   │       ├── reports.py         # Generate reports
│   │   │       ├── reviews.py         # Review queue
│   │   │       ├── crawl.py           # Crawl management
│   │   │       └── auth.py            # Auth endpoints
│   │   ├── core/
│   │   │   ├── config.py              # Settings (pydantic-settings)
│   │   │   ├── security.py            # JWT, OAuth
│   │   │   └── database.py            # SQLAlchemy engine
│   │   ├── models/                    # SQLAlchemy models
│   │   ├── schemas/                   # Pydantic schemas
│   │   ├── services/                  # Business logic
│   │   └── main.py
│   ├── crawlers/                      # Crawl connectors
│   │   ├── base.py                    # Abstract connector
│   │   ├── facebook_connector.py
│   │   ├── tiktok_connector.py
│   │   ├── threads_connector.py
│   │   ├── csv_importer.py
│   │   └── public_html_crawler.py
│   ├── ai/                            # AI Analysis Pipeline
│   │   ├── pipeline.py                # Orchestrator
│   │   ├── relevance.py               # Step 1
│   │   ├── entity_resolution.py       # Step 2
│   │   ├── sentiment.py               # Step 3
│   │   ├── topic_classifier.py        # Step 4
│   │   ├── risk_assessor.py           # Step 5a
│   │   ├── action_recommender.py      # Step 5b
│   │   ├── query_pack.py              # Query Pack engine
│   │   └── prompts/                   # LLM prompt templates
│   ├── tasks/                         # Celery tasks
│   ├── alembic/                       # DB migrations
│   └── tests/
│
├── config/
│   ├── query_packs/
│   │   └── vsf_v2.yaml               # Query Pack cho VSF
│   ├── topic_taxonomy.yaml            # Taxonomy chủ đề
│   └── risk_rules.yaml                # Risk assessment rules
│
├── data/
│   ├── samples/                       # Mock/sample data (giữ lại)
│   ├── imports/                       # CSV/JSON upload area
│   └── exports/                       # Generated reports
│
├── docker-compose.yml                 # PostgreSQL + Redis + Backend + Frontend
├── .env.example
├── DEVELOPMENT_PLAN.md                # Plan v1 (giữ lại)
├── DEVELOPMENT_PLAN_V2.md             # Plan v2 (file này)
└── README.md
```

---

## 6. Database Schema chi tiết

### 6.1 Sơ đồ quan hệ (ERD)

```
SOURCES ──1:N──► RAW_ITEMS ──1:1──► NORMALIZED_ITEMS ──1:N──► ANNOTATIONS
                                         │                        │
                                         │──1:N──► REVIEWS        │──N:1──► AI_RUNS
                                         │
                                         └──N:M──► ISSUES ──1:N──► ACTIONS

METRIC_SNAPSHOTS ──N:1──► SOURCES
```

### 6.2 Chi tiết các bảng

**SOURCES** — Danh sách nguồn dữ liệu

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR | Tên nguồn |
| platform | VARCHAR | facebook / tiktok / threads / website / manual |
| source_type | VARCHAR | public_earned / restricted / partner / sponsored / owned |
| authorization_status | VARCHAR | approved / pending / blocked / disabled |
| collection_method | VARCHAR | graph_api / html_crawl / csv_import / rss |
| access_metadata | JSONB | access_basis, approved_by, retention_days, etc. |
| last_collected_at | TIMESTAMP | |
| priority | VARCHAR | P0 / P1 / P2 |
| active | BOOLEAN | |

**RAW_ITEMS** — Dữ liệu gốc (immutable)

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| source_id | UUID FK → sources | |
| external_id | VARCHAR | ID từ platform gốc |
| raw_content | TEXT | Nội dung gốc |
| raw_metadata | JSONB | Toàn bộ metadata gốc |
| content_hash | VARCHAR | SHA-256 cho dedup |
| collected_at | TIMESTAMP | |
| published_at | TIMESTAMP | |

**NORMALIZED_ITEMS** — Nội dung đã chuẩn hoá

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| raw_item_id | UUID FK → raw_items | |
| source_id | UUID FK → sources | |
| author_hash | VARCHAR | Hash tác giả (privacy) |
| content_text | TEXT | Nội dung cleaned |
| title | VARCHAR | Tiêu đề (nếu có) |
| permalink | VARCHAR | Link gốc |
| platform | VARCHAR | |
| voice_type | VARCHAR | public_earned / restricted / partner / sponsored / owned |
| published_at | TIMESTAMP | |
| collected_at | TIMESTAMP | |

**ANNOTATIONS** — Kết quả AI phân tích

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| item_id | UUID FK → normalized_items | |
| ai_run_id | UUID FK → ai_runs | |
| relevance_score | FLOAT | 0.0 – 1.0 |
| relevance_tier | VARCHAR | core / contextual / watchlist / irrelevant |
| sentiment | VARCHAR | positive / negative / neutral / mixed |
| sentiment_confidence | FLOAT | |
| topic | VARCHAR | Theo taxonomy cố định |
| risk_level | VARCHAR | none / low / medium / high / critical |
| matched_terms | JSONB | Các từ khoá match |
| context_evidence | JSONB | Bằng chứng ngữ cảnh |
| recommended_actions | JSONB | Đề xuất hành động |
| review_status | VARCHAR | auto_accepted / needs_review / approved / rejected |

**REVIEWS** — Hàng chờ rà soát

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| item_id | UUID FK → normalized_items | |
| annotation_id | UUID FK → annotations | |
| reason | TEXT | Lý do cần review |
| priority | VARCHAR | low / medium / high |
| suggested_action | TEXT | |
| decision | VARCHAR | approve / reject / keep |
| decided_by | VARCHAR | |
| decided_at | TIMESTAMP | |

**AI_RUNS** — Lịch sử chạy AI

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| model_name | VARCHAR | gemini-2.5-flash / gpt-4o-mini |
| pipeline_version | VARCHAR | |
| items_processed | INTEGER | |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |
| metrics | JSONB | Precision, recall, cost |

**ISSUES** — Cảnh báo rủi ro

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| title | TEXT | |
| risk_level | VARCHAR | |
| risk_type | VARCHAR | misinformation / negative_ux / controversy / etc. |
| status | VARCHAR | open / investigating / resolved / dismissed |
| related_item_ids | JSONB | Danh sách item liên quan |
| detected_at | TIMESTAMP | |
| resolved_at | TIMESTAMP | |

**ACTIONS** — Hành động từ đề xuất AI

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| issue_id | UUID FK → issues | |
| action_text | TEXT | |
| action_type | VARCHAR | content_creation / direct_response / monitoring / escalation |
| priority | VARCHAR | |
| owner | VARCHAR | |
| status | VARCHAR | pending / in_progress / done / skipped |
| deadline | TIMESTAMP | |

**METRIC_SNAPSHOTS** — KPI theo thời gian

| Cột | Kiểu | Mô tả |
|---|---|---|
| id | UUID PK | |
| snapshot_date | DATE | |
| granularity | VARCHAR | daily / weekly |
| total_mentions | INTEGER | |
| positive_count | INTEGER | |
| negative_count | INTEGER | |
| neutral_count | INTEGER | |
| net_sentiment | FLOAT | |
| topic_distribution | JSONB | |
| source_distribution | JSONB | |

---

## 7. Data Flow chi tiết — Từ crawl đến đề xuất

```
⏰ Celery Beat (trigger mỗi 30 phút)
    │
    ▼
🕷️ Crawler (fetch data từ Facebook/TikTok/Threads)
    │
    ├──► 🗄️ Store raw_items (immutable)
    ├──► 🔄 Normalize → normalized_items
    └──► 🔍 Dedup (content_hash check)
    │
    ▼
⏰ Celery Beat (trigger phân tích cho items mới)
    │
    ▼
🧠 AI Pipeline
    │
    ├──► 🤖 Gemini: Step 1 — Relevance check (batch)
    │         └── relevance_score, matched_terms
    │
    ├──► 🤖 Gemini: Step 2 — Sentiment analysis (batch)
    │         └── sentiment, confidence, target
    │
    ├──► 🤖 Gemini: Step 3 — Topic + Risk (batch)
    │         └── topic, risk_level, risk_type
    │
    └──► 🤖 Gemini: Step 4 — Action recommendation
              └── recommended_actions[]
    │
    ▼
🗄️ Store annotations + issues + actions
    │
    ├──► Items low confidence → review queue
    │
    ▼
📊 Dashboard (query KPI, filtered posts, alerts)
    │
    ▼
👤 VSF User (review decisions, ra quyết định)
```

---

## 8. Tính năng Dashboard mới (Next.js)

### 8.1 Trang chính

| Trang | Chức năng | Dữ liệu |
|---|---|---|
| **Overview** | KPI cards, trend charts, sentiment donut, source health | Aggregated metrics |
| **Feed** | Timeline nội dung, filter, search, evidence | normalized_items + annotations |
| **Analytics** | Sentiment trend, topic heatmap, engagement chart, word cloud | metric_snapshots + annotations |
| **Risk Alerts** | Issue cards, severity badge, velocity indicator, action tracker | issues + actions |
| **Review Queue** | Danh sách cần duyệt, inline approve/reject, bulk actions | reviews |
| **Sources** | Source health matrix, connector status, crawl history | sources + crawl logs |
| **Reports** | Generate daily/weekly report, export PDF/CSV, schedule auto-send | report templates |
| **Settings** | Account, OAuth connectors, Query Pack editor, notification rules | config |

### 8.2 Design system

| Element | Spec |
|---|---|
| **Color palette** | Slate-900 background, emerald/rose/amber accent, blue-500 primary |
| **Typography** | Inter (heading), JetBrains Mono (data/code) |
| **Dark mode** | Default, với light mode toggle |
| **Animations** | Framer Motion — card hover, page transition, number count-up |
| **Charts** | Recharts với custom theme matching dark palette |
| **Cards** | Glassmorphism effect cho KPI cards |

---

## 9. Roadmap triển khai — 4 tuần chi tiết

### Tuần 1: Foundation (Nền tảng)

| Ngày | Việc | Output |
|---|---|---|
| D1-D2 | Setup Docker Compose (PostgreSQL + Redis), Alembic migrations, FastAPI skeleton | DB + API chạy được |
| D2-D3 | Setup Next.js 15 + shadcn/ui + Tailwind, layout, sidebar navigation | Frontend skeleton |
| D3-D4 | Implement database models (SQLAlchemy), Pydantic schemas | Schema hoàn chỉnh |
| D4-D5 | CSV/JSON Importer — upload file → parse → store raw_items → normalize | Import pipeline chạy |
| D5 | Query Pack v2 YAML loader + keyword matcher | Query engine cơ bản |

**Deliverable tuần 1:** Import CSV → xem trong database → API trả về danh sách items.

---

### Tuần 2: AI Pipeline + Crawlers

| Ngày | Việc | Output |
|---|---|---|
| D1-D2 | AI Pipeline: Relevance + Sentiment analysis với Gemini 2.5 Flash | 2 bước AI chạy |
| D2-D3 | AI Pipeline: Topic classification + Risk assessment | 4 bước AI chạy |
| D3-D4 | Facebook connector (Graph API) + refine public HTML crawler | Facebook data flow |
| D4-D5 | TikTok connector skeleton + Threads connector skeleton | Multi-platform ready |
| D5 | Celery tasks: scheduled crawl + scheduled analysis + dedup | Background jobs chạy |

**Deliverable tuần 2:** Import/crawl → AI phân tích → annotations trong DB → API trả về.

---

### Tuần 3: Dashboard + Reports

| Ngày | Việc | Output |
|---|---|---|
| D1-D2 | Overview page: KPI cards (glassmorphism), sentiment donut, trend line | Overview hoàn chỉnh |
| D2-D3 | Feed page: timeline cards, filter panel, search, evidence display | Feed hoàn chỉnh |
| D3-D4 | Risk Alerts + Review Queue pages | Alert + review workflow |
| D4 | Analytics page: topic heatmap, word cloud, engagement chart | Analytics page |
| D5 | Report generation: daily digest + weekly brief (Markdown/PDF export) | Báo cáo tự động |

**Deliverable tuần 3:** Dashboard full-feature có thể demo.

---

### Tuần 4: Polish + UAT

| Ngày | Việc | Output |
|---|---|---|
| D1-D2 | Action Recommendation AI (Step 5) + action tracking UI | AI đề xuất hành động |
| D2-D3 | UAT: chạy dữ liệu thật, tune prompts, fix false positive/negative | Chất lượng AI |
| D3-D4 | Source health dashboard, notification system, settings page | Trang quản trị |
| D4-D5 | Documentation, deployment guide, baseline report, backlog | Bàn giao |

**Deliverable tuần 4:** MVP production-ready.

---

## 10. API Endpoints chính

```
# Auth
POST   /api/v1/auth/login
POST   /api/v1/auth/register
POST   /api/v1/auth/oauth/facebook/callback
POST   /api/v1/auth/oauth/tiktok/callback

# Sources
GET    /api/v1/sources                    # List all sources
POST   /api/v1/sources                    # Register new source
PATCH  /api/v1/sources/{id}               # Update source config
GET    /api/v1/sources/{id}/health        # Source health check

# Items
GET    /api/v1/items                      # List items with filters
GET    /api/v1/items/{id}                 # Item detail with annotations
POST   /api/v1/items/import              # CSV/JSON upload
GET    /api/v1/items/search              # Full-text + semantic search

# Analysis
POST   /api/v1/analysis/trigger           # Trigger AI analysis
GET    /api/v1/analysis/runs              # List AI run history
GET    /api/v1/analysis/runs/{id}         # Run detail + metrics

# Reviews
GET    /api/v1/reviews                    # Review queue
PATCH  /api/v1/reviews/{id}              # Approve/reject
POST   /api/v1/reviews/bulk-action        # Bulk approve/reject

# Metrics
GET    /api/v1/metrics/overview           # KPI summary
GET    /api/v1/metrics/trend              # Time-series metrics
GET    /api/v1/metrics/topics             # Topic distribution
GET    /api/v1/metrics/sentiment          # Sentiment breakdown

# Issues & Actions
GET    /api/v1/issues                     # Active issues
POST   /api/v1/issues/{id}/actions        # Add action to issue
PATCH  /api/v1/actions/{id}              # Update action status

# Reports
POST   /api/v1/reports/daily-digest       # Generate daily digest
POST   /api/v1/reports/weekly-brief       # Generate weekly brief
GET    /api/v1/reports/exports            # List past exports

# Crawl
POST   /api/v1/crawl/trigger             # Manual crawl trigger
GET    /api/v1/crawl/status               # Current crawl status
GET    /api/v1/crawl/history              # Crawl run history
```

---

## 11. Biến môi trường cần thiết

```env
# Database
DATABASE_URL=postgresql+asyncpg://talent_radar:password@localhost:5432/talent_radar

# Redis
REDIS_URL=redis://localhost:6379/0

# AI / LLM
GOOGLE_AI_API_KEY=                     # Gemini API key
OPENAI_API_KEY=                        # Fallback (optional)
AI_MODEL=gemini-2.5-flash             # Primary model
AI_FALLBACK_MODEL=gpt-4o-mini         # Fallback model

# Facebook OAuth
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_REDIRECT_URI=http://localhost:3000/api/auth/callback/facebook
FACEBOOK_GRAPH_API_VERSION=v20.0

# TikTok
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# Threads
THREADS_APP_ID=                        # Same as Facebook App ID
THREADS_APP_SECRET=

# App
SECRET_KEY=                            # JWT signing
NEXTAUTH_SECRET=                       # NextAuth secret
NEXTAUTH_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

---

## 12. So sánh Plan v1 vs Plan v2

| Khía cạnh | Plan v1 (hiện tại) | Plan v2 (mới) |
|---|---|---|
| **Frontend** | Streamlit (prototype) | Next.js 15 + shadcn/ui (production-grade) |
| **Backend** | Python script trong app.py | FastAPI + Celery (scalable API) |
| **Database** | Không có (mock JSON) | PostgreSQL 16 + Redis |
| **AI** | Không có (manual rules) | Gemini 2.5 Flash pipeline (5 bước) |
| **Crawling** | HTML fetch cơ bản | Multi-platform connectors + scheduled |
| **Auth** | Session-only demo | NextAuth.js + OAuth thật |
| **Reports** | Chưa có | Auto-generated daily/weekly |
| **Deployment** | `streamlit run` | Docker Compose (production) |
| **Scalability** | Single-user | Multi-user, async, queued |

---

## 13. Open Questions — Cần chốt trước khi code

1. **Facebook App ID:** Đã có Meta App được duyệt chưa? Nếu chưa, tuần 1 cần apply.
2. **TikTok Research API:** Đã đăng ký chưa? Nếu chưa, TikTok sẽ dùng import CSV trước.
3. **Google AI API Key:** Đã có Gemini API key chưa? Cần cho AI pipeline.
4. **Deployment target:** Deploy ở đâu? (VPS, AWS, GCP, Azure, hay chạy local?)
5. **Budget:** Giới hạn chi phí LLM API hàng tháng?
6. **Giữ hay bỏ Streamlit prototype?** Có muốn giữ song song để demo nhanh không?
