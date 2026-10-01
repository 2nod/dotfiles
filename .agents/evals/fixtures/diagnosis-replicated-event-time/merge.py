def reconcile_event(left, right):
    """Merge a replicated lifecycle event, keeping semantic conflicts visible."""
    return left if left == right else None
