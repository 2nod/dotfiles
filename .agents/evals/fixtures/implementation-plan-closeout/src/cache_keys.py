def canonical_key(tenant_id: str, item_id: str) -> str:
    return f"{tenant_id}:{item_id}"


def legacy_key(item_id: str) -> str:
    return item_id
