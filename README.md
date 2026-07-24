# Talent Radar

Talent Radar is a local Windows app for collecting Facebook posts, comments, and
replies through the existing Coc Coc profile selected in configuration. It provides local user accounts,
platform connection settings, collection schedules, background jobs, JSON exports,
and database import.

The current collector is read-only. It does not post, react, message, or modify
Facebook content.

## Current Scope

- Create a local Talent Radar account and sign in with email/password.
- Connect Facebook, TikTok, or Threads through Coc Coc profile `Default` belonging
  to Vũ Văn Huy.
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

The default local database is `data/talent_radar.sqlite3`. Coc Coc is expected at:

```text
C:\Program Files\CocCoc\Browser\Application\browser.exe
```

Override `COCCOC_EXECUTABLE_PATH` in `.env` when needed.

## Start The App

Start the API, background worker, and dashboard as hidden processes:

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

1. Close all Coc Coc windows so Talent Radar can open the profile with its local
   verification channel.
2. Open Settings and select **Lien ket** for Facebook.
3. Confirm that Settings shows `Vũ Văn Huy (Default)`.
4. Sign in to Facebook and keep that Coc Coc window open.
5. Return to Talent Radar and select **Xac nhan**.
6. Talent Radar opens `/me` in a temporary tab and accepts the connection only when
   Facebook does not redirect to login or checkpoint.
7. After confirmation, close Coc Coc before starting a scheduled collection.

The collector reuses Huy's existing profile. It does not read or export cookies,
passwords, or saved credentials. Only one process can use the profile at a time.

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

## API

Core endpoints:

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET /connections`
- `POST /connections/{platform}/connect`
- `POST /connections/{platform}/confirm`
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
