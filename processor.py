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

# Comprehensive condition mapping based on eBay API values
# Updated to include all possible eBay condition values with case-insensitive support
CONDITION_MAPPING = {
    'new': [
        # Official eBay condition values
        'NEW', 'LIKE_NEW', 'NEW_OTHER', 'NEW_WITH_DEFECTS',
        # Common variations and display names
        'New', 'Like New', 'New (Other)', 'New with defects',
        'New with tags', 'Brand New', 'Mint', 'Perfect'
    ],
    'used': [
        # Official eBay condition values
        'PRE_OWNED_EXCELLENT', 'USED_EXCELLENT', 'USED_VERY_GOOD', 'USED_GOOD', 'USED_ACCEPTABLE',
        # Common variations and display names
        'Used', 'Pre-owned', 'Excellent', 'Very Good', 'Good', 'Acceptable',
        'Fair', 'Used - Excellent', 'Used - Very Good', 'Used - Good', 'Used - Acceptable'
    ],
    'refurbished': [
        # Official eBay condition values
        'CERTIFIED_REFURBISHED', 'EXCELLENT_REFURBISHED', 'VERY_GOOD_REFURBISHED', 
        'GOOD_REFURBISHED', 'SELLER_REFURBISHED',
        # Common variations and display names
        'Refurbished', 'Certified Refurbished', 'Excellent Refurbished', 
        'Very Good Refurbished', 'Good Refurbished', 'Seller Refurbished',
        'Manufacturer Refurbished'
    ],
    'parts_only': [
        # Official eBay condition values
        'FOR_PARTS_OR_NOT_WORKING',
        # Common variations and display names
        'For Parts', 'For Parts or Not Working', 'Parts Only', 'Not Working'
    ],
    'all': []  # Special case meaning no filter
}

def filter_data(df, condition):
    """Filter DataFrame by condition with improved case-insensitive matching"""
    if condition == 'all' or df.empty:
        return df
    
    condition = condition.lower()
    valid_conditions = CONDITION_MAPPING.get(condition, [])
    if not valid_conditions:
        logger.warning(f"Invalid condition specified: {condition}")
        return df
    
    # Create a copy to avoid modifying the original
    df_filtered = df.copy()
    
    # Normalize condition values for comparison (case-insensitive)
    df_filtered['Condition_Normalized'] = df_filtered['Condition'].str.upper().str.strip()
    
    # Create a set of normalized valid conditions for faster lookup
    valid_conditions_normalized = {c.upper().strip() for c in valid_conditions}
    
    # Filter based on normalized conditions
    mask = df_filtered['Condition_Normalized'].isin(valid_conditions_normalized)
    filtered_df = df_filtered[mask].drop('Condition_Normalized', axis=1)
    
    # Log detailed information about the filtering
    original_count = len(df)
    filtered_count = len(filtered_df)
    logger.info(f"Condition filtering: '{condition}' - {original_count} items -> {filtered_count} items")
    
    # Log unique conditions found in the data for debugging
    unique_conditions = df['Condition'].unique()
    logger.info(f"Unique conditions in data: {list(unique_conditions)}")
    
    # Log which conditions were matched
    matched_conditions = filtered_df['Condition'].unique()
    logger.info(f"Matched conditions: {list(matched_conditions)}")
    
    return filtered_df