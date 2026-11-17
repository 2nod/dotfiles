class Ledger:
    """Completion IDs are append-only. Requests resolve under caller control."""

    def __init__(self):
        self.completed = set()
        self.loading = False
        self.loaded = False
        self.request_id = 0
        self.active = None

    def begin(self):
        self.request_id += 1
        self.active = self.request_id
        self.loading = True
        self.completed.clear()
        return self.active

    def complete(self, request_id, completed):
        self.completed = set(completed)
        self.loaded = True
        self.loading = False
        self.active = None

    def cancel(self, request_id):
        if self.active == request_id:
            self.active = None
            self.loading = False

    def record(self, item_id):
        self.completed.add(item_id)

    def can_start(self, item_id):
        return self.loaded and not self.loading and item_id not in self.completed
