# JWT security and load testing

The API rejects all event reads and writes without a signed **HS256** bearer token.
It validates the issuer, audience, expiration and mandatory subject/tenant claims.
The authorized tenant comes from the token; a client-provided tenant cannot cross
that boundary. Use `events:read` and `events:write` scopes.

For local demonstration only, generate a strong secret and set it in your
untracked `.env` file. Do not commit any passwords, signing keys or live tokens.

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Set VECTORHARBOR_JWT_SECRET, VECTORHARBOR_JWT_ISSUER and
# VECTORHARBOR_JWT_AUDIENCE in your local .env, then:
python scripts/mint_dev_token.py acme "events:read events:write"
```

The mint script is a local test utility only; production should use a managed
identity provider with JWKS/asymmetric signing, key rotation and audit logging.

After starting the API and Celery worker, run the opt-in load test against
disposable local data (k6 must be installed separately):

```sh
JWT="<copy test token>" TENANT=acme BASE_URL=http://localhost:8091 k6 run load/k6-events.js
```

The 10-VU/45-second thresholds are initial targets, **not measured results**.
Record throughput, p95 response time, error rate and hardware before claiming
performance. Never load-test another party's infrastructure without approval.
