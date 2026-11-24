from dataclasses import dataclass


@dataclass
class Key:
    name: str
    stopped: bool = False


class Picker:
    def __init__(self):
        self.open = True
        self.workspace_keys = []

    def handle_key(self, name, *, from_picker):
        event = Key(name)
        if self.open and from_picker:
            self.handle_control(event)
            if not event.stopped:
                self.handle_dialog(event)
        if not event.stopped:
            self.workspace_keys.append(name)

    def handle_control(self, event):
        if event.name == 'Enter':
            self.open = False
            event.stopped = True

    def handle_dialog(self, event):
        if event.name == 'Escape':
            self.open = False
            event.stopped = True
