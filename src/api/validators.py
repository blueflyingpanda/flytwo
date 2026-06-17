from api.common import bad_request
from currency_converter import CurrencyConverter


def validate_airport_code(code: str) -> str:
    code = code.strip().upper()
    if len(code) != 3:
        raise bad_request('Invalid airport code! Should be 3 letters.')
    return code


def validate_currency(code: str) -> str:
    code = code.strip().upper()
    if code not in CurrencyConverter.SUPPORTED_CURRENCIES:
        raise bad_request(f'Unsupported currency: {code}')
    return code
