"""
NSO Compliance Report Downloader.

Downloads compliance report files from NSO using JSON-RPC authentication.
The reports are saved locally for preprocessing before LLM analysis.

NOTE: This module re-exports from split modules for backward compatibility.
- NSOReportDownloader, get_report_downloader -> nso_report_downloader.py
- preprocess_compliance_report, download_and_preprocess_report -> report_preprocessor.py
"""

# Re-export from split modules for backward compatibility
from .nso_report_downloader import (
    NSOReportDownloader,
    get_report_downloader,
    REPORTS_DOWNLOAD_DIR,
)
from .report_preprocessor import (
    preprocess_compliance_report,
    download_and_preprocess_report,
)

__all__ = [
    "NSOReportDownloader",
    "get_report_downloader",
    "REPORTS_DOWNLOAD_DIR",
    "preprocess_compliance_report",
    "download_and_preprocess_report",
]
