"""
Configuration for OFO email pipeline.
Fill in AZURE_CLIENT_ID and AZURE_TENANT_ID after creating your Azure app registration.
ANTHROPIC_API_KEY should be set as an environment variable.
"""

# ── Azure AD App Registration ────────────────────────────────────────────────
# Create an app registration in Azure Portal → App registrations:
#   1. Set "Supported account types" to your org (single tenant)
#   2. Under Authentication → Advanced → "Allow public client flows" = Yes
#   3. Under API Permissions → Add: Microsoft Graph → Delegated → Mail.Read
#   4. Grant admin consent (or have your admin do it)
AZURE_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
AZURE_TENANT_ID = "YOUR_TENANT_ID_HERE"

# ── Microsoft Graph Scopes ───────────────────────────────────────────────────
GRAPH_SCOPES = ["Mail.Read"]

# ── Token Cache ──────────────────────────────────────────────────────────────
# Tokens are cached to this file so you don't re-auth every run.
TOKEN_CACHE_FILE = ".token_cache.json"

# ── Email Search Window ──────────────────────────────────────────────────────
EMAIL_LOOKBACK_HOURS = 48

# ── Claude API ───────────────────────────────────────────────────────────────
# Anthropic's most capable generally available model as of 2026-05-18.
# Bumped from claude-sonnet-4-20250514 (which retires 2026-06-15) on 2026-05-18.
CLAUDE_MODEL = "claude-opus-4-7"

# ── Output ───────────────────────────────────────────────────────────────────
OUTPUT_FILE = "pipeline_status.json"

# ── Pipelines to monitor ────────────────────────────────────────────────────
PIPELINES = [
    "NGPL",
    "NNG",
    "Panhandle Eastern",
    "MRT",
    "CIG",
    "ANR",
    "TIGT",
    "Southern Star",
    "Northern Border",
]
