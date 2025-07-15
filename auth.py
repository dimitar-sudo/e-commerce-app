# auth.py (modified version)
import os
import base64
import threading
import requests
from datetime import datetime, timedelta, timezone
from flask import g, current_app

class EbayAuthError(Exception):
    """Custom exception for eBay authentication errors"""
    pass

def get_ebay_access_token() -> str:
    """Retrieve eBay OAuth access token with caching and automatic renewal"""
    # Check if we already have a valid token in this request context
    if 'ebay_token' in g and g.ebay_token["expires_at"] > datetime.now(timezone.utc):
        return g.ebay_token["access_token"]
    
    # Initialize token structure in app context if needed
    if 'ebay_token' not in g:
        g.ebay_token = {
            "access_token": None,
            "expires_at": datetime.min.replace(tzinfo=timezone.utc)
        }
    
    # Use lock only for the current request context
    if 'token_lock' not in g:
        g.token_lock = threading.Lock()
    
    with g.token_lock:
        current_time = datetime.now(timezone.utc)
        
        # Double-check after acquiring lock
        if g.ebay_token["access_token"] and current_time < g.ebay_token["expires_at"]:
            return g.ebay_token["access_token"]
        
        # Get credentials from Flask config (safer than dotenv)
        client_id = current_app.config.get("EBAY_CLIENT_ID")
        client_secret = current_app.config.get("EBAY_CLIENT_SECRET")
        scope = current_app.config.get("EBAY_SCOPE", "https://api.ebay.com/oauth/api_scope")
        
        if not client_id or not client_secret:
            missing = []
            if not client_id: missing.append("EBAY_CLIENT_ID")
            if not client_secret: missing.append("EBAY_CLIENT_SECRET")
            raise EbayAuthError(
                f"Missing credentials: {', '.join(missing)}\n"
                "Set them in your Flask app configuration"
            )

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
        except ValueError as e:
            raise EbayAuthError("Invalid JSON response") from e

        if "access_token" not in token_data or "expires_in" not in token_data:
            raise EbayAuthError("Invalid token response: missing required fields")

        # Update token in request context
        g.ebay_token["access_token"] = token_data["access_token"]
        g.ebay_token["expires_at"] = current_time + timedelta(
            seconds=token_data["expires_in"] - 60  # 60-second buffer
        )
        
        return g.ebay_token["access_token"]