import os
import base64
import threading
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Token cache and lock for thread safety
_cached_token = {
    "access_token": None,
    "expires_at": datetime.min.replace(tzinfo=timezone.utc)  # Timezone-aware initial state
}
_token_lock = threading.Lock()

class EbayAuthError(Exception):
    """Custom exception for eBay authentication errors"""
    pass

def get_ebay_access_token() -> str:
    """Retrieve eBay OAuth access token with caching and automatic renewal"""
    global _cached_token
    current_time = datetime.now(timezone.utc)  # Timezone-aware current time

    # First check (non-blocking)
    if _cached_token["access_token"] and current_time < _cached_token["expires_at"]:
        return _cached_token["access_token"]

    # Thread-safe refresh section
    with _token_lock:
        # Re-check after acquiring lock
        current_time = datetime.now(timezone.utc)  # Refresh current time
        if _cached_token["access_token"] and current_time < _cached_token["expires_at"]:
            return _cached_token["access_token"]

        # Fetch credentials with explicit .env loading
        script_dir = Path(__file__).parent.absolute()
        env_path = script_dir / '.env'
        
        # Try to load .env file if exists
        try:
            from dotenv import load_dotenv
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                print(f"Loaded .env from: {env_path}")
            else:
                print(".env file not found in script directory")
        except ImportError:
            pass  # Proceed without dotenv

        client_id = os.getenv("EBAY_CLIENT_ID")
        client_secret = os.getenv("EBAY_CLIENT_SECRET")
        scope = os.getenv("EBAY_SCOPE", "https://api.ebay.com/oauth/api_scope")
        
        # Detailed error reporting
        missing = []
        if not client_id:
            missing.append("EBAY_CLIENT_ID")
        if not client_secret:
            missing.append("EBAY_CLIENT_SECRET")
        
        if missing:
            env_location = env_path if env_path.exists() else "environment variables"
            raise EbayAuthError(
                f"Missing credentials: {', '.join(missing)}\n"
                f"Please create a .env file at {env_path} with these variables or "
                "set them in your environment."
            )

        # Prepare request
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        payload = {"grant_type": "client_credentials", "scope": scope}

        # Execute request
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

        # Validate response
        if "access_token" not in token_data or "expires_in" not in token_data:
            raise EbayAuthError("Invalid token response: missing required fields")

        # Update cache with safety buffer using timezone-aware datetime
        _cached_token["access_token"] = token_data["access_token"]
        _cached_token["expires_at"] = current_time + timedelta(
            seconds=token_data["expires_in"] - 60
        )

        return _cached_token["access_token"]