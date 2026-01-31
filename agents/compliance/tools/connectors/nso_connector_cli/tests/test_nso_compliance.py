"""
NSO Compliance Reporting Integration Tests.

This test module provides integration tests for the NSO Compliance Manager.
Tests are designed to run against a live NSO instance configured via environment variables.

Prerequisites:
    - NSO instance running and accessible
    - Environment variables configured in .env file:
        NSO_HOST, NSO_PORT, NSO_USERNAME, NSO_PASSWORD, etc.
    - pyATS and unicon packages installed

Usage:
    # Run all tests
    pytest agents/compliance/tools/connectors/nso_connector_cli/tests/test_nso_compliance.py -v
    
    # Run specific test category
    pytest agents/compliance/tools/connectors/nso_connector_cli/tests/test_nso_compliance.py -v -k "report"
    
    # Run with print output
    pytest agents/compliance/tools/connectors/nso_connector_cli/tests/test_nso_compliance.py -v -s
"""

import pytest
import logging
from typing import Generator

from agents.compliance.tools.connectors.nso_connector_cli.nso_client_cli import NSOClient
from agents.compliance.tools.connectors.nso_connector_cli.compliance_manager import NSOComplianceManager

# Configure logging for test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def nso_client() -> Generator[NSOClient, None, None]:
    """
    Creates an NSO client using environment variables.
    Automatically disconnects after all tests in module complete.
    """
    client = NSOClient()  # Uses env vars from config
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def compliance_manager(nso_client: NSOClient) -> NSOComplianceManager:
    """Creates a compliance manager instance for testing."""
    return NSOComplianceManager(nso_client)


# =============================================================================
# 1. COMPLIANCE REPORT CONFIGURATION TESTS
# =============================================================================

class TestComplianceReportConfiguration:
    """Tests for configuring compliance report definitions."""
    
    TEST_REPORT_PREFIX = "pytest-test-"
    
    def test_configure_report_device_check_all(self, compliance_manager: NSOComplianceManager):
        """Test: Configure a compliance report that checks ALL devices."""
        report_name = f"{self.TEST_REPORT_PREFIX}device-check-all"
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True
        )
        
        logger.info(f"Configure device-check-all result:\n{result}")
        assert result is not None
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_configure_report_specific_devices(self, compliance_manager: NSOComplianceManager):
        """Test: Configure a compliance report for specific devices."""
        report_name = f"{self.TEST_REPORT_PREFIX}specific-devices"
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_devices=["ios-1"],
            device_current_out_of_sync=True
        )
        
        logger.info(f"Configure specific devices result:\n{result}")
        assert result is not None
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_configure_report_device_groups(self, compliance_manager: NSOComplianceManager):
        """Test: Configure a compliance report for device groups."""
        report_name = f"{self.TEST_REPORT_PREFIX}device-groups"
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_device_groups=["IOS-DEVICES", "IOS-XR-DEVICES"]
        )
        
        logger.info(f"Configure device groups result:\n{result}")
        assert result is not None
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_configure_report_service_check_all(self, compliance_manager: NSOComplianceManager):
        """Test: Configure a compliance report that checks ALL services."""
        report_name = f"{self.TEST_REPORT_PREFIX}service-check-all"
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            service_check_all=True
        )
        
        logger.info(f"Configure service-check-all result:\n{result}")
        assert result is not None
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_configure_report_service_types(self, compliance_manager: NSOComplianceManager):
        """Test: Configure a compliance report for specific service types."""
        report_name = f"{self.TEST_REPORT_PREFIX}service-types"
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            service_check_service_types=["/l3vpn:vpn/l3vpn:l3vpn"]
        )
        
        logger.info(f"Configure service types result:\n{result}")
        assert result is not None
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_configure_report_combined(self, compliance_manager: NSOComplianceManager):
        """Test: Configure a comprehensive compliance report with devices, templates, and services."""
        report_name = f"{self.TEST_REPORT_PREFIX}combined-check"
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True,
            device_check_templates=["ntp_dns"],
            service_check_service_types=["loopback-tunisie:loopback-tunisie"]
        )
        
        logger.info(f"Configure combined report result:\n{result}")
        assert result is not None
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_show_compliance_report_config(self, compliance_manager: NSOComplianceManager):
        """Test: Show configuration of a specific compliance report."""
        # First create a report
        report_name = f"{self.TEST_REPORT_PREFIX}show-config"
        compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True
        )
        
        # Show the config
        result = compliance_manager.show_compliance_report_config(report_name)
        logger.info(f"Show report config result:\n{result}")
        assert result is not None
        
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_show_all_compliance_report_configs(self, compliance_manager: NSOComplianceManager):
        """Test: Show configuration of ALL compliance reports."""
        result = compliance_manager.show_compliance_report_config()
        logger.info(f"Show all report configs result:\n{result}")
        assert result is not None


# =============================================================================
# 2. COMPLIANCE REPORT EXECUTION TESTS
# =============================================================================

class TestComplianceReportExecution:
    """Tests for executing compliance reports and viewing results."""
    
    TEST_REPORT_PREFIX = "pytest-exec-"
    
    def test_run_compliance_report_text(self, compliance_manager: NSOComplianceManager):
        """Test: Run a compliance report with text output format."""
        report_name = f"{self.TEST_REPORT_PREFIX}text-report"
        
        # Configure the report first
        compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True
        )
        
        # Run the report
        result = compliance_manager.run_compliance_report(
            report_name=report_name,
            title="PyTest Text Report",
            outformat="text"
        )
        
        logger.info(f"Run text report result:\n{result}")
        assert result is not None
        
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_run_compliance_report_html(self, compliance_manager: NSOComplianceManager):
        """Test: Run a compliance report with HTML output format."""
        report_name = f"{self.TEST_REPORT_PREFIX}html-report"
        
        # Configure the report first
        compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True
        )
        
        # Run the report
        result = compliance_manager.run_compliance_report(
            report_name=report_name,
            title="PyTest HTML Report",
            outformat="html"
        )
        
        logger.info(f"Run HTML report result:\n{result}")
        assert result is not None
        
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_run_compliance_report_with_time_range(self, compliance_manager: NSOComplianceManager):
        """Test: Run a compliance report with specific time range."""
        report_name = f"{self.TEST_REPORT_PREFIX}time-range-report"
        
        # Configure the report first
        compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True
        )
        
        # Run the report with time constraints
        result = compliance_manager.run_compliance_report(
            report_name=report_name,
            title="Q1 2025 Audit",
            from_time="2025-01-01T00:00:00",
            to_time="2025-03-31T23:59:59",
            outformat="html"
        )
        
        logger.info(f"Run time-range report result:\n{result}")
        assert result is not None
        
        # Cleanup
        compliance_manager.delete_compliance_report(report_name)
    
    def test_list_compliance_reports(self, compliance_manager: NSOComplianceManager):
        """Test: List all compliance report results."""
        result = compliance_manager.list_compliance_reports()
        logger.info(f"List compliance reports result:\n{result}")
        assert result is not None


# =============================================================================
# 3. COMPLIANCE TEMPLATE TESTS
# =============================================================================

class TestComplianceTemplates:
    """Tests for compliance template management."""
    
    TEST_TEMPLATE_PREFIX = "pytest-tmpl-"
    
    def test_create_compliance_template_from_device_template(self, compliance_manager: NSOComplianceManager):
        """Test: Create a compliance template from an existing device template."""
        template_name = f"{self.TEST_TEMPLATE_PREFIX}from-device-tmpl"
        
        result = compliance_manager.create_compliance_template(
            template_name=template_name,
            device_template="ntp_dns"
        )
        
        logger.info(f"Create template from device template result:\n{result}")
        assert result is not None
        
        # Cleanup
        compliance_manager.delete_compliance_template(template_name)
    
    @pytest.mark.skip(reason="Requires specific device config path - customize for your environment")
    def test_create_compliance_template_from_paths(self, compliance_manager: NSOComplianceManager):
        """Test: Create a compliance template from device configuration paths."""
        template_name = f"{self.TEST_TEMPLATE_PREFIX}from-paths"
        
        result = compliance_manager.create_compliance_template(
            template_name=template_name,
            paths=["/devices/device[device-type/netconf/ned-id='router-nc-1.0:router-nc-1.0']/config/sys/syslog"]
        )
        
        logger.info(f"Create template from paths result:\n{result}")
        assert result is not None
        
        # Cleanup
        compliance_manager.delete_compliance_template(template_name)
    
    def test_check_compliance_template(self, compliance_manager: NSOComplianceManager):
        """Test: Check a compliance template against specific devices."""
        # Note: This test assumes 'ntp_dns' template exists in your NSO
        result = compliance_manager.check_compliance_template(
            template_name="ntp_dns",
            devices=["ios-0", "ios-1"]
        )
        
        logger.info(f"Check compliance template result:\n{result}")
        assert result is not None
    
    def test_show_compliance_templates(self, compliance_manager: NSOComplianceManager):
        """Test: Show all compliance templates."""
        result = compliance_manager.show_compliance_templates()
        logger.info(f"Show all templates result:\n{result}")
        assert result is not None
    
    def test_show_specific_compliance_template(self, compliance_manager: NSOComplianceManager):
        """Test: Show a specific compliance template."""
        # Note: This test assumes 'ntp_dns' template exists in your NSO
        result = compliance_manager.show_compliance_templates(template_name="ntp_dns")
        logger.info(f"Show specific template result:\n{result}")
        assert result is not None


# =============================================================================
# 4. CLEANUP TESTS
# =============================================================================

class TestCleanupOperations:
    """Tests for cleanup operations."""
    
    @pytest.mark.skip(reason="Destructive operation - run manually when needed")
    def test_remove_compliance_report_results(self, compliance_manager: NSOComplianceManager):
        """Test: Remove compliance report results by ID range."""
        result = compliance_manager.remove_compliance_report_results("1..3")
        logger.info(f"Remove report results:\n{result}")
        assert result is not None
    
    @pytest.mark.skip(reason="Destructive operation - run manually when needed")
    def test_delete_compliance_report(self, compliance_manager: NSOComplianceManager):
        """Test: Delete a compliance report definition."""
        result = compliance_manager.delete_compliance_report("CUSTOM-DATE-USER")
        logger.info(f"Delete report result:\n{result}")
        assert result is not None
    
    @pytest.mark.skip(reason="Destructive operation - run manually when needed")
    def test_delete_compliance_template(self, compliance_manager: NSOComplianceManager):
        """Test: Delete a compliance template."""
        result = compliance_manager.delete_compliance_template("internal-dns")
        logger.info(f"Delete template result:\n{result}")
        assert result is not None


# =============================================================================
# MANUAL TEST RUNNER (for quick testing without pytest)
# =============================================================================

if __name__ == "__main__":
    """
    Run this file directly for quick manual testing:
        python -m agents.compliance.tools.connectors.nso_connector_cli.tests.test_nso_compliance
    """
    print("=" * 70)
    print("NSO COMPLIANCE REPORTING - MANUAL TEST RUNNER")
    print("=" * 70)
    
    # Initialize client and manager
    client = NSOClient()
    manager = NSOComplianceManager(client)
    
    try:
        # =======================================================================
        # 1. CONFIGURE COMPLIANCE REPORTS
        # =======================================================================
        print("\n--- 1. CONFIGURE COMPLIANCE REPORTS ---")
        
        # Uncomment tests you want to run:
        
        # Test: Check all devices
        # print("\n[TEST] Configure device-check-all report...")
        # result = manager.configure_compliance_report("device-check-all", device_check_all=True)
        # print(result)
        
        # Test: Check specific devices
        # print("\n[TEST] Configure specific device report...")
        # result = manager.configure_compliance_report("test-template", device_check_devices=["ios-1"], device_current_out_of_sync=True)
        # print(result)
        
        # Test: Check device groups
        # print("\n[TEST] Configure device group report...")
        # result = manager.configure_compliance_report("group-check", device_check_device_groups=["IOS-DEVICES", "IOS-XR-DEVICES"])
        # print(result)
        
        # Test: Check all services
        print("\n[TEST] Configure service-check-all report...")
        result = manager.configure_compliance_report("service-check-all-pytest-dry", service_check_all=True, dry_run=True)
        print(result)
        
        # Test: Check specific service types
        # print("\n[TEST] Configure service types report...")
        # result = manager.configure_compliance_report("l3vpn-check", service_check_service_types=["/l3vpn:vpn/l3vpn:l3vpn"])
        # print(result)
        
        # Test: Combined check with templates
        # print("\n[TEST] Configure combined report with templates...")
        # result = manager.configure_compliance_report(
        #     "SALUDOS-gold-check",
        #     device_check_all=True,
        #     device_check_templates=["ntp_dns"],
        #     service_check_service_types=["loopback-tunisie:loopback-tunisie"]
        # )
        # print(result)
        
        # =======================================================================
        # 2. RUN COMPLIANCE REPORTS
        # =======================================================================
        print("\n--- 2. RUN COMPLIANCE REPORTS ---")
        
        # Test: Run report with HTML output
        # print("\n[TEST] Run group-check report (HTML)...")
        # result = manager.run_compliance_report("group-check", title="My First Report from python", outformat="html")
        # print(result)
        
        # Test: Run report with time range
        # print("\n[TEST] Run gold-check report with time range...")
        # result = manager.run_compliance_report(
        #     "gold-check",
        #     title="Q1 2025 Audit",
        #     from_time="2025-01-01T00:00:00",
        #     to_time="2025-03-31T23:59:59",
        #     outformat="html"
        # )
        # print(result)
        
        # =======================================================================
        # 3. LIST/SHOW COMPLIANCE REPORTS
        # =======================================================================
        # print("\n--- 3. LIST/SHOW COMPLIANCE REPORTS ---")
        
        # Test: List all report results
        # print("\n[TEST] List all compliance report results...")
        # result = manager.list_compliance_reports()
        # print(result)
        
        # Test: Show specific report config
        # print("\n[TEST] Show SALUDOS-gold-check configuration...")
        # result = manager.show_compliance_report_config("SALUDOS-gold-check")
        # print(result)
        
        # =======================================================================
        # 4. COMPLIANCE TEMPLATES
        # =======================================================================
        print("\n--- 4. COMPLIANCE TEMPLATES ---")
        
        # Test: Create template from device template
        # print("\n[TEST] Create compliance template from device template...")
        # result = manager.create_compliance_template("internal-dns", device_template="ntp_dns")
        # print(result)
        
        # Test: Create template from paths
        # print("\n[TEST] Create compliance template from paths...")
        # result = manager.create_compliance_template(
        #     "syslog",
        #     paths=["/devices/device[device-type/netconf/ned-id='router-nc-1.0:router-nc-1.0']/config/sys/syslog"]
        # )
        # print(result)
        
        # Test: Check template against devices
        # print("\n[TEST] Check ntp_dns template against devices...")
        # result = manager.check_compliance_template("ntp_dns", devices=["ios-0", "ios-1"])
        # print(result)
        
        # Test: Show all templates
        # print("\n[TEST] Show all compliance templates...")
        # result = manager.show_compliance_templates()
        # print(result)
        
        # =======================================================================
        # 5. CLEANUP (USE WITH CAUTION)
        # =======================================================================
        # print("\n--- 5. CLEANUP (commented out for safety) ---")
        
        # WARNING: These operations are destructive!
        
        # Remove report results by ID range
        # print("\n[TEST] Remove report results 1..3...")
        # result = manager.remove_compliance_report_results("1..3")
        # print(result)
        
        # Delete a report definition
        # print("\n[TEST] Delete CUSTOM-DATE-USER report...")
        # result = manager.delete_compliance_report("CUSTOM-DATE-USER")
        # print(result)
        
        # Delete a template
        # print("\n[TEST] Delete internal-dns template...")
        # result = manager.delete_compliance_template("internal-dns")
        # print(result)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always disconnect
        print("\n" + "=" * 70)
        print("Disconnecting from NSO...")
        client.disconnect()
        print("Done!")
