"""
Microsoft Graph API authentication using MSAL device code flow.
Caches tokens to disk so re-auth is only needed when the refresh token expires.
"""

import json
import os
import sys

import msal

import config


def _build_app():
    """Build an MSAL public client application with persistent token cache."""
    cache = msal.SerializableTokenCache()
    cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.TOKEN_CACHE_FILE)

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        client_id=config.AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}",
        token_cache=cache,
    )
    return app, cache, cache_path


def _save_cache(cache, cache_path):
    """Persist the token cache if it changed."""
    if cache.has_state_changed:
        with open(cache_path, "w") as f:
            f.write(cache.serialize())


def get_access_token():
    """
    Acquire a Microsoft Graph access token.
    Tries the cache first; falls back to device code flow if needed.
    Returns the access token string.
    """
    app, cache, cache_path = _build_app()

    # Try silent acquisition from cache
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(config.GRAPH_SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache, cache_path)
            return result["access_token"]

    # No cached token — use device code flow
    flow = app.initiate_device_flow(scopes=config.GRAPH_SCOPES)
    if "user_code" not in flow:
        print("ERROR: Could not initiate device code flow.")
        print(json.dumps(flow, indent=2))
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  MICROSOFT SIGN-IN REQUIRED")
    print("=" * 60)
    print(f"  1. Open:  {flow['verification_uri']}")
    print(f"  2. Enter: {flow['user_code']}")
    print("=" * 60)
    print("  Waiting for you to sign in...\n")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        print("ERROR: Authentication failed.")
        print(result.get("error_description", result))
        sys.exit(1)

    _save_cache(cache, cache_path)
    print("  ✓ Authenticated successfully.\n")
    return result["access_token"]
