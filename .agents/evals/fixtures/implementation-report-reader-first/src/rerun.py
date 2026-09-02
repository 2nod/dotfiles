def rerun(items, target_id=None):
    targets = items if target_id is None else [item for item in items if item.id == target_id]
    return [translate(item) for item in targets]
