from dataclasses import dataclass
from typing import Annotated
import hmac

from fastapi import Depends, Header, HTTPException, status

from oracle_api.config import settings


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    role: str
    actor: str = "api-key"


_ALLOWED_ROLES = {"viewer", "operator", "admin", "ingestor"}
_ROLE_PERMISSIONS = {
    "viewer": {"read"},
    "operator": {"read", "write"},
    "ingestor": {"read", "ingest"},
    "admin": {"read", "write", "ingest", "audit"},
}


def _extract_token(authorization: str | None, x_api_key: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    return None


def get_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> Principal:
    token = _extract_token(authorization, x_api_key)

    if settings.api_keys.strip():
        for entry in settings.api_keys.split(";"):
            parts = [part.strip() for part in entry.split("|")]
            if len(parts) != 3:
                continue
            configured_token, tenant_id, role = parts
            if (
                configured_token
                and (token or "").isascii()
                and hmac.compare_digest(token or "", configured_token)
                and tenant_id
                and len(tenant_id) <= 120
                and role in _ALLOWED_ROLES
            ):
                if x_tenant_id and (
                    not x_tenant_id.isascii()
                    or not hmac.compare_digest(x_tenant_id.strip(), tenant_id)
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="The requested tenant does not match the API credential.",
                    )
                return Principal(tenant_id=tenant_id, role=role)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid ORACLE API credential is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if settings.oracle_env.lower() not in {"development", "dev", "test"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API credentials are not configured for this environment.",
        )

    tenant_id = (x_tenant_id or "default").strip()
    if not tenant_id or len(tenant_id) > 120:
        raise HTTPException(status_code=400, detail="Invalid tenant identifier.")
    return Principal(tenant_id=tenant_id, role="admin", actor="development")


PrincipalDependency = Annotated[Principal, Depends(get_principal)]


def require_roles(*roles: str):
    allowed = set(roles)

    def dependency(principal: PrincipalDependency) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The API credential does not have permission for this operation.",
            )
        return principal

    return dependency


def has_permission(principal: Principal, permission: str) -> bool:
    return permission in _ROLE_PERMISSIONS.get(principal.role, set())
