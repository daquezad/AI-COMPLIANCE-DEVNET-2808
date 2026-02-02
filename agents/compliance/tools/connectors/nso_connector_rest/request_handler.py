"""
A simple HTTP client for sending authenticated requests to Cisco NSO via RESTCONF.
Supports GET, POST, PATCH, and DELETE methods with YANG JSON headers.

This module is based on the idea from: https://github.com/jillesca/nso-restconf-dns-example
"""
import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict

logger = logging.getLogger("devnet.compliance.tools.nso.rest")


class Response:
    """Response wrapper for HTTP responses."""
    
    def __init__(self, text: str, status_code: int, json: Optional[Dict] = None) -> None:
        self.text = text
        self.status_code = status_code
        self.json = json
    
    @property
    def ok(self) -> bool:
        """Returns True if status code is 2xx."""
        return 200 <= self.status_code < 300
    
    def __repr__(self) -> str:
        return f"Response(status_code={self.status_code}, text_length={len(self.text)})"


class SimpleHttpClient:
    """
    Simple HTTP client for NSO RESTCONF API.
    
    Usage:
        client = SimpleHttpClient(
            username="admin",
            password="admin",
            base_url="http://localhost:8080/restconf/data"
        )
        response = client.get("tailf-ncs:devices/device")
    """
    
    def __init__(self, username: str, password: str, base_url: str):
        """
        Initialize the HTTP client.
        
        Args:
            username: NSO username
            password: NSO password
            base_url: Base URL for RESTCONF API (e.g., http://localhost:8080/restconf/data)
        """
        self._base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.headers.update({
            'Content-Type': 'application/yang-data+json',
            'Accept': 'application/yang-data+json'
        })

    def _handle_response(self, response: requests.Response) -> tuple[str, Optional[Dict]]:
        """Handle response, including 204 No Content."""
        if response.status_code == 204:
            return "", None
        try:
            return response.text, response.json()
        except ValueError:
            return response.text, None

    def _send_request(self, method: str, path: str, data: Optional[Dict] = None) -> Response:
        """
        Send HTTP request to NSO.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: API path (appended to base_url)
            data: Request body for POST/PATCH
            
        Returns:
            Response object with text, status_code, and json
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        logger.info("NSO RESTCONF %s: %s", method.upper(), url)
        
        if data:
            logger.debug("Request body: %s", data)
        
        try:
            response = getattr(self.session, method.lower())(url, json=data)
            response.raise_for_status()
            text, json_data = self._handle_response(response)
            logger.debug("Response status: %s", response.status_code)
            return Response(text, response.status_code, json_data)
        except requests.RequestException as err:
            logger.error("NSO RESTCONF error: %s", err)
            status_code = getattr(err.response, 'status_code', 500) if err.response else 500
            error_text = str(err)
            return Response(text=error_text, status_code=status_code, json=None)

    def get(self, path: str) -> Response:
        """Send GET request."""
        return self._send_request("GET", path)

    def post(self, path: str, data: Optional[Dict] = None) -> Response:
        """Send POST request."""
        return self._send_request("POST", path, data)
    
    def patch(self, path: str, data: Optional[Dict] = None) -> Response:
        """Send PATCH request."""
        return self._send_request("PATCH", path, data)
    
    def delete(self, path: str) -> Response:
        """Send DELETE request."""
        return self._send_request("DELETE", path)
    
    