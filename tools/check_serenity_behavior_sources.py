from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src" / "aurora-serenity-bridge" / "behavior_catalog.toml"
SERENITY = ROOT / "third_party" / "serenity"


def has_glob(pattern: str) -> bool:
    if "*" in pattern:
        return any(SERENITY.glob(pattern))
    return (SERENITY / pattern).exists()


def main() -> int:
    with CATALOG.open("rb") as fh:
        catalog = tomllib.load(fh)

    missing = []
    for section, data in catalog.items():
        for source in data.get("serenity_sources", []):
            if not has_glob(source):
                missing.append((section, source))

    if missing:
        for section, source in missing:
            print(f"missing Serenity source for [{section}]: {source}", file=sys.stderr)
        return 1

    print(f"OK: {len(catalog)} Aurora behavior groups mapped to Serenity reference sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
