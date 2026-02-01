from __future__ import annotations

import logging
import requests
import urllib3
from typing import Optional, Any, Dict

# Suppress InsecureRequestWarning for lab environments using self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("devnet.agents.compliance.tools.connectors.cwm_connector.request_handler")

class Response:
    """Lightweight response wrapper for consistent API handling."""
    def __init__(self, text: str, status_code: int, json_data: Optional[dict]) -> None:
        self.text = text
        self.status_code = status_code
        self.json = json_data

class AuthenticationError(Exception):
    """Raised when the 2-step CAS authentication fails."""
    pass

class CrossworkApiClient:
    """
    Production-ready HTTP client for Cisco Crosswork.
    Optimized for connection pooling and automatic token lifecycle management.
    """

    def __init__(
        self,
        base_url: str,
        auth_url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_url = auth_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._timeout = timeout

        self.session = requests.Session()
        # Default headers for YANG-JSON compliance
        self.session.headers.update({
            "Content-Type": "application/yang-data+json",
            "Accept": "application/yang-data+json",
        })

        self._token: Optional[str] = None

    def _authenticate(self) -> str:
        """Performs the 2-step Ticket -> Token exchange required by Crosswork."""
        logger.info("Initiating Crosswork authentication sequence...")

        try:
            # Step 1: Request Ticket (TGT)
            ticket_url = f"{self._auth_url}/sso/v1/tickets"
            payload = {"username": self._username, "password": self._password}
            
            t_resp = self.session.post(
                ticket_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain"},
                verify=self._verify_ssl,
                timeout=self._timeout
            )
            t_resp.raise_for_status()
            ticket = t_resp.text.strip()

            # Step 2: Exchange Ticket for Bearer Token
            token_url = f"{ticket_url}/{ticket}"
            service_url = f"{self._auth_url}/app-dashboard"
            
            s_resp = self.session.post(
                token_url,
                data={"service": service_url},
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain"},
                verify=self._verify_ssl,
                timeout=self._timeout
            )
            s_resp.raise_for_status()
            
            self._token = s_resp.text.strip()
            # Update session headers with the new token
            self.session.headers["Authorization"] = f"Bearer {self._token}"
            
            logger.info("Authentication successful. Token acquired.")
            return self._token

        except requests.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(f"Failed to authenticate with Crosswork: {e}")

    def _ensure_token(self) -> None:
        if not self._token:
            self._authenticate()

    def _send_request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True
    ) -> Response:
        """Internal generic request dispatcher with auto-retry on expiry."""
        self._ensure_token()
        url = f"{self._base_url}/{path.lstrip('/')}"

        # CRITICAL FIX: CNC Inventory Query requires a valid JSON body.
        # If POSTing and no data is provided, we send an empty object {} 
        # instead of None to ensure the backend processes the 'select all' logic.
        json_payload = data if data is not None else ({} if method.upper() == "POST" else None)

        # Merge custom headers with session headers
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_payload,
                headers=request_headers,
                params=params,
                verify=self._verify_ssl,
                timeout=self._timeout
            )

            # Handle Token Expiration
            if response.status_code == 401 and retry_on_401:
                logger.warning("Token expired. Attempting refresh...")
                self._token = None
                return self._send_request(method, path, data, headers, params, retry_on_401=False)

            # For error responses, capture the body before raise_for_status
            if response.status_code >= 400:
                error_body = response.text
                logger.error(f"API Error ({response.status_code}): {error_body}")
                # Safe JSON parsing for error response
                json_data = None
                if error_body.strip():
                    try:
                        json_data = response.json()
                    except ValueError:
                        logger.debug("Error response body is not JSON.")
                return Response(error_body, response.status_code, json_data)

            # Safe JSON parsing for success response
            json_data = None
            if response.status_code != 204 and response.text.strip():
                try:
                    json_data = response.json()
                except ValueError:
                    logger.debug("Response body is not JSON.")

            return Response(response.text, response.status_code, json_data)

        except requests.RequestException as err:
            status_code = getattr(err.response, "status_code", 500) if hasattr(err, 'response') and err.response else 500
            error_text = getattr(err.response, "text", str(err)) if hasattr(err, 'response') and err.response else str(err)
            logger.error(f"API Error ({status_code}): {error_text}")
            return Response(error_text, status_code, None)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Response:
        return self._send_request("GET", path, params=params)
    
    def post(self, path: str, data: Optional[dict] = None, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Response:
        return self._send_request("POST", path, data, headers, params)
    
    def patch(self, path: str, data: Optional[dict] = None, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Response:
        return self._send_request("PATCH", path, data, headers, params)
    
    def delete(self, path: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Response:
        return self._send_request("DELETE", path, headers=headers, params=params)