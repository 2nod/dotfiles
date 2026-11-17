class Channel:
    def __init__(self):
        self.visible = True
        self.running = False
        self.waiting = False
        self.pending_action = False
        self.connected = True
        self.opens = 1
        self.closes = 0

    def set_visible(self, visible):
        self.visible = visible
        self._sync()

    def accept_message(self):
        self.waiting = True
        self._sync()

    def receive(self, event):
        if not self.connected:
            return
        if event == "running":
            self.running = True
            self.waiting = False
        elif event == "action_required":
            self.running = False
            self.waiting = False
            self.pending_action = True
        elif event == "receipt" and self.pending_action:
            self.pending_action = False
        elif event == "complete":
            self.running = self.waiting = self.pending_action = False
        self._sync()

    def _sync(self):
        needed = self.visible or self.running or self.waiting or self.pending_action
        if self.connected and not needed:
            self.connected = False
            self.closes += 1
        elif not self.connected and needed:
            self.connected = True
            self.opens += 1
