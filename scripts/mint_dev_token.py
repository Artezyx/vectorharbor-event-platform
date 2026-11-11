"""Local-only development JWT generator; never deploy as an API endpoint."""
import os
import sys
from datetime import datetime, timedelta, timezone
import jwt

if __name__ == "__main__":
    secret = os.getenv("VECTORHARBOR_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise SystemExit("Set a random VECTORHARBOR_JWT_SECRET (>=32 bytes) first.")
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python scripts/mint_dev_token.py TENANT "events:read events:write"')
    now = datetime.now(timezone.utc)
    print(jwt.encode({
        "sub": "local-load-tester", "tenant_id": sys.argv[1], "scope": sys.argv[2],
        "iss": os.getenv("VECTORHARBOR_JWT_ISSUER", "vectorharbor-local"),
        "aud": os.getenv("VECTORHARBOR_JWT_AUDIENCE", "vectorharbor-api"),
        "iat": now, "exp": now + timedelta(minutes=30),
    }, secret, algorithm="HS256"))
