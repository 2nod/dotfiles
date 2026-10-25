def read_default(settings):
    destination = settings.get("DEFAULT_DESTINATION")
    if not destination:
        raise ValueError("DEFAULT_DESTINATION is required")
    return destination


def resolve_destination(settings, override=None):
    default = read_default(settings)
    return override if override is not None else default
