def parse_count(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return 0
