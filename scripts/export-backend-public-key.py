import base64
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path


def load_dotenv(path: Path) -> dict[str, str]:
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def der_length(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def der(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + der_length(len(value)) + value


def der_integer(value: bytes) -> bytes:
    value = value.lstrip(b"\x00") or b"\x00"
    if value[0] & 0x80:
        value = b"\x00" + value
    return der(0x02, value)


def jwk_to_pem(key: dict[str, str]) -> str:
    rsa_key = der(0x30, der_integer(decode_base64url(key["n"])) + der_integer(decode_base64url(key["e"])))
    algorithm = bytes.fromhex("300d06092a864886f70d0101010500")
    subject_public_key_info = der(0x30, algorithm + der(0x03, b"\x00" + rsa_key))
    encoded = base64.b64encode(subject_public_key_info).decode("ascii")
    lines = [encoded[index:index + 64] for index in range(0, len(encoded), 64)]
    return "-----BEGIN PUBLIC KEY-----\n" + "\n".join(lines) + "\n-----END PUBLIC KEY-----\n"


root = Path(__file__).resolve().parents[1]
dotenv = load_dotenv(root / ".env")
host = os.environ.get("AUTH_HOSTNAME", dotenv.get("AUTH_HOSTNAME", "auth.vaurenith.test"))
port = os.environ.get("AUTH_HTTPS_PORT", dotenv.get("AUTH_HTTPS_PORT", "8443"))
base = f"https://{host}:{port}"
issuer = f"{base}/realms/vaurenith"
ca_file = root / ".local/tls/rootCA.pem"
if not ca_file.is_file():
    raise SystemExit(f"Local CA file not found: {ca_file}")
context = ssl.create_default_context(cafile=str(ca_file))


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, context=context, timeout=10) as response:
        return json.load(response)


discovery = get_json(issuer + "/.well-known/openid-configuration")
if discovery.get("issuer") != issuer:
    raise SystemExit("Keycloak discovery issuer does not match the expected realm issuer")
jwks_uri = discovery.get("jwks_uri")
expected_jwks = issuer + "/protocol/openid-connect/certs"
if jwks_uri != expected_jwks:
    raise SystemExit("Keycloak JWKS URI does not match the expected realm endpoint")
if jwks_uri:
    keys = get_json(jwks_uri).get("keys", [])
signing_keys = [key for key in keys if key.get("kty") == "RSA" and key.get("alg") == "RS256" and key.get("use") == "sig"]
if len(signing_keys) != 1:
    raise SystemExit(f"Expected exactly one published RS256 signing key, found {len(signing_keys)}")

destination = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".local/backend/jwt-public.pem"
if not destination.is_absolute():
    destination = root / destination
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(jwk_to_pem(signing_keys[0]))
destination.chmod(0o644)
print(f"Wrote RS256 public key ({signing_keys[0]['kid']}) to {destination}")
