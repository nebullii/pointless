"""Pointless entrypoint."""

from core.config import Settings


def main() -> int:
    settings = Settings()
    print(f"Pointless starting. profile={settings.profile}")
    # TODO: wire capture -> tracker -> gesture engine -> dispatcher
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
