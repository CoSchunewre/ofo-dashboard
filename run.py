#!/usr/bin/env python3
"""
OFO Email Pipeline — Main Entry Point

Authenticates with Microsoft Graph, fetches OFO-related emails,
parses them with Claude, and writes pipeline_status.json.

Usage:
    python run.py
"""

import json
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on the path so config + ofo_pipeline are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from ofo_pipeline.auth import get_access_token
from ofo_pipeline.fetch_emails import fetch_ofo_emails, match_emails_to_pipelines
from ofo_pipeline.parse_emails import parse_emails_for_pipeline


def main():
    print("=" * 60)
    print("  OFO EMAIL PIPELINE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── Preflight checks ─────────────────────────────────────────────────
    if config.AZURE_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        print("\nERROR: Set AZURE_CLIENT_ID in config.py")
        sys.exit(1)
    if config.AZURE_TENANT_ID == "YOUR_TENANT_ID_HERE":
        print("\nERROR: Set AZURE_TENANT_ID in config.py")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nERROR: Set the ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    # ── Step 1: Authenticate ─────────────────────────────────────────────
    print("\n[1/4] Authenticating with Microsoft Graph...")
    token = get_access_token()
    print("       Done.")

    # ── Step 2: Fetch emails ─────────────────────────────────────────────
    print(f"\n[2/4] Fetching emails from the last {config.EMAIL_LOOKBACK_HOURS} hours...")
    emails = fetch_ofo_emails(token)
    print(f"       Found {len(emails)} OFO-related emails.")

    # ── Step 3: Match & parse per pipeline ───────────────────────────────
    print("\n[3/4] Parsing emails per pipeline with Claude...")
    pipeline_emails = match_emails_to_pipelines(emails)

    results = {}
    for pipeline_name in config.PIPELINES:
        matched = pipeline_emails.get(pipeline_name, [])
        tag = f"  {pipeline_name:<20}"

        if matched:
            print(f"{tag} → {len(matched)} email(s), parsing...")
            parsed = parse_emails_for_pipeline(pipeline_name, matched)
        else:
            print(f"{tag} → no emails found")
            parsed = {
                "pipeline_name": pipeline_name,
                "ofo_type": "None",
                "status": "NO OFO",
                "effective_start": None,
                "effective_end": None,
                "notice_id": None,
                "summary": f"No OFO-related notices found for {pipeline_name}.",
            }

        results[pipeline_name] = parsed

    # ── Step 4: Write JSON ───────────────────────────────────────────────
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.OUTPUT_FILE)
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "pipelines": results,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[4/4] Wrote {output_path}")

    # ── Summary ──────────────────────────────────────────────────────────
    active = [name for name, r in results.items() if r["status"] not in ("NO OFO", "Resolved")]
    print("\n" + "=" * 60)
    if active:
        print(f"  ⚠  ACTIVE OFOs: {', '.join(active)}")
    else:
        print("  ✓  No active OFOs across all 9 pipelines.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
