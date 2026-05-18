# Claude Code Kickoff Prompt — OFO Email Pipeline

> Paste this entire document into a fresh Claude Code session at the start of work on the email pipeline.

---

## What you're building

WoodRiver Energy maintains an **OFO Notice Dashboard** that monitors 9 natural gas pipelines for Operational Flow Order notices. The current implementation scrapes each pipeline's public Electronic Bulletin Board (EBB) live via a Cloudflare Worker. That approach has run into a structural wall: several EBBs (Northern Border via TC eConnects, Tallgrass, ET Messenger, Southern Star, Kinder Morgan in part) render their notice tables via JavaScript in nested ASP.NET iframes that plain HTTP fetch cannot see. As of 2026-05-18 the Northern Border card on the live dashboard explicitly says "VERIFY EBB — this EBB can't be auto-checked" because we proved scraping won't work.

**This project replaces the entire EBB-scraping layer with email-based ingestion.** Each pipeline operator emails critical notices to Courtenay's mailbox (`Courtenay.Schunemann@woodriverenergy.com`). A Python pipeline pulls those emails via the Microsoft Graph API, parses them with the Claude API, and writes a `pipeline_status.json` file that a refreshed dashboard reads. Once live, the EBB-scraping path in the current dashboard can be retired.

- **Current live dashboard:** https://coschunewre.github.io/ofo-dashboard/
- **GitHub repo:** https://github.com/CoSchunewre/ofo-dashboard
- **Canonical clone (this is where you should work):** `C:\Users\CourtenaySchunemann\source\repos\ofo-dashboard` — both the dashboard and the email-pipeline scaffold live here. Moved out of OneDrive on 2026-05-18 to keep `.git` out of OneDrive sync.

## Architecture

```
[Pipeline operators]
   email critical notices → Courtenay's Outlook
                                  │
                                  ▼
        [Scheduled Task: run.py, e.g. 7am CT weekdays]
                                  │
                  ┌───────────────┼────────────────┐
                  ▼               ▼                ▼
            auth.py         fetch_emails.py   parse_emails.py
        (MSAL device   →   (Graph API,   →   (Claude API,
         code flow,         48hr window)     structured JSON)
         token cached)
                                  │
                                  ▼
                       pipeline_status.json
                                  │
                                  ▼
                    git commit + push to main
                                  │
                                  ▼
                  GitHub Pages serves index.html
                  which fetches pipeline_status.json
                  and renders pipeline cards
```

There is **no live web server in this design.** The dashboard remains a static page on GitHub Pages; it just reads a JSON file instead of scraping. All processing happens on Courtenay's local machine via Windows Task Scheduler.

## Files in the scaffold (already written, 4/7/2026 — over a month stale)

```
OFO-dashboard/
├── config.py                       # Azure + Claude config, pipeline list
├── run.py                          # Main entry point — orchestrates the four steps
├── requirements.txt                # msal, requests, anthropic
├── SETUP.md                        # Setup guide (Azure registration walkthrough)
├── ofo_pipeline/
│   ├── __init__.py
│   ├── auth.py                     # MSAL device-code flow + token caching
│   ├── fetch_emails.py             # Graph API fetch, keyword/pipeline matching
│   └── parse_emails.py             # Claude API parsing with OFO-specific prompt
├── index.email-pipeline.html       # Dashboard variant that reads pipeline_status.json
└── pipeline_ofo_dashboard.html     # Older iteration (3/25) — superseded by above, can probably retire
```

Treat the existing Python as starting code, not gospel. It hasn't been run end-to-end yet — Azure registration was never completed.

## Output schema (pipeline_status.json)

```json
{
  "last_updated": "2026-05-18T13:00:00+00:00",
  "pipelines": {
    "NGPL": {
      "pipeline_name": "NGPL",
      "ofo_type": "OFO" | "Watch" | "Operational Alert" | "SOL" | "SUL" | "None",
      "status": "Active" | "NO OFO",
      "effective_start": "2026-05-18T05:00:00-05:00" | null,
      "effective_end": "2026-05-19T05:00:00-05:00" | null,
      "notice_id": "123014" | null,
      "summary": "1-2 sentence plain English description"
    },
    ...
  }
}
```

Note `status` is **already normalized** to either "Active" or "NO OFO" by the time it reaches the JSON. `parse_emails.py` collapses Claude's "Resolved" output into "NO OFO" so the dashboard never has to know about transitions — it just renders state.

## Invariants — these must be preserved

These come from the existing dashboard's product rules. Anything that changes them needs Courtenay's explicit sign-off.

1. **Carlton Resolution notices on NNG are ALWAYS excluded.** Both `fetch_emails.py` and `parse_emails.py` need to drop these regardless of status. The current `parse_emails.py` system prompt handles this; verify nothing slips past the email-fetch filter.
2. **NNG SOL, SUL, and Operational Alert** notices are treated as OFO-level events. Already encoded in the parser prompt.
3. **Resolved/Terminated/Lifted/Rescinded/Cancelled status → NO OFO.** The existing parser collapses this on the way out. Cancellation-of notices specifically (e.g. CIG's "Cancellation of Strained Operating Cond" we fixed 2026-05-14) must be treated as resolved even when the email itself is a fresh "Initiate" of a cancellation notice. The Claude prompt currently relies on the model figuring this out — worth testing against a real cancellation email.
4. **On parse/fetch failure, a pipeline must show NO OFO — never an error state.** This intentionally avoids false alarms from transient Graph API outages. The existing `parse_emails.py` already returns a default NO OFO entry on any exception. Don't change this without discussion.
   - **Exception:** if the email pipeline has been UNABLE TO RUN for a long time (no `pipeline_status.json` update for >24h), the dashboard should show a system-wide "stale data" warning rather than confident NO OFOs. Not yet implemented in the dashboard side. Worth designing in.
5. **Pipelines monitored (9):** NGPL, NNG, Panhandle Eastern, MRT, CIG, ANR, TIGT, Southern Star, Northern Border. Already in `config.py`. Don't add or remove without explicit ask.

## Things discovered during the EBB-scraping era — fold these in

These are real-world quirks observed in the dashboard's parsing logic that should inform the email parser too:

- **OFO keyword variations we know exist in real notices:** `OFO`, `Operational Flow Order`, `Flow Order`, `Strained Operating` (the EBBs actually use "Strained" with an 'i', not "Stranded"), `Critical Notice`, `Imbalance Warning`, `Underperformance`, `Under-Performance`, `Under Performance`, `High Inventory OFO`, `Low Inventory OFO`. The current `OFO_KEYWORDS` list in `fetch_emails.py` is missing `Underperformance` / `Under Performance` / `High Inventory` / `Low Inventory` / `Cancellation` — add these on day one.
- **Pipeline name variants** in `PIPELINE_ALIASES` look mostly right but check that real emails from each pipeline match. Some pipelines email from a third-party service (e.g. ET Messenger, TC eConnects forwarders) and the sender name may not contain the pipeline name. Subject lines are more reliable.
- **CIG and NGPL share a Kinder Morgan EBB structure** and likely share email templates too. If you fix one's parsing, audit the other.
- **NNG's email cadence is the heaviest** because of how operational alerts get classified. Expect more noise per refresh.

## Current state of completion

| Done | Not done |
|---|---|
| All Python modules written | Azure App Registration (placeholder values in `config.py`) |
| MSAL device-code auth flow | First-run authentication never attempted |
| Graph API fetch with OData filter | `ANTHROPIC_API_KEY` env var not set |
| Pipeline-to-email matching | No `pipeline_status.json` has ever been produced |
| Claude API parsing with OFO-aware prompt | Dashboard `index.html` not yet pointed at JSON (current live one still scrapes) |
| Fail-silent default → NO OFO | Task Scheduler entry not created |
| `index.email-pipeline.html` reads `pipeline_status.json` | EBB-scraping layer in current `index.html` not yet decommissioned |
| `SETUP.md` walkthrough for Azure + scheduling | Real OFO email samples haven't been tested against the parser |

## Things to think about before deploying

- **Azure App Registration may need admin consent.** WoodRiver IT may or may not have a policy here. `SETUP.md` step 6 covers this. If admin consent is blocked, the project is blocked until it's resolved — get this conversation started early.
- **Email subscriptions need to exist.** This pipeline is only useful if Courtenay's mailbox actually receives critical notices from each of the 9 pipelines. Verify for each pipeline (especially the JS-rendered ones — Northern Border, Tallgrass, Southern Star) that emails are arriving. If any pipeline isn't sending email, you'll need to subscribe through their EBB or work with their customer service.
- **`CLAUDE_MODEL` is set to `claude-opus-4-7`** (bumped from `claude-sonnet-4-20250514` on 2026-05-18 — the prior model retires 2026-06-15). Opus is overkill for short structured-extraction prompts, but at this volume (9 calls/day) cost is trivial (~$0.02/day worst case). If you ever scale this up materially, downgrade to `claude-sonnet-4-6` and re-test.
- **`pipeline_ofo_dashboard.html` (31 KB, dated 3/25/2026)** is from before `index.email-pipeline.html`. Courtenay opted to keep it for reference for now (decision made 2026-05-18); revisit retirement later.
- **Once the email pipeline is live, the EBB-scraping layer can be retired.** The current `index.html` and `ofo_worker.js` would become dead code. But run them in parallel for a few weeks before decommissioning — false negatives in the new system are operationally expensive, so keep the redundancy until you've calibrated.

## Maintenance / debugging methodology

1. **Read the entire scaffold end-to-end before editing.** `config.py`, `run.py`, all three modules in `ofo_pipeline/`, and `SETUP.md`. The scaffold is small (~600 LOC total) so this is cheap.
2. **For any change to the OFO parser:** before editing the Claude prompt or keyword lists, run `run.py` once on real emails and look at what comes back. Don't iterate on the parser blind.
3. **Token cache file (`.token_cache.json`)** is git-ignored — must NEVER be committed. Worth adding it to `.gitignore` explicitly before any git work.
4. **Anthropic API key** must NEVER end up in `config.py` or any committed file. Always read from `os.environ`.
5. **Run failures should not break the dashboard.** If `run.py` crashes, the previous `pipeline_status.json` is still in the repo and the dashboard keeps rendering yesterday's data. This is by design; the dashboard's `last_updated` timestamp lets users see stale data is stale.
6. **Test each pipeline individually** — temporarily edit `config.PIPELINES` to just `["NGPL"]` while iterating on a specific parser issue. Saves API budget and noise.

## First action for Claude Code

Do these in order, without making any edits:

1. **Read the existing scaffold end-to-end.** All of `config.py`, `run.py`, `ofo_pipeline/auth.py`, `ofo_pipeline/fetch_emails.py`, `ofo_pipeline/parse_emails.py`, `SETUP.md`. Note any assumptions that look brittle, any places where the invariants above aren't enforced, and any code that's been written but not used.
2. **Read `index.email-pipeline.html`** end-to-end. Map out exactly which JSON fields it reads, how it renders each status, and what assumptions it makes about the schema. Cross-check against `parse_emails.py`'s output — flag any mismatch.
3. **Summarize what you found.** Specifically: (a) the JSON schema contract — does the producer (parser) match the consumer (dashboard)? (b) what's missing from the keyword lists based on the EBB-era quirks above? (c) is `index.email-pipeline.html` actually a drop-in replacement for the current `index.html`, or does it need work?
4. **Then ask Courtenay** about the one remaining open question:
   - **Has the Azure App Registration been completed yet?** If yes, dive into running `run.py` — the device-code flow will prompt for sign-in. If no, work with Courtenay on the walkthrough in `SETUP.md` step 2 of "Azure App Registration"; admin consent may be required from WoodRiver IT.

Don't write code until that's answered. The scaffold is real work and shouldn't be redirected on autopilot.

---

## Reference materials (from the EBB-era project memory)

- Today's date: 2026-05-18
- Live dashboard: https://coschunewre.github.io/ofo-dashboard/
- GitHub repo: https://github.com/CoSchunewre/ofo-dashboard
- Recent commits (relevant context for what the dashboard currently does):
  - `9f0da12` Fix ANR: route fetch failures to NO OFO per documented invariant
  - `b441371` Fix CIG: treat "Cancellation of …" notices as resolved
  - `95145d4` Fix Northern Border: detect Underperformance OFO notices
  - `c06a1a7` Add ofo_worker.js to repo and document manual Cloudflare deploy
  - `ae729ad` Show VERIFY EBB on Northern Border instead of false NO OFO
- Cloudflare Worker (current EBB-era CORS proxy, will become irrelevant once email pipeline ships): https://ofo-proxy.courtenay-schunemann.workers.dev
- Pipeline-specific notice URL formats and other EBB-era quirks are documented in `~/.claude/projects/<this-project>/memory/` if needed.
