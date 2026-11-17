class Inbox:
    def __init__(self):
        self.pending = set()
        self.failed = set()
        self.error = None

    def begin(self, key):
        self.pending.add(key)
        self.error = None

    def fail(self, key):
        self.failed.add(key)
        self.error = "Delivery failed"

    def accept(self, key):
        self.pending.discard(key)
        self.failed.discard(key)
        if not self.failed.intersection(self.pending):
            self.error = None

    def retry(self):
        self.failed.clear()
        self.error = None
