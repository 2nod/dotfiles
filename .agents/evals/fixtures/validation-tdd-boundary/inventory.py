class Inventory:
    def __init__(self, stock): self.stock=stock
    def reserve(self, quantity):
        if quantity <= 0: raise ValueError("invalid quantity")
        self.stock -= quantity
        return self.stock
