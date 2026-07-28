# Talent Radar Architecture

## Components

### Central website

- React provides account, source, job, post, comment, and settings screens.
- FastAPI authenticates users and browser agents, owns job state, and validates
  every imported record.
- PostgreSQL stores normalized Facebook, TikTok, and Threads data.
- Topic filters and future AI classification run centrally so models, prompts,
  credentials, and results are consistent across browsers.

### Browser extension

- One source tree builds a Chromium package for Cốc Cốc, Chrome, Edge, Brave, and
  Opera, plus a Firefox package.
- A service worker sends heartbeat events and claims only explicitly queued jobs.
- Content scripts use separate Facebook, TikTok, and Threads adapters.
- Collected records are streamed to the API in batches. Cookies remain inside the
  browser.

## Job flow

1. A signed-in user creates a run configuration and presses Run.
2. FastAPI creates a `browser_extension` job in `queued` state.
3. A paired extension claims a compatible job and opens its source in a background
   tab.
4. The platform adapter sends records to the API as they are found.
5. FastAPI deduplicates and normalizes each batch in PostgreSQL.
6. The extension completes or fails the job and closes the temporary tab.

## Trust boundaries

- User bearer tokens can manage the central account but cannot authenticate an
  extension.
- Pairing codes are single-use, expire after ten minutes, and are stored only as
  SHA-256 hashes.
- Browser agent tokens are returned once, stored by extension storage, and can be
  revoked from the website.
- Agent submissions must match the claimed job's user, platform, and source.
- A revoked agent cannot claim, submit, or complete jobs.

## AI boundary

AI belongs behind the FastAPI service, after deterministic normalization and topic
filtering. The extension should not contain model keys or perform final relevance
decisions. This keeps classification reproducible and lets all three platforms use
the same taxonomy, review queue, and model policy.
