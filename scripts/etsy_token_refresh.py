"""
Etsy token refresh helper.
Called automatically before any Etsy API request in publish.py.
Access tokens expire after 1 hour — this keeps them fresh.
"""

import os
import json
import requests

KEYSTRING     = os.getenv("ETSY_API_KEY")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
REFRESH_TOKEN = os.getenv("ETSY_REFRESH_TOKEN")


def get_fresh_token():
    """
    Exchange refresh token for a new access token.
    Call this at the start of every publish run.
    Refresh tokens last 90 days — each refresh gives a new one too.
    """
    if not REFRESH_TOKEN:
        print("No refresh token found — using static access token")
        return os.getenv("ETSY_ACCESS_TOKEN")

    url     = "https://api.etsy.com/v3/public/oauth/token"
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     KEYSTRING,
        "refresh_token": REFRESH_TOKEN
    }
    headers = {
        "x-api-key":    f"{KEYSTRING}:{SHARED_SECRET}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=payload, headers=headers)
    result   = response.json()

    if "access_token" in result:
        print(f"  Etsy token refreshed successfully")
        # Note: also save new refresh token to GitHub Secrets via API
        # For now print it so you can update manually if needed
        print(f"  New refresh token (update GitHub Secret if changed): {result['refresh_token'][:30]}...")
        return result["access_token"]
    else:
        print(f"  Token refresh failed: {result}")
        print(f"  Falling back to stored access token")
        return os.getenv("ETSY_ACCESS_TOKEN")


if __name__ == "__main__":
    token = get_fresh_token()
    print(f"Fresh token: {token[:30]}..." if token else "Failed")
