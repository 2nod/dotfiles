class Inventory:
    def __init__(self, stock): self.stock=stock
    def reserve(self, quantity):
        if quantity <= 0 or quantity > self.stock: raise ValueError("invalid quantity")
        self.stock -= quantity
        return self.stock
