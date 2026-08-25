MODES = ("baseline", "optimized")


def build_schedule(members, key, horizon):
    """Return benchmark work in dispatch order."""
    return [
        {
            "mode": mode,
            "member": member,
            "latent": latent,
            "key": key,
            "horizon": horizon,
        }
        for mode in MODES
        for member, latent in members
    ]


def validate_pair(rows):
    return len(rows) == 2
