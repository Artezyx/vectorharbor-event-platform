"""Signed JWT authentication and tenant-scoped authorization.

All tenants are derived from verified claims, never trusted from query parameters.
This HS256 setup is appropriate for the local portfolio demo; use a managed
OIDC identity provider and asymmetric keys for deployed multi-service systems.
"""
import os
from dataclasses import dataclass
import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    scopes: frozenset[str]

def require_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    secret = os.getenv("VECTORHARBOR_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="JWT signing key is not configured")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(
            credentials.credentials, secret, algorithms=["HS256"],
            issuer=os.getenv("VECTORHARBOR_JWT_ISSUER", "vectorharbor-local"),
            audience=os.getenv("VECTORHARBOR_JWT_AUDIENCE", "vectorharbor-api"),
            options={"require": ["sub", "tenant_id", "iss", "aud", "iat", "exp"]},
            leeway=10,
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc
    tenant = claims.get("tenant_id")
    subject = claims.get("sub")
    if not isinstance(tenant, str) or not 2 <= len(tenant) <= 80 or not tenant.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=401, detail="Invalid token tenant")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    scopes = claims.get("scope", "")
    if not isinstance(scopes, str):
        raise HTTPException(status_code=401, detail="Invalid token scopes")
    return Principal(subject, tenant, frozenset(scopes.split()))

def require_scope(principal: Principal, tenant_id: str, scope: str) -> None:
    if principal.tenant_id != tenant_id or scope not in principal.scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions for this tenant")
