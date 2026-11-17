class Connection:
    def __init__(self):
        self.closed = self.finished = False
        self.listeners = []

    def on_close(self, listener):
        self.listeners.append(listener)

    def disconnect(self):
        if self.closed:
            return
        self.closed = True
        for listener in self.listeners:
            listener()

    def finish(self):
        self.finished = True
        self.disconnect()


class Relay:
    def __init__(self):
        self.opens = self.stops = self.client_disconnects = 0

    async def start(self, connection, authorization):
        await authorization

        def on_close():
            self.stops += 1
            self.client_disconnects += 1

        connection.on_close(on_close)
        self.opens += 1
