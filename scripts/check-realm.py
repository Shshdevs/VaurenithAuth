import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

realm = json.loads(Path("config/realm/vaurenith-realm.json").read_text())
assert realm["realm"] == "vaurenith"
assert realm["users"] == []
assert realm["identityProviders"] == []
assert realm["registrationAllowed"] is True
assert realm["verifyEmail"] is True
assert realm["duplicateEmailsAllowed"] is False
assert realm["loginWithEmailAllowed"] is True
assert realm["bruteForceProtected"] is True
assert realm["resetPasswordAllowed"] is True
assert 0 < realm["accessTokenLifespan"] <= 300
assert 0 < realm["ssoSessionIdleTimeout"] <= 604800
assert 0 < realm["ssoSessionMaxLifespan"] <= 2592000
assert 0 < realm["clientSessionIdleTimeout"] <= 604800
assert 0 < realm["clientSessionMaxLifespan"] <= 2592000
assert realm["revokeRefreshToken"] is True
assert realm["refreshTokenMaxReuse"] == 0
assert realm["defaultSignatureAlgorithm"] == "RS256"
assert realm["loginTheme"] == "vaurenith"
assert realm["internationalizationEnabled"] is True
assert realm["defaultLocale"] == "ru"
assert realm["supportedLocales"] == ["en", "ru"]

expected = {
    "VaurenithWeb": ("http://localhost:5173/auth/callback", "http://localhost:5173"),
    "VaurenithDesktop": ("http://127.0.0.1:49152/oauth/callback", None),
}
clients = {client["clientId"]: client for client in realm["clients"]}
assert set(clients) == set(expected)
assert "basic" in realm["defaultDefaultClientScopes"]
basic_scope = next(scope for scope in realm["clientScopes"] if scope["name"] == "basic")
basic_mappers = {mapper["name"]: mapper for mapper in basic_scope["protocolMappers"]}
assert basic_mappers["sub"]["protocolMapper"] == "oidc-sub-mapper"
assert basic_mappers["sub"]["config"]["access.token.claim"] == "true"
assert basic_mappers["sub"]["config"]["introspection.token.claim"] == "true"
assert basic_mappers["auth_time"]["config"]["user.session.note"] == "AUTH_TIME"
assert basic_mappers["auth_time"]["config"]["access.token.claim"] == "true"
for client_id, (redirect_uri, origin) in expected.items():
    client = clients[client_id]
    assert client["publicClient"] is True
    assert client["standardFlowEnabled"] is True
    assert client["implicitFlowEnabled"] is False
    assert client["directAccessGrantsEnabled"] is False
    assert client["serviceAccountsEnabled"] is False
    assert client["fullScopeAllowed"] is False
    assert "secret" not in client
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert client["attributes"]["access.token.header.type.rfc9068"] == "true"
    assert client["redirectUris"] == [redirect_uri]
    assert client["webOrigins"] == ([] if origin is None else [origin])
    assert "basic" in client["defaultClientScopes"]
    assert "vaurenith-backend" in client["defaultClientScopes"]
    client_id_mappers = [
        mapper for mapper in client["protocolMappers"]
        if mapper["config"].get("claim.name") == "client_id"
    ]
    assert len(client_id_mappers) == 1
    assert client_id_mappers[0]["config"]["claim.value"] == client_id
    assert client_id_mappers[0]["config"]["access.token.claim"] == "true"
    assert client_id_mappers[0]["config"]["id.token.claim"] == "false"
    assert "*" not in json.dumps(client)

backend_scope = next(
    scope for scope in realm["clientScopes"]
    if scope["name"] == "vaurenith-backend"
)
backend_mappers = {
    mapper["config"]["claim.name"]: mapper
    for mapper in backend_scope["protocolMappers"]
    if "claim.name" in mapper.get("config", {})
}
assert backend_mappers["auth_provider"]["config"]["claim.value"] == "local"
assert backend_mappers["auth_provider"]["config"]["access.token.claim"] == "true"
assert backend_mappers["auth_provider"]["config"]["id.token.claim"] == "false"
assert "nbf" not in backend_mappers
audience_mapper = next(
    mapper for mapper in backend_scope["protocolMappers"]
    if mapper["protocolMapper"] == "oidc-audience-mapper"
)
assert audience_mapper["config"]["included.custom.audience"] == "vaurenith-backend"
display_name_mapper = backend_mappers["display_name"]
assert display_name_mapper["protocolMapper"] == "oidc-usermodel-attribute-mapper"
assert display_name_mapper["config"]["user.attribute"] == "display_name"
assert display_name_mapper["config"]["id.token.claim"] == "true"

base = f"https://{os.environ.get('AUTH_HOSTNAME', 'auth.vaurenith.test')}:{os.environ.get('AUTH_HTTPS_PORT', '8443')}"
context = ssl.create_default_context(cafile=".local/tls/rootCA.pem")
url = f"{base}/realms/vaurenith/.well-known/openid-configuration"
with urllib.request.urlopen(url, context=context, timeout=10) as response:
    discovery = json.load(response)
issuer = f"{base}/realms/vaurenith"
assert discovery["issuer"] == issuer
assert discovery["authorization_endpoint"] == f"{issuer}/protocol/openid-connect/auth"
assert discovery["token_endpoint"] == f"{issuer}/protocol/openid-connect/token"
with urllib.request.urlopen(discovery["jwks_uri"], context=context, timeout=10) as response:
    jwks = json.load(response)
assert jwks["keys"]

def get_status(url):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, response, code, message, headers, new_url):
            return None

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
        NoRedirect(),
    )
    try:
        with opener.open(url, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


web = clients["VaurenithWeb"]
invalid_redirect = f"{discovery['authorization_endpoint']}?client_id=VaurenithWeb&response_type=code&scope=openid&redirect_uri=https%3A%2F%2Fevil.example%2Fcallback"
invalid_status, _, _ = get_status(invalid_redirect)
assert invalid_status >= 400
implicit = f"{discovery['authorization_endpoint']}?client_id=VaurenithWeb&response_type=token&scope=openid&redirect_uri={urllib.parse.quote(web['redirectUris'][0], safe='')}"
implicit_status, implicit_headers, _ = get_status(implicit)
assert implicit_status >= 400 or "error=" in implicit_headers.get("Location", "")

token_request = urllib.request.Request(
    discovery["token_endpoint"],
    data=b"grant_type=password&client_id=VaurenithWeb&username=nobody%40example.test&password=not-a-real-password",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
direct_status, _, direct_body = get_status(token_request)
assert direct_status == 400
assert json.loads(direct_body)["error"] == "unauthorized_client"

origin_probe = urllib.request.Request(
    discovery["token_endpoint"],
    data=b"grant_type=password&client_id=VaurenithWeb",
    headers={
        "Origin": "https://evil.example",
        "Content-Type": "application/x-www-form-urlencoded",
    },
    method="POST",
)
origin_status, origin_headers, _ = get_status(origin_probe)
assert origin_status == 403
assert origin_headers.get("Access-Control-Allow-Origin") != "https://evil.example"
