"""Wait until VulnBank responds on GET /health."""

import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("DAST_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT_SECONDS = int(os.environ.get("DAST_HEALTH_TIMEOUT", "60"))


def main() -> int:
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2) as response:
                if response.status == 200:
                    return 0
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(1)

    print(f"DAST health check failed: {BASE_URL}/health did not respond in time", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
