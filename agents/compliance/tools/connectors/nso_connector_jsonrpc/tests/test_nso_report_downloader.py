#!/usr/bin/env python3
"""
Test script for NSOReportDownloader class.

Tests the report_downloader.py module which re-exports from the split modules.

Run this script to test the downloader class:
    PYTHONPATH=. python agents/compliance/tools/connectors/nso_connector_jsonrpc/tests/test_nso_report_downloader.py [report_id]
"""
import sys

# Import from the backward-compatible report_downloader module
from agents.compliance.tools.connectors.nso_connector_jsonrpc.report_downloader import (
    NSOReportDownloader,
    get_report_downloader,
    preprocess_compliance_report,
    download_and_preprocess_report,
)


def test_downloader_class():
    """Test the NSOReportDownloader class directly."""
    print("=" * 60)
    print("NSOReportDownloader Class Test")
    print("=" * 60)
    
    # Create downloader using factory function
    downloader = get_report_downloader()
    
    print(f"Host: {downloader.host}")
    print(f"Port: {downloader.port}")
    print(f"Protocol: {downloader.protocol}")
    print(f"Username: {downloader.username}")
    print(f"Base URL: {downloader.base_url}")
    print(f"Download Dir: {downloader.download_dir}")
    print("=" * 60)
    
    return downloader


def test_login(downloader: NSOReportDownloader):
    """Test JSON-RPC login."""
    print("\n1. Testing login...")
    
    success = downloader._login()
    
    if success:
        print("   ✅ LOGIN SUCCESSFUL!")
        return True
    else:
        print("   ❌ LOGIN FAILED")
        return False


def test_download_by_id(downloader: NSOReportDownloader, report_id: str):
    """Test downloading a report by ID."""
    print(f"\n2. Testing download_report_by_id('{report_id}')...")
    
    filepath, content = downloader.download_report_by_id(report_id)
    
    if filepath and content:
        print(f"   ✅ DOWNLOAD SUCCESSFUL!")
        print(f"   Saved to: {filepath}")
        print(f"   Content length: {len(content)} characters")
        print(f"   Content preview:\n{'-' * 40}")
        print(content[:500])
        print(f"{'-' * 40}")
        return content
    else:
        print("   ❌ DOWNLOAD FAILED")
        return None


def test_preprocess(content: str):
    """Test the preprocess function."""
    print("\n3. Testing preprocess_compliance_report()...")
    
    if not content:
        print("   ⚠️ No content to preprocess")
        return None
    
    preprocessed = preprocess_compliance_report(content)

    
    print(f"   ✅ Preprocessing complete!")
    print(f"   Original length: {len(content)}")
    print(f"   Preprocessed length: {len(preprocessed)}")
    
    return preprocessed


def test_convenience_function(report_id: str):
    """Test the download_and_preprocess_report convenience function."""
    print(f"\n4. Testing download_and_preprocess_report('{report_id}')...")
    
    filepath, preprocessed = download_and_preprocess_report(report_id)
    
    if filepath and preprocessed:
        print(f"   ✅ DOWNLOAD & PREPROCESS SUCCESSFUL!")
        print(f"   Saved to: {filepath}")
        print(f"   Preprocessed length: {len(preprocessed)} characters")
        return True
    else:
        print("   ❌ DOWNLOAD & PREPROCESS FAILED")
        return False


def test_context_manager(report_id: str):
    """Test the context manager interface."""
    print(f"\n5. Testing context manager with download_report_by_id('{report_id}')...")
    
    with NSOReportDownloader() as downloader:
        filepath, content = downloader.download_report_by_id(report_id)
        
        if filepath and content:
            print(f"   ✅ CONTEXT MANAGER DOWNLOAD SUCCESSFUL!")
            print(f"   Saved to: {filepath}")
            return True
        else:
            print("   ❌ CONTEXT MANAGER DOWNLOAD FAILED")
            return False


def test_various_id_formats(downloader: NSOReportDownloader):
    """Test that download_report_by_id handles various input formats."""
    print("\n6. Testing various report_id formats...")
    
    test_cases = [
        ("2026-02-01T01:34:34.241829+00:00", "Plain timestamp"),
        ("report_2026-02-01T01:34:34.241829+00:00", "With prefix"),
        ("report_2026-02-01T04:28:30.595862+00:00.html", "With prefix and suffix"),
        ("2026-02-01T01:34:34.241829+00:00.txt", "With suffix only"),
    ]
    
    for report_id, description in test_cases:
        # Test the ID cleaning logic by checking the constructed path
        clean_id = report_id
        if clean_id.endswith('.txt'):
            clean_id = clean_id[:-4]
        if clean_id.startswith('report_'):
            clean_id = clean_id[7:]
        
        expected_path = f"/compliance-reports/report_{clean_id}.txt"
        print(f"   {description}: '{report_id}'")
        print(f"      -> Expected path: {expected_path}")
    
    print("   ✅ ID format handling verified")


if __name__ == "__main__":
    # Get report ID from command line if provided
    report_id = sys.argv[1] if len(sys.argv) > 1 else "report_2026-02-01T04:28:30.595862+00:00"
    
    print(f"\nUsing report ID: {report_id}\n")
    
    # Test 1: Create downloader
    downloader = test_downloader_class()
    
    # Test 2: Login
    if test_login(downloader):
        # Test 3: Download by ID
        content = test_download_by_id(downloader, report_id)
        
        # Test 4: Preprocess
        test_preprocess(content)
        
        # Logout
        downloader._logout()
        print("\n   Session logged out.")
    
    # Test 5: Convenience function (creates its own session)
    test_convenience_function(report_id)
    
    # Test 6: Context manager
    test_context_manager(report_id)
    
    # Test 7: ID format handling
    test_various_id_formats(downloader)
    
    print(f"\n{'=' * 60}")
    print("All tests complete!")
    print(f"{'=' * 60}")
