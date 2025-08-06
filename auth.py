import os
import base64
import requests
import threading
import logging
from datetime import datetime, timedelta, timezone
from exceptions import EbayAuthError

# Configure logging
logger = logging.getLogger(__name__)

# Token cache with thread safety
token_cache = {
    "access_token": None,
    "expires_at": datetime.min.replace(tzinfo=timezone.utc)
}
token_lock = threading.Lock()

def get_ebay_access_token() -> str:
    """Get eBay OAuth token with enhanced error handling and debugging"""
    global token_cache, token_lock
    
    current_time = datetime.now(timezone.utc)
    
    # Check cache first (with lock to ensure thread safety)
    with token_lock:
        if token_cache["access_token"] and current_time < token_cache["expires_at"]:
            return token_cache["access_token"]
    
    # Verify configuration from environment variables
    client_id = os.getenv('EBAY_CLIENT_ID')
    client_secret = os.getenv('EBAY_CLIENT_SECRET')
    scope = os.getenv('EBAY_SCOPE', 'https://api.ebay.com/oauth/api_scope')

    if not client_id or not client_secret:
        raise EbayAuthError("Empty credentials detected - check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET environment variables")
    
    # Prepare authentication
    auth_string = f"{client_id}:{client_secret}"
    try:
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
    except Exception as e:
        raise EbayAuthError(f"Base64 encoding failed: {str(e)}")

    # Log authentication attempt (without exposing full credentials)
    logger.info(f"Attempting eBay OAuth with Client ID: {client_id[:5]}...{client_id[-5:]}")

    # Double-checked locking pattern with proper implementation
    with token_lock:
        # Check cache again after acquiring lock
        if token_cache["access_token"] and current_time < token_cache["expires_at"]:
            return token_cache["access_token"]
            
        try:
            response = requests.post(
                "https://api.ebay.com/identity/v1/oauth2/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {encoded_auth}"
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": scope
                },
                timeout=15
            )
            
            # Detailed error diagnostics
            if response.status_code != 200:
                error_msg = (f"eBay API Error {response.status_code}: {response.text}\n"
                        f"Request Headers: {dict(response.request.headers)}\n"
                        f"Request Body: {response.request.body}")
                logger.error(error_msg)
                raise EbayAuthError(f"eBay API Error {response.status_code}: {response.text}")

            token_data = response.json()
            
            if not all(k in token_data for k in ("access_token", "expires_in")):
                raise EbayAuthError("Invalid token response format")

            # Update cache with buffer
            token_cache["access_token"] = token_data["access_token"]
            token_cache["expires_at"] = current_time + timedelta(
                seconds=int(token_data["expires_in"]) - 120  # 2 minute buffer
            )
            
            logger.info(f"Successfully obtained eBay access token, expires in {token_data['expires_in']} seconds")
            return token_cache["access_token"]
            
        except requests.RequestException as e:
            logger.error(f"Network error during eBay OAuth: {str(e)}")
            raise EbayAuthError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during eBay OAuth: {str(e)}")
            raise EbayAuthError(f"Unexpected error: {str(e)}")

def clear_token_cache():
    """Clear the token cache (useful for testing or manual refresh)"""
    global token_cache, token_lock
    
    with token_lock:
        token_cache["access_token"] = None
        token_cache["expires_at"] = datetime.min.replace(tzinfo=timezone.utc)
        logger.info("eBay token cache cleared")

def get_token_info():
    """Get information about the current token (for debugging)"""
    global token_cache, token_lock
    
    with token_lock:
        current_time = datetime.now(timezone.utc)
        is_valid = token_cache["access_token"] and current_time < token_cache["expires_at"]
        
        return {
            "has_token": bool(token_cache["access_token"]),
            "is_valid": is_valid,
            "expires_at": token_cache["expires_at"].isoformat() if token_cache["expires_at"] else None,
            "current_time": current_time.isoformat()
        }