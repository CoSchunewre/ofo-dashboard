# OFO Email Pipeline — Setup Guide

## Prerequisites

- Python 3.x (available on your machine)
- An Azure AD app registration (see below)
- `ANTHROPIC_API_KEY` environment variable set

## 1. Install dependencies

```bash
pip install --user -r requirements.txt
```

## 2. Azure App Registration

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
   - Name: `OFO Dashboard`
   - Supported account types: **Accounts in this organizational directory only** (single tenant)
   - Redirect URI: leave blank
3. After creation, copy the **Application (client) ID** and **Directory (tenant) ID**
4. Go to **Authentication** → **Advanced settings** → Set **Allow public client flows** to **Yes** → Save
5. Go to **API Permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions** → search for `Mail.Read` → Add
6. Click **Grant admin consent** (or ask your admin)

## 3. Configure

Edit `config.py` and replace the placeholders:

```python
AZURE_CLIENT_ID = "paste-your-client-id-here"
AZURE_TENANT_ID = "paste-your-tenant-id-here"
```

## 4. Set Anthropic API key

```bash
set ANTHROPIC_API_KEY=sk-ant-...
```

Or add it permanently via System Properties → Environment Variables.

## 5. First run

```bash
python run.py
```

On first run, you'll see a device code prompt:
1. Open the URL shown in the console
2. Enter the code displayed
3. Sign in with your Microsoft account
4. The token is cached to `.token_cache.json` — you won't need to sign in again until the refresh token expires (~90 days)

After successful run, `pipeline_status.json` will be written to the project root.

## 6. Schedule with Windows Task Scheduler

To run every weekday at 7:00 AM Central Time:

1. Open **Task Scheduler** (search from Start menu)
2. Click **Create Basic Task**
   - Name: `OFO Dashboard Pipeline`
   - Description: `Fetch OFO emails and update pipeline_status.json`
3. Trigger: **Weekly** → Check Mon–Fri → Start time: **7:00 AM**
4. Action: **Start a program**
   - Program/script: `python`
   - Add arguments: `run.py`
   - Start in: `C:\Users\CourtenaySchunemann\source\repos\ofo-dashboard`
5. Check **Open the Properties dialog** → Finish
6. In Properties:
   - Under **General**: check "Run whether user is logged on or not"
   - Under **Settings**: check "Run task as soon as possible after a scheduled start is missed"

**Important:** The task needs the `ANTHROPIC_API_KEY` environment variable available. Since Task Scheduler runs in a separate session, ensure the variable is set as a **System** environment variable (not just User), or add it as a `set` command in a wrapper batch file:

### Wrapper batch file (optional)

Create `run_ofo.bat` in the project directory:

```batch
@echo off
set ANTHROPIC_API_KEY=sk-ant-your-key-here
cd /d "C:\Users\CourtenaySchunemann\source\repos\ofo-dashboard"
python run.py >> ofo_log.txt 2>&1
```

Then point Task Scheduler at `run_ofo.bat` instead of `python run.py`.

## 7. Deploy to GitHub Pages

After each run, commit and push `pipeline_status.json` alongside `index.html`:

```bash
git add pipeline_status.json index.html
git commit -m "Update OFO status"
git push
```

The dashboard at `https://coschunewre.github.io/ofo-dashboard/` will then load the fresh JSON.

To automate the push, add these lines to the end of `run_ofo.bat`:

```batch
git add pipeline_status.json
git commit -m "Auto-update OFO status %date% %time%"
git push
```

## File structure

```
ofo-dashboard/                          (canonical clone, not in OneDrive)
├── config.py                           # Azure + Claude configuration
├── run.py                              # Main entry point
├── requirements.txt                    # Python dependencies (msal, requests, anthropic)
├── ofo_pipeline/
│   ├── __init__.py
│   ├── auth.py                         # Microsoft Graph device code auth
│   ├── fetch_emails.py                 # Email fetching via Graph API
│   └── parse_emails.py                 # Claude API email parsing
├── index.html                          # CURRENT live dashboard (EBB-scraping, will retire)
├── index.email-pipeline.html           # NEW dashboard variant — reads pipeline_status.json
├── pipeline_ofo_dashboard.html         # Older dashboard iteration (kept for reference)
├── ofo_worker.js                       # Cloudflare Worker source (legacy, EBB-era)
├── pipeline_status.json                # Generated output (after first run)
├── .token_cache.json                   # MSAL token cache (DO NOT commit — gitignored)
├── EMAIL_PIPELINE_KICKOFF.md           # Project kickoff for Claude Code sessions
├── SETUP.md                            # This file
└── README.md                           # Repo overview
```
