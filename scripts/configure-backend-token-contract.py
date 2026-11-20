import getpass
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

root = Path(__file__).resolve().parents[1]
realm_config = json.loads((root / "config/realm/vaurenith-realm.json").read_text())
realm_name = realm_config["realm"]
dotenv = root / ".env"
dotenv_values = {}
if dotenv.exists():
    for line in dotenv.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        dotenv_values[key.strip()] = value.strip().strip("\"'")

admin_host = os.environ.get(
    "ADMIN_AUTH_HOSTNAME",
    dotenv_values.get("ADMIN_AUTH_HOSTNAME", "admin.auth.vaurenith.test"),
)
admin_port = os.environ.get(
    "ADMIN_HTTPS_PORT", dotenv_values.get("ADMIN_HTTPS_PORT", "8444")
)
admin_base = f"https://{admin_host}:{admin_port}"
auth_host = os.environ.get(
    "AUTH_HOSTNAME", dotenv_values.get("AUTH_HOSTNAME", "auth.vaurenith.test")
)
auth_port = os.environ.get(
    "AUTH_HTTPS_PORT", dotenv_values.get("AUTH_HTTPS_PORT", "8443")
)
issuer = f"https://{auth_host}:{auth_port}/realms/{realm_name}"
ca_file = root / ".local/tls/rootCA.pem"
if not ca_file.is_file():
    raise SystemExit(f"Local CA file not found: {ca_file}")
context = ssl.create_default_context(cafile=str(ca_file))

username = os.environ.get("KEYCLOAK_ADMIN_USERNAME") or input(
    "Keycloak master administrator username: "
)
password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or getpass.getpass(
    "Keycloak master administrator password: "
)


def request(
    method: str,
    path: str,
    payload: Any | None = None,
    token: str | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        admin_base + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, context=context, timeout=20) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Keycloak Admin API returned HTTP {error.code} for {method} {path}") from None


token_request = urllib.request.Request(
    admin_base + "/realms/master/protocol/openid-connect/token",
    data=urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        }
    ).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
try:
    with urllib.request.urlopen(token_request, context=context, timeout=20) as response:
        access_token = json.load(response)["access_token"]
except urllib.error.HTTPError as error:
    raise SystemExit(f"Could not authenticate to Keycloak Admin API (HTTP {error.code})") from None

realm = request("GET", f"/admin/realms/{realm_name}", token=access_token)
realm["defaultSignatureAlgorithm"] = realm_config["defaultSignatureAlgorithm"]
realm["loginTheme"] = realm_config["loginTheme"]
realm["internationalizationEnabled"] = realm_config["internationalizationEnabled"]
realm["supportedLocales"] = realm_config["supportedLocales"]
realm["defaultLocale"] = realm_config["defaultLocale"]
request("PUT", f"/admin/realms/{realm_name}", realm, token=access_token)

user_profile_path = f"/admin/realms/{realm_name}/users/profile"
user_profile = request("GET", user_profile_path, token=access_token)
attributes = user_profile.get("attributes") or []
display_name = next((item for item in attributes if item.get("name") == "display_name"), None)
if display_name is None:
    attributes.append({
        "name": "display_name",
        "displayName": "${vaurenithDisplayName}",
        "required": {"roles": ["user"]},
        "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
        "validations": {"length": {"max": 255}},
    })
else:
    display_name.update({
        "displayName": "${vaurenithDisplayName}",
        "required": {"roles": ["user"]},
        "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
        "validations": {"length": {"max": 255}},
    })

for profile_attribute in attributes:
    if profile_attribute.get("name") in {"firstName", "lastName"}:
        profile_attribute["permissions"] = {"view": ["admin"], "edit": ["admin"]}
        profile_attribute.pop("required", None)

user_profile["attributes"] = attributes
request("PUT", user_profile_path, user_profile, token=access_token)

def ensure_client_scope(scope_config: dict[str, Any]) -> dict[str, Any]:
    scopes = request("GET", f"/admin/realms/{realm_name}/client-scopes", token=access_token)
    scope = next((item for item in scopes if item.get("name") == scope_config["name"]), None)
    if scope is None:
        create_scope = {key: value for key, value in scope_config.items() if key != "protocolMappers"}
        request("POST", f"/admin/realms/{realm_name}/client-scopes", create_scope, token=access_token)
        scopes = request("GET", f"/admin/realms/{realm_name}/client-scopes", token=access_token)
        scope = next(item for item in scopes if item.get("name") == scope_config["name"])
    else:
        scope.update({key: value for key, value in scope_config.items() if key not in {"id", "protocolMappers"}})
        request(
            "PUT",
            f"/admin/realms/{realm_name}/client-scopes/{scope['id']}",
            scope,
            token=access_token,
        )

    mapper_path = f"/admin/realms/{realm_name}/client-scopes/{scope['id']}/protocol-mappers/models"
    existing_mappers = request("GET", mapper_path, token=access_token)
    for mapper in scope_config["protocolMappers"]:
        current = next((item for item in existing_mappers if item.get("name") == mapper["name"]), None)
        if current:
            mapper_with_id = {**mapper, "id": current["id"]}
            request("PUT", f"{mapper_path}/{current['id']}", mapper_with_id, token=access_token)
        else:
            request("POST", mapper_path, mapper, token=access_token)
    return scope


scope_configs = {
    scope["name"]: scope
    for scope in realm_config["clientScopes"]
}
basic_scope = ensure_client_scope(scope_configs["basic"])
scope = ensure_client_scope(scope_configs["vaurenith-backend"])

for client_config in realm_config["clients"]:
    client_id = client_config["clientId"]
    matches = request(
        "GET",
        f"/admin/realms/{realm_name}/clients?clientId={urllib.parse.quote(client_id)}",
        token=access_token,
    )
    if not matches:
        raise SystemExit(f"Client {client_id} was not found in realm {realm_name}")
    client = matches[0]
    client_uuid = client["id"]
    attributes = client.get("attributes") or {}
    attributes["access.token.header.type.rfc9068"] = "true"
    client["attributes"] = attributes
    request("PUT", f"/admin/realms/{realm_name}/clients/{client_uuid}", client, token=access_token)

    mapper_path = f"/admin/realms/{realm_name}/clients/{client_uuid}/protocol-mappers/models"
    existing_mappers = request("GET", mapper_path, token=access_token)
    for mapper in client_config.get("protocolMappers", []):
        current = next((item for item in existing_mappers if item.get("name") == mapper["name"]), None)
        if current:
            mapper_with_id = {**mapper, "id": current["id"]}
            request("PUT", f"{mapper_path}/{current['id']}", mapper_with_id, token=access_token)
        else:
            request("POST", mapper_path, mapper, token=access_token)

    default_scopes_path = f"/admin/realms/{realm_name}/clients/{client_uuid}/default-client-scopes"
    attached = request("GET", default_scopes_path, token=access_token)
    for required_scope in (basic_scope, scope):
        if not any(item.get("id") == required_scope["id"] for item in attached):
            request("PUT", f"{default_scopes_path}/{required_scope['id']}", token=access_token)

print(
    f"Applied realm login theme, required display_name registration field, and admin-only firstName/lastName profile fields. Applied Backend token contract: issuer {issuer}, audience vaurenith-backend, and basic scope for sub."
)
