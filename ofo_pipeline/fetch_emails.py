"""
Fetch OFO-related emails from Microsoft Graph API.
Searches the user's inbox for the last 48 hours of messages
matching pipeline OFO keywords in the subject line.
"""

from datetime import datetime, timedelta, timezone

import requests

import config


# Keywords that indicate an email is OFO-related
OFO_KEYWORDS = [
    "OFO",
    "Operational Flow Order",
    "System Overrun Limitation",
    "SOL",
    "System Underrun Limitation",
    "SUL",
    "Operational Alert",
    "Critical Notice",
    "Strained Operating",
    "Flow Order",
    "Imbalance",
]

# Pipeline name variants that may appear in email subjects
PIPELINE_ALIASES = {
    "NGPL": ["NGPL", "Natural Gas Pipeline"],
    "NNG": ["NNG", "Northern Natural Gas", "Northern Natural"],
    "Panhandle Eastern": ["PEPL", "Panhandle Eastern", "Panhandle"],
    "MRT": ["MRT", "Mississippi River Transmission"],
    "CIG": ["CIG", "Colorado Interstate"],
    "ANR": ["ANR", "ANR Pipeline"],
    "TIGT": ["TIGT", "Tallgrass"],
    "Southern Star": ["Southern Star", "SSCGP"],
    "Northern Border": ["Northern Border", "NBPL"],
}


def fetch_ofo_emails(access_token):
    """
    Fetch emails from the last EMAIL_LOOKBACK_HOURS hours that may contain
    OFO notices. Returns a list of dicts with keys: subject, body, received, sender.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.EMAIL_LOOKBACK_HOURS)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build OData filter: received after cutoff
    # We cast a wide net and filter more precisely in Python
    ofo_subject_filters = " or ".join(
        f"contains(subject, '{kw}')" for kw in OFO_KEYWORDS
    )
    filter_query = f"receivedDateTime ge {cutoff_str} and ({ofo_subject_filters})"

    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://graph.microsoft.com/v1.0/me/messages"
    params = {
        "$filter": filter_query,
        "$select": "subject,body,receivedDateTime,from",
        "$top": 100,
        "$orderby": "receivedDateTime desc",
    }

    all_emails = []

    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for msg in data.get("value", []):
            all_emails.append({
                "subject": msg.get("subject", ""),
                "body": msg.get("body", {}).get("content", ""),
                "body_type": msg.get("body", {}).get("contentType", "text"),
                "received": msg.get("receivedDateTime", ""),
                "sender": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            })

        # Handle pagination
        url = data.get("@odata.nextLink")
        params = None  # nextLink already includes params

    return all_emails


def match_emails_to_pipelines(emails):
    """
    Group emails by pipeline. Each email may match multiple pipelines.
    Returns dict: { pipeline_name: [list of email dicts] }
    """
    result = {name: [] for name in config.PIPELINES}

    for email in emails:
        subject_upper = email["subject"].upper()
        body_upper = email["body"][:2000].upper()  # Check first 2000 chars of body too
        text = subject_upper + " " + body_upper

        for pipeline_name, aliases in PIPELINE_ALIASES.items():
            for alias in aliases:
                if alias.upper() in text:
                    result[pipeline_name].append(email)
                    break

    return result
