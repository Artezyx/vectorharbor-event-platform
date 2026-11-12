import hashlib
import json
import re

def normalize(body):
    if not isinstance(body, dict):
        raise ValueError("body must be an object")
    name, payload = body.get("type"), body.get("payload")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{2,63}", name):
        raise ValueError("invalid event type")
    if not isinstance(payload, dict):
        raise ValueError("invalid payload")
    if len(json.dumps(payload).encode()) > 120000:
        raise ValueError("payload too large")
    return {"type": name, "payload": payload}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def identity(event):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user = claims.get("sub")
    if not isinstance(user, str) or not re.fullmatch(r"[\w-]{5,128}", user):
        raise ValueError("invalid authenticated user")
    return user

def key(headers):
    values = {str(k).lower(): v for k, v in (headers or {}).items()}
    value = values.get("idempotency-key")
    if not isinstance(value, str) or not re.fullmatch(r"[\w.:-]{8,128}", value):
        raise ValueError("invalid idempotency key")
    return value

def result(code, data):
    return {"statusCode": code, "headers": {"content-type": "application/json", "cache-control":"no-store"}, "body": json.dumps(data)}
