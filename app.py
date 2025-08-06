from flask import Flask, request, jsonify, session, g, send_from_directory
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from auth import get_ebay_access_token, EbayAuthError
from api_fetcher import fetch_ebay_listings
from processor import process_ebay_data, sort_dataframe, filter_data
from exporter import export_data
from exchange import get_exchange_rate, ExchangeRateUnavailableError
from exceptions import ProcessingError

load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')

# Enable CORS for production (configure origins properly in production)
CORS(app, origins=['*'], supports_credentials=True)  

# Validate required environment variables
required_env_vars = ['EBAY_CLIENT_ID', 'EBAY_CLIENT_SECRET']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

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

@app.route('/debug/token')
def debug_token():
    try:
        from auth import get_token_info, get_ebay_access_token
        
        # Get token info
        token_info = get_token_info()
        
        # If no valid token, try to get one
        if not token_info['is_valid']:
            token = get_ebay_access_token()
            token_info = get_token_info()
        
        return jsonify({
            "has_token": token_info['has_token'],
            "is_valid": token_info['is_valid'],
            "expires_at": token_info['expires_at'],
            "current_time": token_info['current_time']
        })
    except EbayAuthError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
@limiter.limit("5 per second")  # Server-side rate limiting
def search_products():
    """Endpoint for product search with filtering and sorting"""
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        # Validate required parameters
        if not request.json or 'product_name' not in request.json:
            return jsonify({'error': 'Missing product_name parameter'}), 400
            
        # Validate product name length
        product_name = request.json['product_name'].strip()
        if not product_name or len(product_name) > 200:
            return jsonify({'error': 'Product name must be between 1 and 200 characters'}), 400
        
        params = request.json
        product_name = product_name  # Already validated above
        condition = params.get('condition', 'all')
        currency = params.get('currency', 'USD')
        sort_by = params.get('sort_by', '')
        page = params.get('page', 1)
        
        # Validate page number
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        
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
            page_number=page,
            condition=condition
        )
        
        # Process data (including currency conversion)
        df = process_ebay_data(raw_data, currency)
        
        # Apply condition filter as fallback (in case API filtering didn't work)
        if condition != 'all':
            df = filter_data(df, condition)
        
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
            page_number=page,
            condition=condition
        )
        
        # Process data
        df = process_ebay_data(raw_data, currency)
    
        # Apply condition filter as fallback (in case API filtering didn't work)
        if condition != 'all':
            df = filter_data(df, condition)
    
        # Apply sorting
        if sort_by:
            df = sort_dataframe(df, sort_by)
        
        # Generate export file
        return export_data(df, export_format, filename_prefix="ebay_products")
        
    except Exception as e:
        logger.exception("Error in export endpoint")
        return jsonify({'error': 'Export failed'}), 500
    
@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy', 'service': 'ebay-product-finder'})

@app.route('/')
def serve_frontend():
    return send_from_directory('templates', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    try:
        return send_from_directory('static', path)
    except FileNotFoundError:
        return jsonify({'error': 'Static file not found'}), 404

if __name__ == '__main__':
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)