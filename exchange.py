import requests
from flask import current_app
from exceptions import ExchangeRateUnavailableError

def get_exchange_rate(base_currency, target_currency):
    if target_currency == 'USD':
        return 1.0

    api_key = current_app.config.get("EXCHANGE_API_KEY")
    if not api_key:
        raise ValueError("Missing EXCHANGE_API_KEY in Flask config")

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data['result'] != 'success':
            error_type = data.get('error-type', 'Unknown error')
            raise ExchangeRateUnavailableError(f"ExchangeRate-API error: {error_type}")

        return data["conversion_rates"][target_currency]

    except requests.exceptions.Timeout:
        raise ExchangeRateUnavailableError("Exchange rate API timed out")
    except requests.exceptions.RequestException as e:
        raise ExchangeRateUnavailableError(f"Request failed: {e}")
    except KeyError:
        raise ExchangeRateUnavailableError("Invalid currency code in response")