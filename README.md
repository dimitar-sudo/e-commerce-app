# eBay Product Finder

A web application that searches eBay products with advanced filtering, sorting, and export capabilities.

## Features

- **Product Search**: Search eBay products by name
- **Condition Filtering**: Filter by New, Used, or All conditions
- **Currency Conversion**: Support for multiple currencies (USD, EUR, GBP, JPY, CAD, CNY, HKD, AUD, SGD, CHF)
- **Sorting Options**: Sort by price (low/high) or seller rating (low/high)
- **Export Functionality**: Export results to CSV, Excel, or JSON formats
- **Responsive Design**: Modern, mobile-friendly interface

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **APIs**: eBay Browse API, Exchange Rate API
- **Data Processing**: Pandas
- **Caching**: Flask-Caching
- **Rate Limiting**: Flask-Limiter

## Environment Variables

Create a `.env` file with the following variables:

```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=production
EBAY_CLIENT_ID=your-ebay-client-id
EBAY_CLIENT_SECRET=your-ebay-client-secret
EBAY_SCOPE=https://api.ebay.com/oauth/api_scope
EXCHANGE_API_KEY=your-exchange-api-key
```

## Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ebay-product-finder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Fill in your API keys

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open http://localhost:5000 in your browser

## Deployment on Render

1. **Connect your repository** to Render
2. **Create a new Web Service**
3. **Configure environment variables** in Render dashboard:
   - `EBAY_CLIENT_ID`
   - `EBAY_CLIENT_SECRET`
   - `EXCHANGE_API_KEY`
   - `FLASK_SECRET_KEY` (auto-generated)
4. **Deploy**

The application will be available at your Render URL.

## API Endpoints

- `GET /` - Main application interface
- `POST /api/search` - Search for products
- `GET /api/export` - Export search results
- `GET /health` - Health check endpoint
- `GET /debug/token` - Debug eBay token status

## Project Structure

```
├── app.py                 # Main Flask application
├── auth.py               # eBay authentication
├── api_fetcher.py        # eBay API integration
├── processor.py          # Data processing and filtering
├── exporter.py           # Export functionality
├── exchange.py           # Currency conversion
├── exceptions.py         # Custom exceptions
├── requirements.txt      # Python dependencies
├── render.yaml           # Render deployment config
├── static/               # Static assets
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── script.js
└── templates/            # HTML templates
    └── index.html
```

## License

This project is licensed under the MIT License. 