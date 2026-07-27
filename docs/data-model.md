# Talent Radar Data Model

## Design Rules

- PostgreSQL is the runtime database. SQLite is used only for unit tests and as a
  read-only legacy backup.
- All timestamps are stored as timezone-aware UTC values.
- Facebook, TikTok, and Threads use the same content model.
- Platform-specific payloads are retained in JSONB, while fields used for filters,
  joins, and reporting have typed columns.
- Metrics are snapshots. A later collection appends or updates an observation
  instead of overwriting the history of likes, views, comments, or shares.
- A comment or reply points to its direct parent and its root post.
- User ownership is recorded on raw and normalized content so one local account
  cannot see another account's collected data.

## Core Tables

| Table | Purpose |
| --- | --- |
| `users` | Local Talent Radar accounts |
| `auth_sessions` | Revocable local login sessions |
| `platform_connections` | One authorization state per user and platform |
| `oauth_states` | Short-lived OAuth callback state |
| `sources` | Group, page, profile, hashtag, or search feed being monitored |
| `run_configurations` | Saved manual collection parameters for one source |
| `collection_jobs` | One explicit collection execution and its result |
| `raw_items` | Original collected payload and provenance |
| `social_accounts` | Normalized post/comment authors |
| `content_items` | Normalized post, comment, and reply records |
| `content_metric_snapshots` | Time series of engagement counters |
| `content_topic_matches` | VSF and future deterministic topic-filter results |
| `alembic_version` | Applied database schema revision |

## Shared Content Contract

`content_items.item_type` is one of `post`, `comment`, or `reply`.

- `platform`: `facebook`, `tiktok`, or `threads`
- `external_id`: identifier assigned by the platform
- `source_id`: group, profile, hashtag, or feed where the item was observed
- `parent_item_id`: direct parent for a comment or reply
- `root_item_id`: root post for every comment and reply
- `author_id`: normalized author in `social_accounts`
- `content_text`: searchable normalized text
- `published_at`: platform publication time when available
- `collected_at`: observation time
- `platform_metadata`: fields that do not have a cross-platform meaning

Raw deduplication uses owner, source, and content hash. When a stable platform ID is
available, normalized content also has a unique owner/source/type/external-ID key.

## Platform Mapping

| Concept | Facebook | TikTok | Threads |
| --- | --- | --- | --- |
| Source | group, page, profile | profile, hashtag, search | profile, search |
| Post | group/page post | video or photo post | thread |
| Comment | post comment | video comment | thread reply |
| Reply | nested comment reply | comment reply | nested reply |
| Reactions | reaction count | like count | like count |
| Views | platform metadata when available | view count | view count when available |
| Shares | share count | share count | repost/share count |

Platform-only counters remain in `platform_metrics` JSONB, while common counters
have typed columns in `content_metric_snapshots`.

## Search And Topic Filtering

PostgreSQL has a GIN expression index over
`to_tsvector('simple', content_items.content_text)`. The `simple` configuration
keeps Vietnamese words and aliases intact without applying an English stemmer.

VSF filtering is deterministic and stored in `content_topic_matches`:

- `topic_key`
- `matched_terms`
- `matched_groups`
- `score`
- `filter_version`

This keeps topic results queryable without mixing them into raw platform payloads.

## Migration

Create the PostgreSQL schema:

```powershell
docker compose up -d db
python -m alembic upgrade head
```

Copy a legacy SQLite database into an empty PostgreSQL database:

```powershell
python scripts/migrate_sqlite_to_postgres.py `
  --source data/talent_radar.sqlite3 `
  --target-url postgresql+psycopg://talent_radar:talent_radar@localhost:5432/talent_radar
```

The copy command refuses to run when the PostgreSQL target already contains a user,
which prevents accidental duplicate imports. It never modifies the SQLite source.
