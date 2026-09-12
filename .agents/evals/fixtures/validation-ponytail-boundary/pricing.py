_fetch_count=0
_cache=None
def fetch_rate(currency):
    global _fetch_count
    _fetch_count+=1
    return {"USD":1.0,"EUR":0.92,"JPY":150.0}[currency]
def get_rate(currency):
    global _cache
    if _cache is None: _cache=fetch_rate(currency)
    return _cache
def fetch_count(): return _fetch_count
