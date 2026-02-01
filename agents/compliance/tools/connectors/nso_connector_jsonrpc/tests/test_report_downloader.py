#!/usr/bin/env python3
"""
Quick test script to debug NSO JSON-RPC connection for report downloads.

Run this script to test connectivity and authentication:
    PYTHONPATH=. python agents/compliance/tools/connectors/nso_connector_cli/tests/test_report_downloader.py
"""
import os
import requests
import json

from config.config import (
    NSO_PROTOCOL,
    NSO_HOST,
    NSO_USERNAME,
    NSO_PASSWORD,
    NSO_JSONRPC_PORT,
    NSO_HOST_DOWNLOAD
)


def test_jsonrpc_login():
    """Test JSON-RPC login to NSO."""
    base_url = f"{NSO_PROTOCOL}://{NSO_HOST_DOWNLOAD}:{NSO_JSONRPC_PORT}"
    jsonrpc_url = f"{base_url}/jsonrpc"
    
    print(f"=" * 60)
    print(f"NSO JSON-RPC Connection Test")
    print(f"=" * 60)
    print(f"Base URL: {base_url}")
    print(f"JSON-RPC URL: {jsonrpc_url}")
    print(f"Username: {NSO_USERNAME}")
    print(f"Password: {'*' * len(NSO_PASSWORD)}")
    print(f"=" * 60)
    
    session = requests.Session()
    headers = {"Content-Type": "application/json"}
    
    login_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "login",
        "params": {
            "user": NSO_USERNAME,
            "passwd": NSO_PASSWORD
        }
    }
    
    print(f"\n1. Testing JSON-RPC login...")
    print(f"   Payload: {json.dumps(login_payload, indent=2)}")
    
    try:
        response = session.post(
            jsonrpc_url,
            json=login_payload,
            headers=headers,
            verify=False
        )
        
        print(f"\n   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                print(f"\n   ✅ LOGIN SUCCESSFUL!")
                print(f"   Session established.")
                return session, base_url
            elif "error" in result:
                print(f"\n   ❌ LOGIN FAILED: {result['error']}")
        else:
            print(f"\n   ❌ LOGIN FAILED with status {response.status_code}")
            
    except requests.RequestException as e:
        print(f"\n   ❌ CONNECTION ERROR: {e}")
    
    return None, None


def test_report_download(session, base_url, report_id):
    """Test downloading a compliance report."""
    if not session:
        print("\n❌ No valid session - cannot test download")
        return
    
    # Construct report URL
    report_url = f"{base_url}/compliance-reports/report_{report_id}.txt"
    
    print(f"\n2. Testing report download...")
    print(f"   Report URL: {report_url}")
    
    try:
        response = session.get(report_url, stream=True, verify=False)
        
        print(f"\n   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text[:500]
            print(f"\n   ✅ DOWNLOAD SUCCESSFUL!")
            print(f"   Content preview: {content}...")
        else:
            print(f"\n   ❌ DOWNLOAD FAILED with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            
    except requests.RequestException as e:
        print(f"\n   ❌ DOWNLOAD ERROR: {e}")


def test_list_reports(session, base_url):
    """Try to list available reports via JSON-RPC."""
    if not session:
        return
    
    jsonrpc_url = f"{base_url}/jsonrpc"
    
    print(f"\n3. Testing report listing via JSON-RPC...")
    
    # Try to get compliance report-results
    list_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "get_schema",
        "params": {
            "path": "/compliance:compliance/report-results"
        }
    }
    
    try:
        response = session.post(
            jsonrpc_url,
            json=list_payload,
            headers={"Content-Type": "application/json"},
            verify=False
        )
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
    except requests.RequestException as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    import sys
    
    # Get report ID from command line if provided
    report_id = sys.argv[1] if len(sys.argv) > 1 else "2026-02-01T01:34:34.241829+00:00"
    
    session, base_url = test_jsonrpc_login()
    
    if session:
        test_report_download(session, base_url, report_id)
        test_list_reports(session, base_url)
    
    print(f"\n{'=' * 60}")
    print("Test complete!")
    print(f"{'=' * 60}")
