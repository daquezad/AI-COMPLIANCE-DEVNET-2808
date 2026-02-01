"""
NSO Compliance Report Downloader.

Downloads compliance report files from NSO using JSON-RPC authentication.
The reports are saved locally for preprocessing before LLM analysis.
"""
import os
import logging
import requests
from typing import Optional, Tuple
from pathlib import Path
from config.config import  NSO_PASSWORD, NSO_JSONRPC_PORT, NSO_HOST_DOWNLOAD, NSO_USERNAME, NSO_PROTOCOL
logger = logging.getLogger("devnet.compliance.tools.nso.downloader")

# Default directory for downloaded reports (can be overridden by env var)
REPORTS_DOWNLOAD_DIR = os.getenv("NSO_REPORTS_DIR", "/tmp/compliance-reports")



class NSOReportDownloader:
    """
    Downloads compliance reports from NSO via JSON-RPC authenticated session.
    
    Usage:
        downloader = NSOReportDownloader(
            host="localhost",
            port=8080,
            username="admin",
            password="admin"
        )
        filepath, content = downloader.download_report(report_url)
    """
    
    def __init__(
        self,
        host: str = NSO_HOST_DOWNLOAD,
        port: int = NSO_JSONRPC_PORT,
        username: str = NSO_USERNAME,
        password: str = NSO_PASSWORD,
        protocol: str = NSO_PROTOCOL,
        verify_ssl: bool = False,
        download_dir: Optional[str] = None
    ):
        """
        Initialize the NSO Report Downloader.
        
        Args:
            host: NSO server hostname
            port: NSO JSON-RPC port (usually 8080)
            username: NSO username
            password: NSO password
            protocol: http or https
            verify_ssl: Whether to verify SSL certificates
            download_dir: Directory to save downloaded reports
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.verify_ssl = verify_ssl
        self.download_dir = download_dir or REPORTS_DOWNLOAD_DIR
        
        self.base_url = f"{protocol}://{host}:{port}"
        self.jsonrpc_url = f"{self.base_url}/jsonrpc"
        self.session: Optional[requests.Session] = None
        
        # Ensure download directory exists
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
    
    def _login(self) -> bool:
        """
        Authenticate with NSO via JSON-RPC and create a session.
        
        Returns:
            True if login successful, False otherwise
        """
        self.session = requests.Session()
        headers = {"Content-Type": "application/json"}
        
        login_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "login",
            "params": {
                "user": self.username,
                "passwd": self.password
            }
        }
        
        logger.info(f"Attempting NSO JSON-RPC login to: {self.jsonrpc_url}")
        logger.debug(f"Login payload: {login_payload}")
        
        try:
            response = self.session.post(
                self.jsonrpc_url,
                json=login_payload,
                headers=headers,
                verify=self.verify_ssl
            )
            
            logger.info(f"Login response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    logger.info("NSO JSON-RPC login successful")
                    return True
                elif "error" in result:
                    logger.error(f"NSO login error: {result['error']}")
                    return False
            else:
                logger.error(f"NSO login failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"NSO connection error during login: {e}")
            return False
    
    def _logout(self) -> None:
        """Logout from NSO session."""
        if self.session:
            try:
                logout_payload = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "logout",
                    "params": {}
                }
                self.session.post(
                    self.jsonrpc_url,
                    json=logout_payload,
                    verify=self.verify_ssl
                )
            except Exception as e:
                logger.warning(f"Error during logout: {e}")
            finally:
                self.session.close()
                self.session = None
    
    def download_report(self, report_url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download a compliance report from NSO.
        
        Args:
            report_url: Full URL to the report file 
                       (e.g., "http://localhost:8080/compliance-reports/report_2025-10-09T13:48:32.txt")
                       OR just the report filename/path after the base URL
        
        Returns:
            Tuple of (filepath, content):
                - filepath: Local path where the report was saved
                - content: The raw content of the report file
            Returns (None, None) if download fails.
        """
        # Ensure we have a valid session
        if not self.session:
            if not self._login():
                logger.error("Failed to login to NSO for report download")
                return None, None
        
        # Handle both full URLs and relative paths
        if report_url.startswith("http"):
            full_url = report_url
        else:
            # Assume it's a path like "/compliance-reports/report_xxx.txt"
            full_url = f"{self.base_url}{report_url}"
        
        # Extract filename from URL
        filename = report_url.split("/")[-1]
        local_filepath = os.path.join(self.download_dir, filename)
        
        try:
            logger.info(f"Downloading report from: {full_url}")
            response = self.session.get(full_url, stream=True, verify=self.verify_ssl)
            
            if response.status_code == 200:
                content = ""
                with open(local_filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            content += chunk.decode('utf-8', errors='ignore')
                
                logger.info(f"Report downloaded successfully to: {local_filepath}")
                return local_filepath, content
            else:
                logger.error(f"Failed to download report. Status: {response.status_code}, Response: {response.text}")
                return None, None
                
        except requests.RequestException as e:
            logger.error(f"Error downloading report: {e}")
            return None, None
    
    def download_report_by_id(self, report_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download a compliance report by its ID.
        
        The report ID is typically a timestamp or identifier that forms part of the filename.
        This method constructs the URL based on NSO's standard compliance report path.
        
        Args:
            report_id: The report identifier. Can be:
                - Just the timestamp: "2025-10-09T13:48:32.663282+00:00"
                - With prefix: "report_2025-10-09T13:48:32.663282+00:00"
                - Full filename: "report_2025-10-09T13:48:32.663282+00:00.txt"
                - Numeric ID: "5"
        
        Returns:
            Tuple of (filepath, content) or (None, None) if download fails.
        """
        # Clean up the report_id - remove prefix/suffix if already present
        clean_id = report_id
        
        # Remove .txt suffix if present
        if clean_id.endswith('.txt'):
            clean_id = clean_id[:-4]
        
        # Remove report_ prefix if present
        if clean_id.startswith('report_'):
            clean_id = clean_id[7:]  # len('report_') = 7
        
        # NSO compliance reports are at /compliance-reports/report_<id>.txt
        report_path = f"/compliance-reports/report_{clean_id}.txt"
        logger.info(f"Constructed report path: {report_path}")
        return self.download_report(report_path)
    
    def __enter__(self):
        """Context manager entry."""
        self._login()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._logout()


# =============================================================================
# REPORT PREPROCESSING
# =============================================================================

def preprocess_compliance_report(report_content: str) -> str:
    """
    Preprocess the compliance report before passing to LLM for analysis.
    
    This function can be used to:
    - Remove sensitive information
    - Filter out irrelevant sections
    - Normalize the format
    - Reduce token count by removing boilerplate
    
    For now, this is a pass-through function that returns the content as-is.
    
    Args:
        report_content: Raw content of the compliance report
    
    Returns:
        Preprocessed report content ready for LLM analysis
    """
    # TODO: Implement preprocessing logic as needed
    # Examples of future preprocessing:
    # - Remove header/footer boilerplate
    # - Strip timestamps if not needed
    # - Remove sections that are always compliant
    # - Anonymize device names if required
    # - Compress repeated patterns
    
    # For now, just pass through unchanged
    return report_content


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_report_downloader() -> NSOReportDownloader:
    """
    Factory function to create an NSOReportDownloader with settings from environment.
    
    Uses the following environment variables:
    - NSO_HOST_DOWNLOAD: NSO server hostname (default: localhost)
    - NSO_JSONRPC_PORT: NSO JSON-RPC port (default: 8080)
    - NSO_USERNAME: NSO username (default: admin)
    - NSO_PASSWORD: NSO password (default: admin)
    - NSO_PROTOCOL: http or https (default: http)
    - NSO_REPORTS_DIR: Directory for downloaded reports (default: /tmp/compliance-reports)
    
    Returns:
        Configured NSOReportDownloader instance
    """
    host = os.getenv("NSO_HOST_DOWNLOAD", "localhost")
    port = int(os.getenv("NSO_JSONRPC_PORT", "8080"))
    username = os.getenv("NSO_USERNAME", "admin")
    protocol = os.getenv("NSO_PROTOCOL", "http")
    download_dir = os.getenv("NSO_REPORTS_DIR", "/tmp/compliance-reports")
    
    logger.info(f"Creating NSOReportDownloader with: host={host}, port={port}, protocol={protocol}, user={username}")
    
    return NSOReportDownloader(
        host=host,
        port=port,
        username=username,
        password=os.getenv("NSO_PASSWORD", "admin"),
        protocol=protocol,
        verify_ssl=os.getenv("NSO_VERIFY_SSL", "false").lower() == "true",
        download_dir=download_dir
    )


def download_and_preprocess_report(report_url_or_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Convenience function to download and preprocess a compliance report.
    
    Args:
        report_url_or_id: Can be:
            - Full URL: "http://x.x.x.x:8080/compliance-reports/report_xxx.txt"
            - Relative path: "/compliance-reports/report_xxx.txt"
            - Full filename: "report_2026-02-01T01:34:34.241829+00:00.txt"
            - Just timestamp ID: "2026-02-01T01:34:34.241829+00:00"
            - Numeric ID: "5"
    
    Returns:
        Tuple of (filepath, preprocessed_content) or (None, None) if failed
    """
    downloader = get_report_downloader()
    
    try:
        # Determine if it's a URL, path, or ID
        if report_url_or_id.startswith("http"):
            # Full URL
            filepath, content = downloader.download_report(report_url_or_id)
        elif report_url_or_id.startswith("/"):
            # Relative path starting with /
            filepath, content = downloader.download_report(report_url_or_id)
        else:
            # Could be a filename or an ID - download_report_by_id handles both
            filepath, content = downloader.download_report_by_id(report_url_or_id)
        
        if content:
            preprocessed = preprocess_compliance_report(content)
            return filepath, preprocessed
        
        return None, None
        
    finally:
        downloader._logout()
