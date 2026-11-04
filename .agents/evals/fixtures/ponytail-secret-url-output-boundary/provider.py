class Provider:
    def __init__(self):
        self.calls = []

    def request(self, url):
        self.calls.append(url)
        return {
            "session": {"service": {"url": url}, "state": "ready"},
            "history": [{"type": "configuration", "service": {"url": url}}],
            "stream": [{"type": "update", "detail": "Connected to " + url}],
            "diagnostics": {"message": "Endpoint " + url, "attempt": 1},
            "other_url": "https://public.example.invalid/help",
            "answer": "Reference found",
        }
