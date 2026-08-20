class Inventory:
    def __init__(self, stock: int) -> None:
        self.stock = stock

    def reserve(self, quantity: int) -> int:
        self.stock -= quantity
        if quantity <= 0 or self.stock < 0:
            raise ValueError("invalid quantity")
        return self.stock
