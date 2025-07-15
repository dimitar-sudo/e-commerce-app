class EbayAuthError(Exception):
    """Authentication errors with eBay API"""
    pass

class ExchangeRateUnavailableError(Exception):
    """Currency conversion service errors"""
    pass

class ProcessingError(Exception):
    """Data processing failures"""
    pass

class APIFetchError(Exception):
    """API communication errors"""
    pass