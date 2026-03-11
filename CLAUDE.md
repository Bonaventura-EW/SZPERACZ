# CLAUDE.md — AI Assistant Guide for SZPERACZ OLX

## Project Overview

**SZPERACZ OLX** is an autonomous monitoring system for Polish OLX.pl real estate listings (rooms/apartments for rent in Lublin, Poland). It scrapes listing data daily via GitHub Actions, tracks price changes, generates Excel reports, sends weekly email summaries, and serves an interactive dashboard through GitHub Pages.

**No external servers required** — the entire system runs on GitHub Actions (CI/CD) + GitHub Pages (hosting).

---

## Repository Structure

```
SZPERACZ/
├── main.py              # CLI entry point — orchestrates workflows
├── scraper.py           # Core scraper (1,355 lines) — main business logic
├── email_report.py      # Weekly HTML email with Excel attachment
├── autofix.py           # Reactivates GitHub Actions after 60-day inactivity
├── diagnose.py          # Interactive troubleshooting checklist
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
│
├── data/                # Git-tracked output files (auto-committed daily)
│   ├── dashboard_data.json   # Primary data store for dashboard (~569 KB)
│   └── szperacz_olx.xlsx     # Historical Excel archive (~2.1 MB)
│
├── docs/                # GitHub Pages root
│   ├── index.html            # Interactive dashboard (pure HTML/CSS/JS)
│   ├── favicon.svg
│   └── api/
│       ├── status.json       # Current scan status (REST endpoint)
│       ├── history.json      # 30-day scan history (REST endpoint)
│       ├── openapi.yaml      # OpenAPI 3.0 spec
│       └── README.md         # API documentation
│
└── .github/
    └── workflows/
        ├── scan.yml          # Daily OLX scan (9:00 CET)
        ├── weekly_report.yml # Weekly email (Monday 9:30 CET)
        ├── keep-alive.yml    # Prevent workflow deactivation (every 50 days)
        └── failsafe.yml      # Backup scan trigger (11:00 UTC)
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Web scraping | `requests` + `BeautifulSoup4` + `Playwright` (headless browser) |
| Data storage | JSON files + Excel (`openpyxl`) |
| Email | `smtplib` (Gmail SMTP/TLS) |
| Frontend | Pure HTML5 + CSS3 + Vanilla JavaScript (no frameworks) |
| CI/CD | GitHub Actions |
| Hosting | GitHub Pages (static files from `/docs`) |
| VCS | Git — data files committed daily by automation |

**Python version:** 3.11+ (workflows use 3.12)

**Dependencies (`requirements.txt`):**
```
requests>=2.31.0
beautifulsoup4>=4.12.0
openpyxl>=3.1.0
lxml>=5.0.0
playwright>=1.40.0
brotli>=1.0.0
```

---

## Key Files: Roles and Conventions

### `scraper.py` — Core Business Logic

This is the most important file. Key conventions:

- **PROFILES dict** at top of file defines all monitored OLX profiles (URLs, labels, type)
- **`is_category: True`** = category page (e.g., all rooms in Lublin city)
- **`is_category: False`** = individual user profile page (uses Playwright for dynamic content)
- **`run_scan()`** is the main entry point called by `main.py --scan` and GitHub Actions
- **Retry logic:** exponential backoff for HTTP 429, 500, 502, 503, 504
- **User-Agent rotation:** randomly selects from 5 browser UA strings per request
- **Polish locale:** date parsing handles Polish month names (stycznia, lutego, etc.)
- **Crosscheck:** after scraping, the script verifies header count vs actual scraped count; crosscheck status is stored per profile

Output files written by `scraper.py`:
- `data/szperacz_olx.xlsx` — multi-sheet Excel workbook
- `data/dashboard_data.json` — JSON structure for dashboard
- `docs/api/status.json` — current scan status API endpoint
- `docs/api/history.json` — 30-day scan history API endpoint

### `main.py` — CLI Orchestration

```bash
python main.py --scan    # Run OLX scraping
python main.py --email   # Send email report
python main.py --status  # Show system status
python main.py --help    # Usage info
```

### `email_report.py` — Email Reports

- Reads from `data/dashboard_data.json`
- Generates HTML email with embedded tables
- Attaches Excel file
- Config: `SENDER_EMAIL`, `RECEIVER_EMAIL`, `SMTP_SERVER` are hardcoded at top
- Requires `EMAIL_PASSWORD` env var (16-char Gmail App Password)

### `docs/index.html` — Dashboard

- Single-file, self-contained HTML+CSS+JS application
- Fetches `../data/dashboard_data.json` relative to docs folder
- Dark/Light theme stored in `localStorage`
- Canvas-based bar charts (7/14/30 day selectable range)
- Auto-refreshes every 5 minutes
- Manual scan trigger via GitHub Actions API (requires personal access token stored in `localStorage`)

---

## Data Schemas

### `dashboard_data.json`

```json
{
  "profiles": {
    "<profile_key>": {
      "label": "Display Label",
      "url": "https://www.olx.pl/...",
      "is_category": false,
      "daily_counts": [
        { "date": "YYYY-MM-DD", "count": 15, "change": 2, "timestamp": "..." }
      ],
      "current_listings": [
        {
          "id": "OLX_LISTING_ID",
          "title": "...",
          "price": 1200,
          "url": "...",
          "first_seen": "YYYY-MM-DD HH:MM:SS",
          "last_seen": "YYYY-MM-DD HH:MM:SS",
          "published": "YYYY-MM-DD",
          "refreshed": "YYYY-MM-DD",
          "price_change": -100,
          "previous_price": 1300
        }
      ],
      "archived_listings": [ /* same structure, max 200 entries */ ],
      "price_history": {
        "<listing_id>": [
          { "date": "YYYY-MM-DD", "old_price": 1300, "new_price": 1200, "change": -100 }
        ]
      }
    }
  },
  "scan_history": [
    {
      "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
      "status": "success",
      "total_listings": 847,
      "profiles_scanned": 7,
      "duration_seconds": 145
    }
  ],
  "last_scan": "YYYY-MM-DD HH:MM:SS",
  "metadata": { "created": "...", "version": "1.0.0" }
}
```

**Data retention:**
- `daily_counts`: 90-day rolling window
- `archived_listings`: max 200 per profile
- `scan_history`: 90 entries

### Excel Workbook (`szperacz_olx.xlsx`)

- One sheet per monitored profile
- Sheet: `historia_cen` — all price changes across profiles
- Sheet: `podsumowanie` — daily summary snapshot
- Color coding: green = increase, red = decrease, blue = headers

---

## GitHub Actions Workflows

### `scan.yml` — Daily Scan (most important)

- **Schedule:** `0 6 * * *` (6:00 UTC ≈ 8-9:30 CET due to GitHub queue delays)
- **Steps:** checkout → Python 3.12 → pip install + playwright install → `python scraper.py` → git commit+push `data/` and `docs/api/`
- **Permissions:** `contents: write`
- **Timeout:** 30 minutes
- **Manual trigger:** Yes (`workflow_dispatch`)

### `weekly_report.yml` — Email Report

- **Schedule:** `30 7 * * 1` (Monday 7:30 UTC ≈ 9:30 CET)
- **Steps:** checkout → Python 3.11 → pip install → `python email_report.py`
- **Requires secret:** `EMAIL_PASSWORD`

### `keep-alive.yml` — Prevent Workflow Deactivation

- **Schedule:** `0 3 */50 * *` (every 50 days at 3:00 UTC)
- **Purpose:** GitHub disables scheduled workflows after 60 days without repo activity. This creates a commit to prevent that.
- **Action:** Creates/updates `.github/KEEP_ALIVE.txt` with timestamp, commits and pushes

### `failsafe.yml` — Backup Trigger

- **Schedule:** 11:00 UTC as a safety net
- **Purpose:** Retry if main scan.yml didn't fire

---

## Environment Variables

### Required for Email

| Variable | Description | Where Set |
|----------|-------------|-----------|
| `EMAIL_PASSWORD` | 16-char Gmail App Password (no spaces) | GitHub Secrets (production) / `.env` (local) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Python logging level |
| `LOG_DIR` | `./logs/` | Log file directory |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `MAX_RETRY_ATTEMPTS` | `3` | Retry count for failed requests |
| `RETRY_DELAY` | `5` | Delay between retries (seconds) |
| `USE_USER_AGENT_ROTATION` | `true` | Randomize User-Agent header |

**Configuration priority:** GitHub Secrets > env vars > `.env` file > code defaults

**Local setup:**
```bash
cp .env.example .env
# Edit .env with your values
export $(cat .env | xargs)
```

---

## Development Conventions

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run a scan
python scraper.py
# OR
python main.py --scan

# Send email report (requires EMAIL_PASSWORD)
python main.py --email

# Check system status
python main.py --status

# Diagnose issues
python diagnose.py

# Reactivate workflows after inactivity
python autofix.py
```

### No Test Suite

There is no automated test framework (pytest/unittest). Testing is done:
- Manually running `python scraper.py` locally
- Triggering workflows manually via GitHub Actions UI
- Reviewing logs in GitHub Actions tab
- Visual inspection of the dashboard
- Using `diagnose.py` for troubleshooting

When modifying scraper logic, always test with `python scraper.py` and verify `data/dashboard_data.json` is correctly updated.

### No Linter / Formatter Configuration

No `.flake8`, `pyproject.toml`, or `.black` config files. Follow existing code style:
- 4-space indentation
- f-strings for string formatting
- Type hints not used (legacy style)
- Logging via `logging` module (not `print`) for production code

### Git Conventions

Commit message style (emoji prefix):
- `🔍 Scan: YYYY-MM-DD HH:MM UTC` — automated daily scans
- `🐛 Fix: <description>` — bug fixes
- `✨ <description>` — features and improvements
- `🤖 <description>` — automation/maintenance
- `📚 <description>` — documentation
- `✏️ <description>` — small corrections

**Important:** `data/` directory is git-tracked (contains `.xlsx` and `.json`). Both files are auto-committed by GitHub Actions after each scan. Do not add them to `.gitignore` unless the Excel file exceeds 10 MB.

### Making Changes to the Scraper

When modifying `scraper.py`:
1. The `PROFILES` dict at the top is the only config needed to add/remove monitored profiles
2. Crosscheck logic validates scraped count against OLX header count — don't break this
3. The JSON schema in `generate_dashboard_json()` is consumed by `docs/index.html` — changes must be backward-compatible or update both files
4. Playwright is only used for `is_category: False` profiles (individual user pages)
5. BeautifulSoup with lxml is used for category pages

### Making Changes to the Dashboard (`docs/index.html`)

- Single self-contained file — all CSS and JS is inline
- Data loaded from: `fetch('../data/dashboard_data.json')`
- The API path for manual scan trigger: `POST /repos/{owner}/{repo}/actions/workflows/scan.yml/dispatches`
- Theme preference stored in `localStorage` key `theme`
- PAT stored in `localStorage` key `gh_token`

---

## REST API (Static JSON Endpoints)

Base URL: `https://bonaventura-ew.github.io/SZPERACZ/api`

| Endpoint | Description |
|----------|-------------|
| `GET /status.json` | Current scan status, last scan details, per-profile counts |
| `GET /history.json` | Last 30 days of scan history |
| `GET /openapi.yaml` | OpenAPI 3.0 specification |

These are static files served by GitHub Pages, updated after each daily scan.

**Crosscheck status values:** `passed`, `passed_retry`, `consistent`, `best_of_two`, `error`

---

## Common Issues and Solutions

### Scan Not Running

1. Check GitHub Actions tab for errors
2. Verify GitHub hasn't disabled workflows (60-day inactivity rule)
3. Run `python autofix.py` locally and push to re-enable
4. Check `keep-alive.yml` is scheduled correctly

### Email Not Sending

1. Verify `EMAIL_PASSWORD` secret in GitHub Secrets (Settings → Secrets → Actions)
2. Password must be 16 chars, no spaces (Gmail App Password, not account password)
3. Gmail requires 2FA enabled to generate App Passwords
4. Test locally: `EMAIL_PASSWORD=<your_password> python email_report.py`

### Dashboard Not Updating

1. Check if `data/dashboard_data.json` was updated (check last commit timestamp)
2. GitHub Pages may have cache — hard refresh (Ctrl+Shift+R)
3. Verify GitHub Pages is configured: Settings → Pages → Source: `main` branch, `/docs` folder

### Scraping Failures

1. OLX may have updated their HTML selectors — check `scraper.py` CSS selectors
2. Playwright may need browser update: `playwright install chromium`
3. Rate limiting (HTTP 429) — retry logic handles this automatically

---

## Branching and Deployment

- **Main branch:** `master`
- **Deployment:** Push to `master` → GitHub Pages auto-deploys from `/docs`
- **Data updates:** GitHub Actions commits directly to `master` after each scan
- **No staging environment** — changes go directly to production

When making changes:
1. Work on a feature branch
2. Test locally with `python scraper.py`
3. Merge to `master`
4. GitHub Pages deploys automatically

---

## Project Scale and Performance

- **Scan duration:** ~145 seconds for 7 profiles
- **Data size:** JSON ~569 KB, Excel ~2.1 MB (grows ~100 KB/month)
- **Polling frequency:** Daily at ~9:00 CET
- **Dashboard refresh:** Auto-refresh every 5 minutes (client-side fetch)
- **GitHub API rate limit:** 5,000 requests/hour for manual scan triggers

---

## Documentation Files Reference

| File | Purpose |
|------|---------|
| `README.md` | Main user-facing documentation |
| `SETUP_GUIDE.md` | Step-by-step GitHub Actions setup |
| `PROJECT_STRUCTURE.md` | Architecture and data flow diagrams |
| `QUICK_REFERENCE.md` | Command cheatsheet |
| `TROUBLESHOOTING.md` | Common issues and solutions |
| `docs/api/README.md` | REST API documentation for mobile developers |
| `docs/SCAN_TIMING_FIX.md` | GitHub Actions timezone/timing notes |
