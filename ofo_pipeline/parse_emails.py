"""
Parse OFO email bodies using the Claude API to extract structured notice data.
"""

import json
import os
import re

import anthropic

import config

# HTML tag stripper for cleaner input to Claude
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text):
    """Remove HTML tags and collapse whitespace."""
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return _WS_RE.sub(" ", text).strip()


def _truncate(text, max_chars=8000):
    """Truncate text to fit within Claude's practical input budget."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... truncated]"


SYSTEM_PROMPT = """\
You are a natural gas pipeline OFO (Operational Flow Order) notice parser.
You will receive one or more email bodies related to a specific pipeline.
Extract structured OFO status information.

RULES:
- pipeline_name: Use the exact name provided in the user message.
- ofo_type: One of "OFO", "Watch", "Operational Alert", "SOL", "SUL", or "None".
  - For NNG (Northern Natural Gas): treat SOL, SUL, and Operational Alert as OFO-level events.
  - For NNG: EXCLUDE any notice mentioning "Carlton Resolution" — ignore it entirely.
- status: "Active" if the OFO/alert is currently in effect. "Resolved" if it has been lifted, terminated, rescinded, or cancelled.
  - If the most recent email says the OFO is terminated/lifted/resolved, status = "Resolved".
  - If the most recent email initiates or continues an OFO, status = "Active".
- effective_start: ISO 8601 datetime if stated, otherwise null.
- effective_end: ISO 8601 datetime if stated, otherwise null.
- notice_id: The notice/posting ID number if present, otherwise null.
- summary: 1–2 sentence plain English description of the current situation.

Respond with ONLY valid JSON (no markdown, no explanation). Format:
{
  "pipeline_name": "...",
  "ofo_type": "...",
  "status": "...",
  "effective_start": "..." or null,
  "effective_end": "..." or null,
  "notice_id": "..." or null,
  "summary": "..."
}
"""


def parse_emails_for_pipeline(pipeline_name, emails):
    """
    Send email bodies to Claude for structured parsing.
    Returns a dict with the parsed fields, or a default NO OFO entry on failure.
    """
    default = {
        "pipeline_name": pipeline_name,
        "ofo_type": "None",
        "status": "NO OFO",
        "effective_start": None,
        "effective_end": None,
        "notice_id": None,
        "summary": f"No OFO-related notices found for {pipeline_name}.",
    }

    if not emails:
        return default

    # Build the email digest for Claude
    email_texts = []
    for i, email in enumerate(emails[:10], 1):  # Cap at 10 most recent
        body = email["body"]
        if email.get("body_type") == "html":
            body = _strip_html(body)
        body = _truncate(body)
        email_texts.append(
            f"--- Email {i} ---\n"
            f"Subject: {email['subject']}\n"
            f"From: {email['sender']}\n"
            f"Received: {email['received']}\n"
            f"Body:\n{body}\n"
        )

    user_message = (
        f"Pipeline: {pipeline_name}\n\n"
        f"Below are the most recent emails (newest first) related to this pipeline. "
        f"Determine the current OFO status.\n\n"
        + "\n".join(email_texts)
    )

    try:
        client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        parsed = json.loads(raw)

        # Validate required fields
        required = ["pipeline_name", "ofo_type", "status"]
        for field in required:
            if field not in parsed:
                return default

        # Normalize status for dashboard consumption
        if parsed["status"] == "Resolved":
            parsed["ofo_type"] = "None"
            parsed["status"] = "NO OFO"
            parsed["summary"] = parsed.get("summary", f"Previous OFO resolved for {pipeline_name}.")

        return parsed

    except (json.JSONDecodeError, anthropic.APIError, KeyError, IndexError) as e:
        # Fail silent — return NO OFO so the dashboard never shows errors
        return default
