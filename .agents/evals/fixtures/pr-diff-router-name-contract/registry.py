import re


def register(alias):
    """Existing integration contract. Use the returned command verbatim."""
    if not re.fullmatch(r"[a-z0-9_]+", alias):
        raise ValueError("invalid alias")
    return f"send@{alias}"


def dispatch(command):
    """New entry point. Return the alias for a registered command."""
    match = re.fullmatch(r"send@([a-z0-9]+)", command)
    return match.group(1) if match else None
