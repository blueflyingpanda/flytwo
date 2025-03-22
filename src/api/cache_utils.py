from fastapi_cache.coder import Coder
import json
from datetime import date, datetime
from typing import Any


class DateJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles date and datetime objects."""

    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return {'__type__': 'date', 'value': obj.isoformat()}
        return super().default(obj)


class DateJSONDecoder(json.JSONDecoder):
    """JSON decoder that handles date and datetime objects."""

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if '__type__' in obj and obj['__type__'] == 'date':
            return date.fromisoformat(obj['value'])
        return obj


class DateJsonCoder(Coder):
    """Custom coder for FastAPICache that handles date objects."""

    @classmethod
    def encode(cls, value: Any) -> str:
        """Encode a value with dates to a JSON string."""
        if isinstance(value, dict):
            value = {cls._convert_key(k): v for k, v in value.items()}
        return json.dumps(value, cls=DateJSONEncoder)

    @classmethod
    def decode(cls, value: str) -> Any:
        """Decode a JSON string with dates back to the original structure."""
        if value is None:
            return None
        decoded_value = json.loads(value, cls=DateJSONDecoder)
        if isinstance(decoded_value, dict):
            decoded_value = {cls._convert_key(k): v for k, v in decoded_value.items()}
        return decoded_value

    @staticmethod
    def _convert_key(key):
        """Convert datetime.date keys to strings."""
        if isinstance(key, date):
            return key.isoformat()
        return key


def price_history_key_builder(func, namespace, request, response, *args, **kwargs):
    return f'{request.url.path}:{str(request.query_params.get("dt"))}'
