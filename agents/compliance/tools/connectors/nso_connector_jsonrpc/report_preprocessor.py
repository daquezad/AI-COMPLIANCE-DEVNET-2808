"""
NSO Compliance Report Preprocessor.

Preprocesses compliance reports (HTML or text) before passing to LLM for analysis.
"""
import logging
import re
from typing import Optional, Tuple
from html.parser import HTMLParser

from .nso_report_downloader import get_report_downloader

logger = logging.getLogger("devnet.compliance.tools.nso.preprocessor")


class HTMLTextExtractor(HTMLParser):
    """
    Simple HTML parser that extracts text content while preserving structure.
    Handles NSO compliance report HTML format.
    """
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_tag = None
        self.in_style = False
        self.in_script = False
        self.in_table = False
        self.table_row = []
        self.table_rows = []
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag == 'style':
            self.in_style = True
        elif tag == 'script':
            self.in_script = True
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
        elif tag == 'tr':
            self.table_row = []
        elif tag == 'br':
            self.text_parts.append('\n')
        elif tag in ('h1', 'h2', 'h3', 'h4'):
            self.text_parts.append('\n\n### ')
        elif tag == 'p':
            self.text_parts.append('\n')
        elif tag == 'li':
            self.text_parts.append('\n- ')
    
    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False
        elif tag == 'script':
            self.in_script = False
        elif tag == 'table':
            self.in_table = False
            # Format table rows
            if self.table_rows:
                self.text_parts.append('\n')
                for row in self.table_rows:
                    self.text_parts.append(' | '.join(row) + '\n')
                self.text_parts.append('\n')
        elif tag == 'tr' and self.in_table:
            if self.table_row:
                self.table_rows.append(self.table_row)
        elif tag in ('h1', 'h2', 'h3', 'h4'):
            self.text_parts.append('\n')
        elif tag == 'div':
            self.text_parts.append('\n')
        self.current_tag = None
    
    def handle_data(self, data):
        if self.in_style or self.in_script:
            return
        
        text = data.strip()
        if not text:
            return
        
        if self.in_table and self.current_tag in ('td', 'th'):
            self.table_row.append(text)
        else:
            self.text_parts.append(text + ' ')
    
    def get_text(self) -> str:
        return ''.join(self.text_parts)


def extract_text_from_html(html_content: str) -> str:
    """
    Extract readable text from HTML compliance report.
    
    Args:
        html_content: Raw HTML content
    
    Returns:
        Extracted text with preserved structure
    """
    parser = HTMLTextExtractor()
    try:
        parser.feed(html_content)
        text = parser.get_text()
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    except Exception as e:
        logger.warning(f"HTML parsing failed, returning raw content: {e}")
        return html_content


def is_html_content(content: str) -> bool:
    """Check if content appears to be HTML."""
    content_lower = content.strip().lower()
    return (
        content_lower.startswith('<!doctype html') or
        content_lower.startswith('<html') or
        '<html' in content_lower[:500]
    )


def preprocess_compliance_report(report_content: str, format_hint: Optional[str] = None) -> str:
    """
    Preprocess the compliance report before passing to LLM for analysis.
    
    Handles both HTML and text formats:
    - HTML: Extracts text content, preserves tables and structure
    - Text: Returns as-is with minor cleanup
    
    Args:
        report_content: Raw content of the compliance report (HTML or text)
        format_hint: Optional hint about format ('html', 'text', 'xml')
    
    Returns:
        Preprocessed report content ready for LLM analysis
    """
    if not report_content:
        return ""
    
    # Detect HTML content
    is_html = format_hint == 'html' or is_html_content(report_content)
    
    if is_html:
        logger.info("Preprocessing HTML compliance report")
        text_content = extract_text_from_html(report_content)
    else:
        logger.info("Preprocessing text compliance report")
        text_content = report_content
    
    # Common cleanup for all formats
    # Remove excessive blank lines
    text_content = re.sub(r'\n{3,}', '\n\n', text_content)
    
    # Remove everything below "### Details" section (device timestamps, commit history, etc.)
    # This keeps only the summary and compliance violations which are most relevant for LLM analysis
    details_markers = ['### Details', '### Details\n', '\n### Details']
    for marker in details_markers:
        if marker in text_content:
            text_content = text_content.split(marker)[0].strip()
            logger.info("Removed '### Details' section and below (timestamps, commit history)")
            break
    
    # Log preprocessing result
    original_len = len(report_content)
    processed_len = len(text_content)
    reduction = ((original_len - processed_len) / original_len * 100) if original_len > 0 else 0
    logger.info(f"Preprocessed report: {original_len} -> {processed_len} chars ({reduction:.1f}% reduction)")
    
    return text_content


def download_and_preprocess_report(report_url_or_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Convenience function to download and preprocess a compliance report.
    
    Args:
        report_url_or_id: Can be:
            - Full URL: "http://x.x.x.x:8080/compliance-reports/report_xxx.html"
            - Relative path: "/compliance-reports/report_xxx.html"
            - Full filename: "report_2026-02-01T04:28:30.595862+00:00.html"
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
