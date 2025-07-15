import requests
import logging
from auth import get_ebay_access_token

logger = logging.getLogger(__name__)

def fetch_ebay_listings(product_name, entries_per_page=100, page_number=1, max_retries=3):
    for attempt in range(max_retries):
        try:
            access_token = get_ebay_access_token()
            url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={product_name}&limit={entries_per_page}&offset={(page_number - 1) * entries_per_page}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 401 and attempt < max_retries - 1:
                logger.info("Refreshing expired access token")
                continue
            logger.error(f"eBay API error: {err.response.text if hasattr(err, 'response') else str(err)}")
            raise
        except requests.exceptions.RequestException as ex:
            logger.error(f"Network error: {str(ex)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying... ({attempt + 1}/{max_retries})")
                continue
            raise
    raise ConnectionError("Max retries exceeded for eBay API")