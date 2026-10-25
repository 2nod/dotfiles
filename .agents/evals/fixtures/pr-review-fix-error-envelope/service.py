class StoreError(Exception):
    def __init__(self, code):
        super().__init__(f"STORE_{code}")
        self.code = code


class ResponseError(Exception):
    def __init__(self, error):
        super().__init__(f"!!{error}!!")
        self.metadata = {"category": "REQUEST_FAILED", "reason": str(error)}


def response_error(code):
    return ResponseError(StoreError(code))
