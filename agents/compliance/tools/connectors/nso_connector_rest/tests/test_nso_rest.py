#!/usr/bin/env python3
"""
Test script for NSO RESTCONF API functions.

Tests the nso_connector_rest module against a live NSO instance.

Run this script to test the connector:
    PYTHONPATH=. python agents/compliance/tools/connectors/nso_connector_rest/tests/test_nso_rest.py [--all]

Options:
    --all       Run all tests including write operations (sync-to, redeploy, etc.)
    --device    Specify a device name for device-specific tests (default: first device found)
"""
import sys
import json
import argparse
import logging

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test.nso.rest")

# Import the NSO REST connector functions
from agents.compliance.tools.connectors.nso_connector_rest import (
    get_nso_rest_client,
    get_devices_group,
    get_devices_list,
    get_device_details,
    sync_from_device,
    sync_to_device,
    check_device_sync_status,
    get_compliance_reports_list,
)
from config.config import NSO_HOST, NSO_JSONRPC_PORT, NSO_PROTOCOL, NSO_USERNAME


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_result(name: str, result: dict):
    """Print test result with formatting."""
    status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
    print(f"\n{name}: {status}")
    print("-" * 40)
    print(json.dumps(result, indent=2, default=str)[:1000])  # Limit output
    if len(json.dumps(result, default=str)) > 1000:
        print("... (truncated)")


def test_connection():
    """Test basic connection to NSO."""
    print_header("Connection Test")
    
    print(f"NSO Host: {NSO_HOST}")
    print(f"NSO Port: {NSO_JSONRPC_PORT}")
    print(f"Protocol: {NSO_PROTOCOL}")
    print(f"Username: {NSO_USERNAME}")
    
    client = get_nso_rest_client()
    print(f"Base URL: {client._base_url}")
    
    # Test basic connectivity with a simple GET
    response = client.get("tailf-ncs:devices")
    
    if response.ok:
        print("\n✅ CONNECTION SUCCESSFUL!")
        return True
    else:
        print(f"\n❌ CONNECTION FAILED: {response.status_code}")
        print(f"Error: {response.text}")
        return False


def test_get_devices_list():
    """Test getting device list."""
    print_header("Get Devices List")
    
    result = get_devices_list()
    print_result("get_devices_list()", result)
    
    # Extract device names for later tests
    devices = []
    if result.get("success") and result.get("data"):
        data = result["data"]
        if "tailf-ncs:device" in data:
            devices = [d.get("name") for d in data["tailf-ncs:device"] if d.get("name")]
        print(f"\nFound {len(devices)} device(s): {devices}")
    
    return result.get("success", False), devices


def test_get_devices_group():
    """Test getting device groups."""
    print_header("Get Device Groups")
    
    result = get_devices_group()
    print_result("get_devices_group()", result)
    
    return result.get("success", False)


def test_get_device_details(device_name: str):
    """Test getting device details."""
    print_header(f"Get Device Details: {device_name}")
    
    result = get_device_details(device_name)
    print_result(f"get_device_details('{device_name}')", result)
    
    return result.get("success", False)


def test_check_device_sync_status(device_name: str):
    """Test checking device sync status."""
    print_header(f"Check Sync Status: {device_name}")
    
    result = check_device_sync_status(device_name)
    print_result(f"check_device_sync_status('{device_name}')", result)
    
    return result.get("success", False)


def test_get_compliance_reports():
    """Test getting compliance reports list."""
    print_header("Get Compliance Reports")
    
    result = get_compliance_reports_list()
    print_result("get_compliance_reports_list()", result)
    
    return result.get("success", False)


def test_sync_from_device(device_name: str):
    """Test sync-from operation (device → NSO)."""
    print_header(f"Sync FROM Device: {device_name}")
    
    print("⚠️  This will sync configuration FROM the device to NSO")
    result = sync_from_device(device_name)
    print_result(f"sync_from_device('{device_name}')", result)
    
    return result.get("success", False)


def test_sync_to_device(device_name: str):
    """Test sync-to operation (NSO → device)."""
    print_header(f"Sync TO Device: {device_name}")
    
    print("⚠️  This will sync configuration TO the device from NSO")
    result = sync_to_device(device_name)
    print_result(f"sync_to_device('{device_name}')", result)
    
    return result.get("success", False)


def run_readonly_tests(test_device: str = None):
    """Run read-only tests that don't modify anything."""
    print("\n" + "🔍" * 20)
    print(" RUNNING READ-ONLY TESTS")
    print("🔍" * 20)
    
    results = []
    
    # Test connection
    results.append(("Connection", test_connection()))
    
    # Test get devices
    success, devices = test_get_devices_list()
    results.append(("Get Devices List", success))
    
    # Test get device groups
    results.append(("Get Device Groups", test_get_devices_group()))
    
    # Test compliance reports
    results.append(("Get Compliance Reports", test_get_compliance_reports()))
    
    # Device-specific tests
    device_name = test_device or (devices[0] if devices else None)
    
    if device_name:
        results.append((f"Get Device Details ({device_name})", test_get_device_details(device_name)))
        results.append((f"Check Sync Status ({device_name})", test_check_device_sync_status(device_name)))
    else:
        print("\n⚠️  No devices found - skipping device-specific tests")
    
    return results, device_name


def run_write_tests(device_name: str):
    """Run write tests that modify state."""
    print("\n" + "⚠️" * 20)
    print(" RUNNING WRITE TESTS (MODIFIES STATE)")
    print("⚠️" * 20)
    
    if not device_name:
        print("❌ No device specified for write tests")
        return []
    
    results = []
    
    # Sync-from test
    results.append((f"Sync FROM ({device_name})", test_sync_from_device(device_name)))
    
    # Sync-to test
    results.append((f"Sync TO ({device_name})", test_sync_to_device(device_name)))
    
    return results


def print_summary(results: list):
    """Print test summary."""
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print("-" * 60)
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test NSO RESTCONF connector")
    parser.add_argument("--all", action="store_true", help="Run all tests including write operations")
    parser.add_argument("--device", type=str, help="Device name for device-specific tests")
    args = parser.parse_args()
    
    print_header("NSO RESTCONF Connector Test Suite")
    print(f"Running {'ALL' if args.all else 'READ-ONLY'} tests")
    
    # Run read-only tests
    results, device_name = run_readonly_tests(args.device)
    
    # Run write tests if requested
    if args.all:
        test_device = args.device or device_name
        write_results = run_write_tests(test_device)
        results.extend(write_results)
    
    # Print summary
    print_summary(results)
    
    # Exit with appropriate code
    failed = sum(1 for _, success in results if not success)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
