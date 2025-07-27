import pandas as pd
import logging
from exchange import get_exchange_rate
from exceptions import ProcessingError

logger = logging.getLogger(__name__)

def process_ebay_data(data, target_currency):
    items = data.get('itemSummaries', [])
    if not items:
        logger.warning("No items found in eBay response")
        return pd.DataFrame()

    try:
        price_converter = get_exchange_rate("USD", target_currency)
    except Exception as e:
        logger.error(f"Currency conversion failed: {str(e)}")
        raise ProcessingError("Currency conversion unavailable") from e

    rows = []
    for item in items:
        try:
            price_value = item.get("price", {}).get("value")
            if price_value is None:
                logger.warning(f"Missing price for item: {item.get('itemId')}")
                continue
                
            rows.append({
                "Product Title": item.get("title"),
                "Price": round(float(price_value) * price_converter, 2),
                "Currency": target_currency,
                "Condition": item.get("condition", "Unknown"),
                "Seller Rating (%)": item.get("seller", {}).get("feedbackPercentage", "N/A"),
                "Seller Feedback Count": item.get("seller", {}).get("feedbackScore", "N/A"),
                "Item Country": item.get("itemLocation", {}).get("country", "N/A"),
                "Product URL": item.get("itemWebUrl")
            })
        except (TypeError, ValueError) as e:
            logger.error(f"Error processing item {item.get('itemId')}: {str(e)}")
            continue

    return pd.DataFrame(rows)

def sort_dataframe(df, sort_by):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
        
    sort_by = sort_by.lower()
    try:
        if 'price' in sort_by:
            ascending = 'asc' in sort_by
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
            return df.sort_values(by='Price', ascending=ascending, na_position='last')
        elif 'rating' in sort_by:
            ascending = 'asc' in sort_by
            df["Seller Rating (%)"] = pd.to_numeric(
                df["Seller Rating (%)"], 
                errors="coerce"
            )
            return df.sort_values(by="Seller Rating (%)", ascending=ascending, na_position='last')
    except KeyError:
        logger.error("Invalid sort column requested")
    
    return df

# Condition mapping based on eBay API values
CONDITION_MAPPING = {
    'new': ['NEW', 'NEW_OTHER', 'NEW_WITH_DEFECTS', 'MANUFACTURER_REFURBISHED'],
    'used': ['USED', 'LIKE_NEW', 'CERTIFIED_REFURBISHED', 'SELLER_REFURBISHED'],
    'all': []  # Special case meaning no filter
}

def filter_data(df, condition):
    """Filter DataFrame by condition"""
    if condition == 'all':
        return df
    
    condition = condition.lower()
    valid_conditions = CONDITION_MAPPING.get(condition, [])
    if not valid_conditions:
        logger.warning(f"Invalid condition specified: {condition}")
        return df
    
    return df[df['Condition'].isin(valid_conditions)]