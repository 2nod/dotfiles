"""Synthetic dependency contract. Version 2 requires explicit keys."""
API_VERSION = 1
_MISSING = object()


def record(key_or_value, value=_MISSING):
    if value is _MISSING:
        if API_VERSION == 2:
            raise TypeError("record requires key type and value type")
        key_type, value_type = str, key_or_value
    else:
        key_type, value_type = key_or_value, value

    class Record:
        def parse(self, data):
            if not isinstance(data, dict):
                raise ValueError("expected an object")
            if not all(isinstance(key, key_type) for key in data):
                raise ValueError("invalid key")
            if not all(isinstance(item, value_type) for item in data.values()):
                raise ValueError("invalid value")
            return dict(data)

    return Record()
