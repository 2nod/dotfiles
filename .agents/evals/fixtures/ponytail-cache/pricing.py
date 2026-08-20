_fetch_count = 0


def fetch_rate(currency: str) -> float:
    global _fetch_count
    _fetch_count += 1
    return {"USD": 1.0, "EUR": 0.92, "JPY": 150.0}[currency]


def get_rate(currency: str) -> float:
    return fetch_rate(currency)


def fetch_count() -> int:
    return _fetch_count
