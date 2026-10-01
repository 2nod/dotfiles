def find_cards(root):
    return sorted(str(path.relative_to(root)) for path in root.rglob('CARD.md'))
