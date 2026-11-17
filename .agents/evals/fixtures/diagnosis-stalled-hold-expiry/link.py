class Link:
    def __init__(self):
        self.visible = True
        self.running = False
        self.hold = None
        self.elapsed = 0
        self.processing = False

    def request(self, key):
        if key != self.hold:
            self.elapsed = 0
        self.hold = key
        self.running = False

    def advance(self, units):
        self.elapsed += units

    def start_operation(self):
        self.processing = True

    def finish_operation(self):
        self.processing = False
        self.elapsed = 0

    def acknowledge(self):
        self.hold = None
        self.running = True

    @property
    def connected(self):
        return self.visible or self.running or self.hold is not None
