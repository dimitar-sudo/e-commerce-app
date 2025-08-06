import requests
import logging
from auth import get_ebay_access_token

logger = logging.getLogger(__name__)

# eBay condition filter mapping for API calls
# Updated to include all possible eBay condition values
EBAY_CONDITION_FILTERS = {
    'new': 'NEW,LIKE_NEW,NEW_OTHER,NEW_WITH_DEFECTS',
    'used': 'PRE_OWNED_EXCELLENT,USED_EXCELLENT,USED_VERY_GOOD,USED_GOOD,USED_ACCEPTABLE',
    'all': None  # No filter applied
}

# Comprehensive condition mapping for reference and future use
EBAY_ALL_CONDITIONS = {
    'new': [
        'NEW',
        'LIKE_NEW', 
        'NEW_OTHER',
        'NEW_WITH_DEFECTS'
    ],
    'used': [
        'PRE_OWNED_EXCELLENT',
        'USED_EXCELLENT',
        'USED_VERY_GOOD', 
        'USED_GOOD',
        'USED_ACCEPTABLE'
    ],
    'refurbished': [
        'CERTIFIED_REFURBISHED',
        'EXCELLENT_REFURBISHED',
        'VERY_GOOD_REFURBISHED',
        'GOOD_REFURBISHED',
        'SELLER_REFURBISHED'
    ],
    'parts_only': [
        'FOR_PARTS_OR_NOT_WORKING'
    ]
}

def fetch_ebay_listings(product_name, entries_per_page=100, page_number=1, condition='all', max_retries=3):
    for attempt in range(max_retries):
        try:
            access_token = get_ebay_access_token()
            url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={product_name}&limit={entries_per_page}&offset={(page_number - 1) * entries_per_page}"
            
            # Add condition filter if specified
            if condition != 'all' and condition in EBAY_CONDITION_FILTERS:
                filter_value = EBAY_CONDITION_FILTERS[condition]
                if filter_value:
                    url += f"&filter=conditions:{filter_value}"
                    logger.info(f"Applied condition filter '{condition}' with value '{filter_value}'")
                else:
                    logger.info(f"No filter value for condition '{condition}'")
            else:
                logger.info(f"No condition filter applied (condition: '{condition}')")
            
            logger.info(f"eBay API URL: {url}")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"eBay API returned {len(result.get('itemSummaries', []))} items")
            
            return result

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