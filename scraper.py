import requests
import pandas as pd
import argparse
import logging
from auth import get_ebay_access_token

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Setup command line arguments
parser = argparse.ArgumentParser(description='eBay Product Search Tool')
parser.add_argument('product_name', type=str, help='Product name to search for')
parser.add_argument('--sort', type=str, default='price_asc', help='Sort order: price_asc, price_desc, rating_asc, rating_desc')
parser.add_argument('--currency', type=str, default='USD', help='Displayed curency: USD, EUR, MKD')
parser.add_argument('--condition', type=str, default='all', help='Item condition: new, used, all')
parser.add_argument('--export_format', type=str, default='csv', help='Export format: csv, excel, json')
parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

args = parser.parse_args()

# Enable verbose logging if flag is set
if args.verbose:
    logger.setLevel(logging.DEBUG)
 
# eBay API constants
EBAY_APP_ID = get_ebay_access_token()

def fetch_ebay_listings(product_name, entries_per_page=100, page_number=1):
    global EBAY_APP_ID
    while True:
        try:
            url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={product_name}&limit={entries_per_page}&offset={(page_number - 1) * entries_per_page}" 
            headers = {"Authorization": f"Bearer {EBAY_APP_ID}"}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as err:
            logger.error(f"HTTP error occurred: {err}")
            if response.status_code == 401:
                EBAY_APP_ID = get_ebay_access_token()
                continue
            else:
                break

        except Exception as ex:
            logger.error(f"An error occurred: {ex}")
    

def process_ebay_data(data):
    items = data.get('itemSummaries', [])
    if not items:
        logger.warning("No items found.")
        return pd.DataFrame()

    rows = []

    for item in items:
        price_converter = get_exchange_rate("USD",args.currency,api_key='7010f1e38352928dffd86550')
        rows.append({
            "Product Title": item.get("title"),
            "Price": round((float(item.get("price", {}).get("value",0)))*price_converter,2),
            "Condition": item.get("condition", "Unknown"),
            "Seller Rating (%)": item.get("seller", {}).get("feedbackPercentage", "N/A"),
            "Seller Feedback Count": item.get("seller", {}).get("feedbackScore", "N/A"),
            "Item Country": item.get("itemLocation", {}).get("country", "N/A"),
            "Product URL": item.get("itemWebUrl")
        })

    return pd.DataFrame(rows)

def get_exchange_rate(base_currency, target_currency, api_key):

    if target_currency == 'USD':
        return 1.0

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}"
    
    try:
        response = requests.get(url, timeout=5)  # 5 second timeout
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()

        if data['result'] != 'success':
            raise Exception(f"ExchangeRate-API error: {data.get('error-type', 'Unknown error')}")

        return data["conversion_rates"][target_currency]

    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")

    return 1.0  

def main():
    logger.info(f"Searching for: {args.product_name}")
    data = fetch_ebay_listings(args.product_name)
    df = process_ebay_data(data)
    if not df.empty:

        # Filtering logic
        if args.condition != 'all':
            df = df[df['Condition'] == args.condition.capitalize()]
    
        # Sorting logic
        if 'price' in args.sort:
            ascending = 'asc' in args.sort
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
            df = df.sort_values(by='Price', ascending=ascending)
        elif 'rating' in args.sort:
            ascending = 'asc' in args.sort
            df["Seller Rating (%)"] = pd.to_numeric(df["Seller Rating (%)"], errors="coerce")
            df = df.sort_values(by="Seller Rating (%)", ascending=ascending)

        # Export logic
        if args.export_format == 'csv':
            df.to_csv('output.csv', index=False)
        elif args.export_format == 'excel':
            df.to_excel('output.xlsx', index=False)
        elif args.export_format == 'json':
            df.to_json('output.json', orient='records')

        logger.info("Data processing complete.")
    else:
        logger.warning("No data available to process.")

if __name__ == "__main__":
    main()