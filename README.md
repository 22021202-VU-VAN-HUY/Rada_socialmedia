# Talent Radar

Talent Radar consists of a central React/FastAPI/PostgreSQL application and one
cross-browser extension. The website owns accounts, sources, jobs, normalized
social data, search, and future AI processing. The extension uses the session in
the browser where it is installed to collect only user-requested jobs.

The current collector is read-only. It does not post, react, message, or modify
Facebook content.

## Current Scope

- Create a local Talent Radar account and sign in with email/password.
- Pair Cốc Cốc, Chrome, Edge, Opera, or Firefox with a one-time code.
- Open Facebook, TikTok, or Threads in the same installed browser profile.
- Collect visible posts and comments with a separate adapter per platform.
- Run a source only after an explicit action in the dashboard.
- Use a React dashboard with instant client-side section navigation.
- Stream each collected batch to PostgreSQL while a job is running.
- Review posts, comments, job status, errors, and export paths.
- Retain the foreground PowerShell crawler as a manual fallback.

Platform markup changes can require updates to an extension adapter. Official APIs
remain preferable where they provide the required content and permissions.

## Setup

PostgreSQL 16 runs through Docker Desktop and is the application database. The
legacy SQLite file is no longer used at runtime.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

The default database URL is
`postgresql+psycopg://talent_radar:talent_radar@localhost:5432/talent_radar`.
Facebook OAuth also requires a Meta app:

```dotenv
FACEBOOK_APP_ID=...
FACEBOOK_APP_SECRET=...
FACEBOOK_REDIRECT_URI=http://localhost:8000/connections/facebook/callback
FACEBOOK_GRAPH_API_VERSION=v20.0
FACEBOOK_SCOPES=public_profile
```

Add the exact redirect URI to **Facebook Login > Settings > Valid OAuth Redirect
URIs** in Meta for Developers. Keep `.env` local; never commit the app secret.

## Start The App

From File Explorer, double-click:

```text
Open Talent Radar.cmd
```

This starts the API and worker as hidden processes, then asks Windows to open
`http://localhost:8000` in the default browser. When Coc Coc is the Windows default,
it reuses Coc Coc's current default profile. VSCode's browser is not used.
The launcher starts PostgreSQL, applies pending Alembic migrations, and then starts
the API.

The PowerShell equivalent is:

```powershell
.\scripts\start_talent_radar.ps1
```

Open [http://localhost:8000](http://localhost:8000), create an account, then use
Settings.

The React source is under `frontend/`. Rebuild the production assets after UI
changes:

```powershell
Set-Location frontend
npm install
npm run build
```

Stop only the processes recorded by Talent Radar:

```powershell
.\scripts\stop_talent_radar.ps1
```

Runtime logs and PID files are stored under `data/runtime`.

New collection jobs are claimed by a paired browser extension. The legacy
Playwright worker does not claim extension jobs. There is no automatic schedule
enqueueing path.

## Browser Extension

Build both browser targets:

```powershell
Set-Location extension
npm run build
```

Load `extension/dist/chromium` as an unpacked extension in Cốc Cốc, Chrome, Edge,
Brave, or Opera. Load `extension/dist/firefox` in Firefox. In Talent Radar, open
**Cài đặt > Extension**, create a one-time code, then enter it in the extension
popup. The raw agent token is shown only to the extension and browser cookies are
never sent to the API.

The extension checks the queue every minute while the browser is running. A manual
**Kiểm tra công việc** button is also available in its popup.

## Platform Authorization

Facebook OAuth remains available for account authorization. Browser collection is
handled by the paired extension in the browser where the user is already signed in.

The OAuth access token is protected with Windows DPAPI before it is stored locally.
The extension does not export cookies, passwords, or saved credentials. OAuth proves
account authorization; it does not automatically grant access to arbitrary Facebook
group posts or comments.

## Run At Windows Logon

After verifying the app locally, install the current-user scheduled task:

```powershell
.\scripts\install_background_task.ps1
```

The task starts after the Windows user logs on. A logged-in Windows session, a valid
Facebook session, and an available Coc Coc profile are required for collection.

## Source Configuration

Sources live in `config/source_registry.example.yaml`. Sync them with:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/sources/sync
```

The included registry contains the public Facebook group from `textlinkmau.txt`.

## Database

The shared Facebook, TikTok, and Threads schema is documented in
[`docs/data-model.md`](docs/data-model.md). It normalizes sources, authors, content
relationships, metric snapshots, and topic matches while retaining original
platform payloads in JSONB.

To move an existing local SQLite database into a new PostgreSQL volume:

```powershell
docker compose up -d db
python -m alembic upgrade head
python scripts/migrate_sqlite_to_postgres.py `
  --source data/talent_radar.sqlite3 `
  --target-url postgresql+psycopg://talent_radar:talent_radar@localhost:5432/talent_radar
```

The SQLite source remains unchanged as a backup.

## VSF Topic Filter

Facebook collection keeps only posts whose text matches the VSF taxonomy in
`config/vsf_keywords.yaml`. Matching ignores case, Vietnamese accents, punctuation,
and repeated whitespace. Comments and replies are expanded only after a post matches.
Each retained post records the matched terms in its `relevance` metadata.

Extend `keyword_groups` in the YAML file to add aliases without changing collector
code. Avoid broad single words such as `vin`, which can create unrelated matches.

## API

Core endpoints:

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET /connections`
- `POST /connections/{platform}/connect`
- `GET /connections/facebook/callback`
- `POST /connections/{platform}/disconnect`
- `GET|POST /run-configurations`
- `PATCH|DELETE /run-configurations/{id}`
- `POST /run-configurations/{id}/run-now`
- `GET /jobs`
- `GET /overview`, `GET /posts`, `GET /comments`
- `GET /sources`, `POST /sources/sync`
- `POST /imports`
- `GET /browser-agents`, `POST /browser-agents/pairing-codes`
- `POST /browser-agent/pair`, `POST /browser-agent/heartbeat`
- `POST /browser-agent/jobs/claim`
- `POST /browser-agent/jobs/{id}/items|complete`

Connection, run-configuration, and job endpoints require the bearer token returned
by login.

## Manual Fallback

The previous foreground crawler remains available:

```powershell
.\scripts\crawl_facebook_coccoc.ps1 `
  -WindowHandle 131176 `
  -GroupScrolls 10 `
  -MaxPosts 5
```

It writes `facebook_coccoc_*.json` and `.csv` files under `data/exports`. Background
jobs write `facebook_playwright_*.json` and import the result automatically.

## Verification

```powershell
python -m pytest -q
python -m compileall -q src tests
```

## Boundaries

- Collect only content the connected account is allowed to view.
- Do not bypass login, CAPTCHA, checkpoints, group permissions, or platform limits.
- Facebook markup changes can require selector updates.
- Confirm that your collection and retention comply with platform terms and
  applicable privacy requirements.
