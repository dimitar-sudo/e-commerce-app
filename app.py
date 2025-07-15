from flask import Flask, request, jsonify, session, g
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv
import logging
from auth import get_ebay_access_token, EbayAuthError
from api_fetcher import fetch_ebay_listings
from processor import process_ebay_data, sort_dataframe
from exporter import export_data
from exchange import get_exchange_rate, ExchangeRateUnavailableError
from exceptions import ProcessingError

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')  

app.config.update({
    'EBAY_CLIENT_ID': os.getenv('EBAY_CLIENT_ID'),
    'EBAY_CLIENT_SECRET': os.getenv('EBAY_CLIENT_SECRET'),
    'EXCHANGE_API_KEY': os.getenv('EXCHANGE_API_KEY'),
    'EBAY_SCOPE': os.getenv('EBAY_SCOPE', 'https://api.ebay.com/oauth/api_scope'),
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 86400 
})

# Initialize caching
cache = Cache(app)

# Initialize rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per minute"],
    storage_uri="memory://",
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.before_request
def before_request():
    """Initialize g object for request context"""
    g.ebay_token = None

def get_cached_exchange_rate(base_currency, target_currency):
    """Get exchange rate with caching"""
    cache_key = f"exchange_rate_{base_currency}_{target_currency}"
    rate = cache.get(cache_key)
    
    if rate is None:
        try:
            rate = get_exchange_rate(base_currency, target_currency)
            cache.set(cache_key, rate)
            logger.info(f"Fetched fresh exchange rate: {base_currency}->{target_currency}")
        except ExchangeRateUnavailableError as e:
            logger.error(f"Exchange rate error: {str(e)}")
            raise ProcessingError("Currency conversion unavailable") from e
    
    return rate

@app.route('/api/search', methods=['POST'])
@limiter.limit("1 per 5 minutes")  # Server-side rate limiting
def search_products():
    """Endpoint for product search with filtering and sorting"""
    try:
        # Validate required parameters
        if not request.json or 'product_name' not in request.json:
            return jsonify({'error': 'Missing product_name parameter'}), 400
        
        params = request.json
        product_name = params['product_name']
        condition = params.get('condition', 'all')
        currency = params.get('currency', 'USD')
        sort_by = params.get('sort_by', '')
        page = params.get('page', 1)
        
        # Validate allowed values
        allowed_conditions = ['all', 'new', 'used']
        allowed_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'CNY', 'HKD', 'AUD', 'SGD', 'CHF']
        
        if condition not in allowed_conditions:
            return jsonify({'error': 'Invalid condition specified'}), 400
        if currency not in allowed_currencies:
            return jsonify({'error': 'Invalid currency specified'}), 400
        
        # Fetch eBay listings
        raw_data = fetch_ebay_listings(
            product_name=product_name,
            page_number=page
        )
        
        # Process data (including currency conversion)
        df = process_ebay_data(raw_data, currency)
        
        # Apply condition filter
        if condition != 'all':
            df = df[df['Condition'].str.lower() == condition.lower()]
        
        # Apply sorting if requested
        if sort_by:
            df = sort_dataframe(df, sort_by)
        
        # Convert to dictionary for JSON response
        results = df.to_dict(orient='records')
        
        # Store search parameters in session for export
        session['last_search_params'] = params
        
        return jsonify({
            'products': results,
            'count': len(results),
            'page': page
        })
        
    except (EbayAuthError, ProcessingError) as e:
        logger.error(f"Processing error: {str(e)}")
        return jsonify({'error': 'Failed to process eBay data'}), 500
    except ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return jsonify({'error': 'eBay API unavailable'}), 503
    except Exception as e:
        logger.exception("Unexpected error in search endpoint")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/export', methods=['GET'])
def export_products():
    """Endpoint for exporting filtered/sorted data"""
    try:
        # Retrieve last search parameters
        params = session.get('last_search_params')
        if not params:
            return jsonify({'error': 'No search data available for export'}), 400
        
        # Validate export format
        export_format = request.args.get('format', 'csv').lower()
        if export_format not in ['csv', 'excel', 'json']:
            return jsonify({'error': 'Invalid export format'}), 400
        
        # Re-run search to get current data
        product_name = params['product_name']
        condition = params.get('condition', 'all')
        currency = params.get('currency', 'USD')
        sort_by = params.get('sort_by', '')
        page = params.get('page', 1)
        
        # Fetch eBay listings
        raw_data = fetch_ebay_listings(
            product_name=product_name,
            page_number=page
        )
        
        # Process data
        df = process_ebay_data(raw_data, currency)
        
        # Apply filters and sorting
        if condition != 'all':
            df = df[df['Condition'].str.lower() == condition.lower()]
        if sort_by:
            df = sort_dataframe(df, sort_by)
        
        # Generate export file
        return export_data(df, export_format, filename_prefix="ebay_products")
        
    except Exception as e:
        logger.exception("Error in export endpoint")
        return jsonify({'error': 'Export failed'}), 500

if __name__ == '__main__':
    app.run(debug=True)