class Pipe:
    def __init__(self):
        self.visible = self.open = True
        self.sending = self.waiting = self.working = False
        self.opens, self.closes = 1, 0
        self.live_version = self.dispatch_version = 0

    def _sync(self):
        needed = self.visible or self.sending or self.waiting or self.working
        if self.open != needed:
            self.opens += bool(needed)
            self.closes += not needed
            self.open = needed

    def visibility(self, value):
        self.visible = value
        self._sync()

    def begin_publish(self):
        self.dispatch_version = self.live_version
        self._sync()

    def finish_publish(self, outcome):
        self.sending = False
        if outcome == "accepted":
            self.waiting = True
        self._sync()

    def receive(self, event):
        if not self.open:
            return
        self.live_version += 1
        self.working = event == "working"
        self.waiting = False
        self._sync()
