
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
CNC_USERNAME = os.getenv("CNC_USERNAME", "")
CNC_PASSWORD = os.getenv("CNC_PASSWORD", "")
CNC_HOST = os.getenv("CNC_HOST", "")
CNC_PORT = os.getenv("CNC_PORT", "")
COMPLIANCE_AGENT_PORT = os.getenv("COMPLIANCE_AGENT_PORT", "9090")
