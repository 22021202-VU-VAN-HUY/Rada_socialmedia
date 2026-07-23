# Talent Radar

Talent Radar collects Facebook posts, comments, and replies through an existing
signed-in Coc Coc window. The collector is read-only and writes JSON/CSV exports
that can be reviewed in Streamlit or imported into the database.

## Current scope

- Open a public Facebook post in the selected Coc Coc session.
- Expand top-level reply threads and nested replies.
- Collect post text, reaction count, comments, reply relationships, IDs, and
  permalinks.
- Scan a public group and retain post links across its virtualized feed.
- Save exports under `data/exports`.
- Import crawler JSON through the existing import adapter/API.

Only collection, storage, import, and review of source data are in scope.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` when local configuration is needed.

## Crawl with Coc Coc

1. Open Coc Coc with the intended user profile and sign in to Facebook.
2. Keep the target Coc Coc window open.
3. Put a sample post URL and group URL in `textlinkmau.txt`.
4. Find the target window handle when several Coc Coc windows are open:

```powershell
Get-Process browser |
  Where-Object { $_.MainWindowHandle -ne 0 } |
  Select-Object MainWindowHandle, MainWindowTitle
```

Run the sample post and group crawl:

```powershell
.\scripts\crawl_facebook_coccoc.ps1 `
  -WindowHandle 131176 `
  -GroupScrolls 10 `
  -MaxPosts 5
```

Run one post only:

```powershell
.\scripts\crawl_facebook_coccoc.ps1 `
  -WindowHandle 131176 `
  -PostUrl "https://www.facebook.com/groups/example/permalink/123/" `
  -SkipGroup
```

The command writes:

- `data/exports/facebook_coccoc_YYYYMMDD_HHMMSS.json`
- `data/exports/facebook_coccoc_YYYYMMDD_HHMMSS.csv`

## Dashboard

```powershell
streamlit run src/talent_radar/dashboard/app.py
```

The dashboard reads the latest JSON exports and shows posts, comments, replies,
permalinks, and collection metadata.

## API

Start the API:

```powershell
uvicorn talent_radar.api.main:app --reload
```

Available endpoints:

- `GET /health`
- `GET /sources`
- `POST /sources`
- `POST /sources/sync`
- `POST /imports`

Load a crawler export and send it to the API:

```powershell
@'
from pathlib import Path
import requests
from talent_radar.services.import_adapter import load_import_file

path = Path("data/exports/facebook_coccoc_YYYYMMDD_HHMMSS.json")
records = [record.model_dump(mode="json") for record in load_import_file(path)]
response = requests.post(
    "http://localhost:8000/imports",
    json={"import_batch_id": "facebook_coccoc_demo", "records": records},
    timeout=30,
)
response.raise_for_status()
print(response.json())
'@ | python -
```

## Safety boundaries

- The crawler reads only the visible target post dialog.
- It does not inspect cookies, passwords, browser profile data, or local
  storage.
- It does not like, share, comment, message, hide, report, or delete content.
- It does not bypass login, CAPTCHA, group permissions, or Facebook limits.
- Facebook UI changes can require selector updates; verify reported and
  collected comment counts after each change.
