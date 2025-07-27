import os
import base64
import requests
import threading
from datetime import datetime, timedelta, timezone
from flask import current_app
from exceptions import EbayAuthError

# Global token cache with thread safety
token_cache = {
    "access_token": None,
    "expires_at": datetime.min.replace(tzinfo=timezone.utc)
}
token_lock = threading.Lock()

def get_ebay_access_token() -> str:
    """Get eBay OAuth access token with proper caching"""
    global token_cache, token_lock
    
    current_time = datetime.now(timezone.utc)
    
    # Check if we have a valid cached token
    with token_lock:
        if token_cache["access_token"] and current_time < token_cache["expires_at"]:
            return token_cache["access_token"]
    
    # Get credentials from app config
    client_id = current_app.config.get("EBAY_CLIENT_ID")
    client_secret = current_app.config.get("EBAY_CLIENT_SECRET")
    scope = current_app.config.get("EBAY_SCOPE", "https://api.ebay.com/oauth/api_scope")
    
    if not client_id or not client_secret:
        missing = []
        if not client_id: missing.append("EBAY_CLIENT_ID")
        if not client_secret: missing.append("EBAY_CLIENT_SECRET")
        raise EbayAuthError(f"Missing credentials: {', '.join(missing)}")

    # Create Basic Auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    payload = {"grant_type": "client_credentials", "scope": scope}

    try:
        response = requests.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers=headers,
            data=payload,
            timeout=10
        )
        response.raise_for_status()
        token_data = response.json()
    except requests.RequestException as e:
        raise EbayAuthError(f"Token request failed: {str(e)}") from e

    if "access_token" not in token_data or "expires_in" not in token_data:
        raise EbayAuthError("Invalid token response: missing required fields")

    # Update cache with new token
    with token_lock:
        token_cache["access_token"] = token_data["access_token"]
        token_cache["expires_at"] = current_time + timedelta(
            seconds=token_data["expires_in"] - 60  # 60-second buffer
        )
    
    return token_cache["access_token"]