"""
NSO Compliance Dry-Run Integration Tests.

Tests the dry-run functionality for compliance report configuration.
This validates the HITL (Human-in-the-Loop) workflow where:
1. Preview changes with dry_run=True
2. User confirms the changes
3. Apply changes with dry_run=False

Prerequisites:
    - NSO instance running and accessible
    - Environment variables configured in .env file
    - pyATS and unicon packages installed

Usage:
    # Run dry-run tests only
    PYTHONPATH=. uv run pytest agents/compliance/tools/connectors/nso_connector_cli/tests/test_dry_run.py -v -s
    
    # Run a specific test
    PYTHONPATH=. uv run pytest agents/compliance/tools/connectors/nso_connector_cli/tests/test_dry_run.py::TestDryRunWorkflow::test_dry_run_shows_preview -v -s
"""

import pytest
import logging
import re
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
    client = NSOClient()
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def compliance_manager(nso_client: NSOClient) -> NSOComplianceManager:
    """Creates a compliance manager instance for testing."""
    return NSOComplianceManager(nso_client)


@pytest.fixture
def test_report_name() -> str:
    """Generates a unique test report name."""
    return "pytest-dry-run-test"


# =============================================================================
# DRY-RUN WORKFLOW TESTS
# =============================================================================

class TestDryRunWorkflow:
    """
    Tests for the dry-run workflow:
    1. dry_run=True → Preview changes (no commit)
    2. dry_run=False → Apply changes (commit)
    """
    
    def test_dry_run_shows_preview(
        self, 
        compliance_manager: NSOComplianceManager, 
        test_report_name: str
    ):
        """
        Test: Dry-run should show a preview of changes in CLI diff format.
        
        Expected output format:
        ```
        cli {
            local-node {
                data  compliance {
                          reports {
                     +        report pytest-dry-run-test {
                     +            device-check {
                     +                all-devices;
                     +            }
                     +        }
                          }
                      }
            }
        }
        ```
        """
        logger.info("=" * 60)
        logger.info("TEST: Dry-run Preview (dry_run=True)")
        logger.info("=" * 60)
        
        # Step 1: Call with dry_run=True to preview changes
        result = compliance_manager.configure_compliance_report(
            report_name=test_report_name,
            device_check_all=True,
            dry_run=True  # 👈 PREVIEW ONLY
        )
        
        logger.info(f"\n📋 DRY-RUN OUTPUT:\n{result}")
        
        # Assertions for dry-run output
        assert result is not None, "Dry-run should return output"
        
        # Check that the output contains CLI diff format indicators
        # The 'cli {' block indicates CLI format output
        assert "cli" in result.lower() or "local-node" in result.lower(), \
            "Dry-run output should contain CLI diff format"
        
        # Check for the '+' indicator showing additions
        assert "+" in result, \
            "Dry-run output should show '+' for additions"
        
        # Check that our report name appears in the preview
        assert test_report_name in result, \
            f"Dry-run should show report name '{test_report_name}' in preview"
        
        logger.info("✅ Dry-run preview shows expected CLI diff format")
    
    def test_dry_run_does_not_commit(
        self, 
        compliance_manager: NSOComplianceManager,
        nso_client: NSOClient,
        test_report_name: str
    ):
        """
        Test: Dry-run should NOT commit changes to NSO.
        After a dry-run, the report should NOT exist.
        """
        logger.info("=" * 60)
        logger.info("TEST: Dry-run Does NOT Commit")
        logger.info("=" * 60)
        
        # Ensure report doesn't exist first (cleanup)
        try:
            compliance_manager.delete_compliance_report(test_report_name)
        except Exception:
            pass  # Report might not exist
        
        # Step 1: Run dry-run
        result = compliance_manager.configure_compliance_report(
            report_name=test_report_name,
            device_check_all=True,
            dry_run=True  # 👈 PREVIEW ONLY
        )
        
        logger.info(f"Dry-run output:\n{result}")
        
        # Step 2: Verify the report was NOT created
        # Try to show the report - it should NOT exist
        show_output = nso_client.execute_read(
            f"show running-config compliance reports report {test_report_name}"
        )
        
        logger.info(f"Show report output after dry-run:\n{show_output}")
        
        # The report should not exist after dry-run
        # NSO returns empty or error when report doesn't exist
        report_exists = test_report_name in show_output and "device-check" in show_output
        
        assert not report_exists, \
            f"Report '{test_report_name}' should NOT exist after dry-run (no commit)"
        
        logger.info("✅ Dry-run correctly did NOT commit changes")
    
    def test_full_dry_run_then_commit_workflow(
        self, 
        compliance_manager: NSOComplianceManager,
        nso_client: NSOClient,
        test_report_name: str
    ):
        """
        Test: Full HITL workflow:
        1. Preview with dry_run=True
        2. "User confirms" (simulated)
        3. Apply with dry_run=False
        4. Verify report exists
        """
        logger.info("=" * 60)
        logger.info("TEST: Full Dry-Run → Confirm → Commit Workflow")
        logger.info("=" * 60)
        
        # Cleanup first
        try:
            compliance_manager.delete_compliance_report(test_report_name)
        except Exception:
            pass
        
        # ===== STEP 1: PREVIEW (dry_run=True) =====
        logger.info("\n🔍 STEP 1: Preview changes (dry_run=True)")
        preview_result = compliance_manager.configure_compliance_report(
            report_name=test_report_name,
            device_check_all=True,
            device_check_templates=["ntp_dns"],
            dry_run=True
        )
        
        logger.info(f"Preview output:\n{preview_result}")
        assert "+" in preview_result, "Preview should show '+' additions"
        
        # ===== STEP 2: USER CONFIRMATION (simulated) =====
        logger.info("\n✋ STEP 2: User confirms: 'Yes, apply these changes'")
        user_confirmed = True  # Simulating user approval
        
        # ===== STEP 3: COMMIT (dry_run=False) =====
        if user_confirmed:
            logger.info("\n💾 STEP 3: Applying changes (dry_run=False)")
            commit_result = compliance_manager.configure_compliance_report(
                report_name=test_report_name,
                device_check_all=True,
                device_check_templates=["ntp_dns"],
                dry_run=False  # 👈 ACTUAL COMMIT
            )
            
            logger.info(f"Commit output:\n{commit_result}")
        
        # ===== STEP 4: VERIFY REPORT EXISTS =====
        logger.info("\n🔎 STEP 4: Verify report was created")
        show_output = nso_client.execute_read(
            f"show running-config compliance reports report {test_report_name}"
        )
        
        logger.info(f"Show report output:\n{show_output}")
        
        # Verify the report exists with expected configuration
        assert test_report_name in show_output, \
            f"Report '{test_report_name}' should exist after commit"
        assert "device-check" in show_output.lower() or "all-devices" in show_output.lower(), \
            "Report should contain device-check configuration"
        
        logger.info("✅ Full workflow completed: Dry-run → Confirm → Commit ✅")
        
        # Cleanup
        logger.info("\n🧹 Cleanup: Deleting test report")
        compliance_manager.delete_compliance_report(test_report_name)
    
    def test_dry_run_output_contains_diff_markers(
        self,
        compliance_manager: NSOComplianceManager,
        test_report_name: str
    ):
        """
        Test: Verify dry-run output format is CLI diff style.
        
        Expected markers:
        - '+' for lines to be added
        - '-' for lines to be removed (when modifying existing)
        """
        logger.info("=" * 60)
        logger.info("TEST: Verify CLI Diff Format Markers")
        logger.info("=" * 60)
        
        result = compliance_manager.configure_compliance_report(
            report_name=test_report_name,
            device_check_devices=["ios-1", "ios-2"],
            dry_run=True
        )
        
        logger.info(f"Dry-run output:\n{result}")
        
        # Count the '+' markers in the output
        plus_count = result.count("+")
        
        logger.info(f"Found {plus_count} '+' markers indicating additions")
        
        assert plus_count > 0, \
            "Dry-run output should contain '+' markers for additions"
        
        # Check for report name in additions
        # Pattern: lines with '+' that contain the report name
        lines_with_plus = [line for line in result.split('\n') if '+' in line]
        logger.info(f"Lines with additions:\n" + "\n".join(lines_with_plus))
        
        report_in_additions = any(test_report_name in line for line in lines_with_plus)
        assert report_in_additions, \
            f"Report name '{test_report_name}' should appear in '+' lines"
        
        logger.info("✅ CLI diff format markers verified")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestDryRunEdgeCases:
    """Tests for edge cases and error handling in dry-run workflow."""
    
    def test_dry_run_with_invalid_template(
        self,
        compliance_manager: NSOComplianceManager
    ):
        """
        Test: Dry-run with a non-existent template.
        Should still show preview but may include warnings.
        """
        logger.info("=" * 60)
        logger.info("TEST: Dry-run with Non-existent Template")
        logger.info("=" * 60)
        
        result = compliance_manager.configure_compliance_report(
            report_name="pytest-invalid-template-test",
            device_check_all=True,
            device_check_templates=["non_existent_template_12345"],
            dry_run=True
        )
        
        logger.info(f"Dry-run output with invalid template:\n{result}")
        
        # The dry-run should still execute and return output
        assert result is not None, "Dry-run should return output even with invalid template"
        
        logger.info("✅ Dry-run handles invalid template gracefully")
    
    def test_multiple_dry_runs_are_idempotent(
        self,
        compliance_manager: NSOComplianceManager,
        nso_client: NSOClient
    ):
        """
        Test: Multiple dry-runs should be idempotent (no side effects).
        Running dry-run multiple times should not create anything.
        """
        logger.info("=" * 60)
        logger.info("TEST: Multiple Dry-Runs are Idempotent")
        logger.info("=" * 60)
        
        report_name = "pytest-idempotent-test"
        
        # Cleanup first
        try:
            compliance_manager.delete_compliance_report(report_name)
        except Exception:
            pass
        
        # Run dry-run multiple times
        for i in range(3):
            logger.info(f"\n--- Dry-run #{i+1} ---")
            result = compliance_manager.configure_compliance_report(
                report_name=report_name,
                device_check_all=True,
                dry_run=True
            )
            logger.info(f"Output: {result[:200]}...")  # First 200 chars
        
        # Verify nothing was created
        show_output = nso_client.execute_read(
            f"show running-config compliance reports report {report_name}"
        )
        
        report_exists = report_name in show_output and "device-check" in show_output
        
        assert not report_exists, \
            "Report should NOT exist after multiple dry-runs"
        
        logger.info("✅ Multiple dry-runs are idempotent (no side effects)")


# =============================================================================
# VERBOSE OUTPUT TEST (for demos)
# =============================================================================

class TestDryRunDemo:
    """Demo tests that show detailed dry-run output for presentation purposes."""
    
    def test_demo_dry_run_output(
        self,
        compliance_manager: NSOComplianceManager
    ):
        """
        Demo: Shows a comprehensive dry-run output for demonstration.
        This test is useful for demos and presentations.
        """
        logger.info("\n" + "=" * 70)
        logger.info("🎬 DEMO: Dry-Run Output for Compliance Report Configuration")
        logger.info("=" * 70)
        
        report_name = "demo-compliance-audit"
        
        logger.info(f"""
📋 CONFIGURATION REQUEST:
   Report Name: {report_name}
   Device Check: All devices
   Templates: ntp_dns
   Services: Check all services
        """)
        
        logger.info("\n📤 Calling configure_nso_compliance_report(dry_run=True)...")
        
        result = compliance_manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=True,
            device_check_templates=["ntp_dns"],
            service_check_all=True,
            dry_run=True
        )
        
        logger.info(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                     🔍 DRY-RUN PREVIEW OUTPUT                        ║
╚══════════════════════════════════════════════════════════════════════╝
{result}
        """)
        
        logger.info("""
╔══════════════════════════════════════════════════════════════════════╗
║                        📝 INTERPRETATION                             ║
╠══════════════════════════════════════════════════════════════════════╣
║  ➕ Lines with '+' = Will be ADDED                                   ║
║  ➖ Lines with '-' = Will be REMOVED                                 ║
║  📌 This is a PREVIEW - no changes have been made yet!               ║
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        logger.info("💬 Ask user: 'Would you like me to apply this configuration? (Yes/No)'")
        
        assert result is not None
        logger.info("\n✅ Demo complete!")
