"""Validate a CycloneDX JSON SBOM generated for VulnBank CI."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_sbom(path: Path) -> int:
    if not path.exists():
        print(f"ERROR: SBOM file not found: {path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: SBOM is not valid JSON: {exc}", file=sys.stderr)
        return 1

    if data.get("bomFormat") != "CycloneDX":
        print(
            f"ERROR: bomFormat must be 'CycloneDX', got {data.get('bomFormat')!r}",
            file=sys.stderr,
        )
        return 1

    spec_version = data.get("specVersion")
    if not spec_version:
        print("ERROR: specVersion is missing", file=sys.stderr)
        return 1

    components = data.get("components")
    if not isinstance(components, list):
        print("ERROR: components must be an array", file=sys.stderr)
        return 1

    if len(components) == 0:
        print("ERROR: components array is empty", file=sys.stderr)
        return 1

    print(f"CycloneDX version: {spec_version}")
    print(f"Components discovered: {len(components)}")
    return 0


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "sbom.cdx.json")
    return validate_sbom(path)


if __name__ == "__main__":
    raise SystemExit(main())
