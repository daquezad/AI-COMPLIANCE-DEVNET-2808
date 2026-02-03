
import os
from dotenv import load_dotenv

load_dotenv()  # Automatically loads from `.env` or `.env.local`

DEFAULT_MESSAGE_TRANSPORT = os.getenv("DEFAULT_MESSAGE_TRANSPORT", "SLIM")
TRANSPORT_SERVER_ENDPOINT = os.getenv("TRANSPORT_SERVER_ENDPOINT", "http://localhost:46357")
FARM_AGENT_HOST = os.getenv("FARM_AGENT_HOST", "localhost")
FARM_AGENT_PORT = int(os.getenv("FARM_AGENT_PORT", "9999"))

LLM_MODEL = os.getenv("LLM_MODEL", "")
## Oauth2 OpenAI Provider
OAUTH2_CLIENT_ID= os.getenv("OAUTH2_CLIENT_ID", "")
OAUTH2_CLIENT_SECRET= os.getenv("OAUTH2_CLIENT_SECRET", "")
OAUTH2_TOKEN_URL= os.getenv("OAUTH2_TOKEN_URL", "")
OAUTH2_BASE_URL= os.getenv("OAUTH2_BASE_URL", "")
OAUTH2_APPKEY= os.getenv("OAUTH2_APPKEY", "")

LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()

ENABLE_HTTP = os.getenv("ENABLE_HTTP", "true").lower() in ("true", "1", "yes")

## CNC Connection Settings
CWM_USERNAME = os.getenv("CWM_USERNAME", "")
CWM_PASSWORD = os.getenv("CWM_PASSWORD", "")
CWM_HOST = os.getenv("CWM_HOST", "")
CWM_PORT = os.getenv("CWM_PORT", "")
COMPLIANCE_AGENT_PORT = int(os.getenv("COMPLIANCE_AGENT_PORT", 9090))
COMPLIANCE_AGENT_IP = os.getenv("COMPLIANCE_AGENT_IP", "0.0.0.0")


def _resolve_host(host: str, fallback: str = "127.0.0.1") -> str:
    """
    Resolve host, falling back if host.docker.internal doesn't resolve (running outside Docker).
    """
    if host == "host.docker.internal":
        import socket
        try:
            socket.gethostbyname(host)
            return host
        except socket.gaierror:
            # host.docker.internal doesn't exist - we're not in Docker
            return fallback
    return host


## NSO Connection Settings (pyATS Testbed)
_nso_host_raw = os.getenv("NSO_HOST", "127.0.0.1")
NSO_HOST = _resolve_host(_nso_host_raw, "127.0.0.1")
NSO_CLI_PORT = int(os.getenv("NSO_CLI_PORT", os.getenv("NSO_PORT", "2024")))
NSO_USERNAME = os.getenv("NSO_USERNAME", "admin")
NSO_PASSWORD = os.getenv("NSO_PASSWORD", "admin")
NSO_CLI_PROTOCOL = os.getenv("NSO_CLI_PROTOCOL", "ssh")

## NSO JSON-RPC Settings (for report downloads)
NSO_JSONRPC_PORT = int(os.getenv("NSO_JSONRPC_PORT", "8080"))
NSO_PROTOCOL = os.getenv("NSO_PROTOCOL", "http")
NSO_VERIFY_SSL = os.getenv("NSO_VERIFY_SSL", "false").lower() == "true"
NSO_REPORTS_DIR = os.getenv("NSO_REPORTS_DIR", "/tmp/compliance-reports")
# NSO_HOST_DOWNLOAD uses NSO_HOST by default
NSO_HOST_DOWNLOAD = os.getenv("NSO_HOST_DOWNLOAD", "localhost")
# NSO_HOST_HEADER overrides HTTP Host header (needed when using host.docker.internal)
NSO_HOST_HEADER = os.getenv("NSO_HOST_HEADER", "")