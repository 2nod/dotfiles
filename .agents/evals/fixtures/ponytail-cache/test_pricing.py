from pricing import fetch_count, get_rate


def main() -> None:
    if get_rate("USD") != 1.0 or get_rate("USD") != 1.0:
        raise SystemExit("unexpected USD rate")
    if fetch_count() != 1:
        raise SystemExit("the implementation should avoid a redundant fetch")


if __name__ == "__main__":
    main()
