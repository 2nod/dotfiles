class Pool:
    def __init__(self):
        self.entries = {}

    def join(self, key, epoch):
        previous = self.entries.get(key)
        if previous:
            previous['open'] = False
        token = {'epoch': epoch, 'open': True}
        self.entries[key] = token
        return token

    def leave(self, key, epoch):
        previous = self.entries.pop(key, None)
        if previous:
            previous['open'] = False

    def release(self, key, token):
        self.leave(key, token['epoch'])
