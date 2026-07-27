# Talent Radar

Talent Radar is a local Windows app for collecting Facebook posts, comments, and
replies through the existing Coc Coc profile selected in configuration. It provides local user accounts,
platform connection settings, collection schedules, background jobs, JSON exports,
and database import.

The current collector is read-only. It does not post, react, message, or modify
Facebook content.

## Current Scope

- Create a local Talent Radar account and sign in with email/password.
- Connect Facebook with Meta OAuth in Coc Coc profile `Default` belonging to
  Vũ Văn Huy.
- Open TikTok or Threads login pages in the configured Coc Coc profile.
- Collect public Facebook posts, comments, and replies visible to the connected
  account.
- Run a Facebook source immediately or on a repeating schedule.
- Keep the worker running after the Streamlit dashboard is closed.
- Review posts, comments, job status, errors, and export paths.
- Retain the foreground PowerShell crawler as a manual fallback.

TikTok and Threads connection profiles are available, but their content collectors
are not implemented in this release.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

The default local database is `data/talent_radar.sqlite3`. Set Coc Coc as the
Windows default browser. Talent Radar opens every app, login, and OAuth URL through
the Windows browser association, so Coc Coc reuses its installed default profile.
`COCCOC_USER_DATA_DIRECTORY` and `COCCOC_PROFILE_DIRECTORY` are read only to verify
that the configured profile exists; Talent Radar does not create another browser
user-data directory.

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
`http://localhost:8501` in the default browser. When Coc Coc is the Windows default,
it reuses Coc Coc's current default profile. VSCode's browser is not used.

The PowerShell equivalent is:

```powershell
.\scripts\start_talent_radar.ps1
```

Open [http://localhost:8501](http://localhost:8501), create an account, then use
Settings.

Stop only the processes recorded by Talent Radar:

```powershell
.\scripts\stop_talent_radar.ps1
```

Runtime logs and PID files are stored under `data/runtime`.

## Connect Facebook

1. Open Settings and select **Lien ket** for Facebook.
2. Windows opens Facebook's official OAuth permission screen in the current default
   Coc Coc profile.
3. Review the requested permission and continue.
4. Facebook redirects to the local API callback. Talent Radar exchanges the code
   server-side, verifies `/me`, and only then marks the connection as connected.

The OAuth access token is protected with Windows DPAPI before it is stored locally.
The collector only attaches to an already controlled instance of that profile and
never launches a copied browser user. It does not export cookies, passwords, or saved
credentials. OAuth proves account authorization; it does not automatically grant
access to arbitrary Facebook group posts or comments.

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
- `GET|POST /schedules`
- `PATCH|DELETE /schedules/{id}`
- `POST /schedules/{id}/run-now`
- `GET /jobs`
- `GET /sources`, `POST /sources/sync`
- `POST /imports`

Connection, schedule, and job endpoints require the bearer token returned by login.

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
