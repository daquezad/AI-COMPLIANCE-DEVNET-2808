"""
NSO Compliance Reporting Tools for LangChain Agent.

This module provides LangChain-compatible tools for Cisco NSO compliance management using pyATS.
The compliance reporting system allows network engineers to verify that device configurations 
match expected states (Golden Configs) and track configuration drift over time.

WORKFLOW OVERVIEW:
1. configure_nso_compliance_report: Create a report DEFINITION (what to check)
2. run_nso_compliance_report: EXECUTE the report (perform the actual compliance check)
3. list_nso_compliance_results: VIEW all historical report RESULTS
4. create_nso_compliance_template: Create a GOLDEN CONFIG template to check against

KEY CONCEPTS:
- Report Definition: Specifies WHAT devices/services to audit and WHAT templates to check against
- Report Execution: Runs the actual compliance check and generates a timestamped result
- Report Results: Historical audit results showing violations and compliance status
- Compliance Template: The "Golden Config" standard that devices should match
"""

import logging
import json
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool

from agents.compliance.tools.connectors.nso_connector_cli.nso_client_cli import NSOClient
from agents.compliance.tools.connectors.nso_connector_cli.compliance_manager import NSOComplianceManager
# from agents.compliance.tools.connectors.nso_connector_cli.exeptions import NSOCLIError


# from exceptions import NSOCLIError

# Initialize Logger
logger = logging.getLogger("devnet.compliance.tools.nso")

# --- INITIALIZATION ---
# NSOClient will auto-generate testbed from environment variables if no path is provided
# Required env vars: NSO_HOST, NSO_PORT, NSO_USERNAME, NSO_PASSWORD
_client = NSOClient()  # Uses environment variables for connection settings
_manager = NSOComplianceManager(_client)

# =============================================================================
# LANGCHAIN TOOLS FOR NSO COMPLIANCE REPORTING
# =============================================================================

@tool
def configure_nso_compliance_report(
    report_name: str,
    device_check_all: bool = False,
    device_check_devices: Optional[List[str]] = None,
    device_check_templates: Optional[List[str]] = None,
    service_check_all: bool = False,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Step 1 of Compliance Workflow: Create or update a compliance report DEFINITION in NSO.
    
    IMPORTANT WORKFLOW - TWO-STEP PROCESS:
    1. FIRST CALL with dry_run=True (default): Preview what will be configured. Show output to user for confirmation.
    2. SECOND CALL with dry_run=False: Actually commit the configuration after user confirms.
    
    This tool DOES NOT run the compliance check - it only defines WHAT should be checked.
    After configuring, use 'run_nso_compliance_report' to execute the actual audit.
    
    PURPOSE: Define which devices, services, and compliance templates should be included
    in the network configuration verification.
    
    DEVICE SELECTION (choose one):
    - device_check_all=True: Audit ALL managed devices in NSO
    - device_check_devices=["router1", "switch1"]: Audit specific devices only
    
    COMPLIANCE TEMPLATES:
    - device_check_templates=["ntp-standard", "acl-baseline"]: Check devices against 
      these Golden Config templates to find configuration drift
    
    SERVICE SELECTION:
    - service_check_all=True: Verify all NSO service instances are in-sync
    
    Args:
        report_name: Unique identifier for this report definition (e.g., "weekly-audit", "dc-core-check")
        device_check_all: True to include ALL devices. Mutually exclusive with device_check_devices.
        device_check_devices: List of specific device names to audit. Mutually exclusive with device_check_all.
        device_check_templates: List of compliance template names to validate devices against.
        service_check_all: True to verify all service instances are synchronized.
        dry_run: If True (default), preview changes without committing. If False, commit the configuration.
    
    Returns:
        success: True if operation completed
        message: Status message
        dry_run: Whether this was a dry-run (preview) or actual commit
        nso_output: NSO CLI output showing the configuration or dry-run preview
        requires_confirmation: True if dry_run was True and user should confirm before committing
    
    Example Workflow:
        1. Call with dry_run=True → Show preview to user → Ask "Do you want to apply this configuration?"
        2. If user confirms → Call again with dry_run=False to commit
    """
    logger.info(f"LLM Tool Call: configure_nso_compliance_report -> {report_name} (dry_run={dry_run})")
    try:
        output = _manager.configure_compliance_report(
            report_name=report_name,
            device_check_all=device_check_all,
            device_check_devices=device_check_devices,
            device_check_templates=device_check_templates,
            service_check_all=service_check_all,
            dry_run=dry_run
        )
        
        if dry_run:
            return {
                "success": True,
                "message": f"DRY-RUN: Preview of report '{report_name}' configuration. No changes committed yet.",
                "dry_run": True,
                "requires_confirmation": True,
                "nso_output": output,
                "next_step": "Ask user to confirm. If approved, call again with dry_run=False to commit."
            }
        else:
            return {
                "success": True,
                "message": f"Report '{report_name}' has been configured and committed to NSO.",
                "dry_run": False,
                "requires_confirmation": False,
                "nso_output": output
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def run_nso_compliance_report(
    report_name: str,
    outformat: str = "text",
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Step 2 of Compliance Workflow: EXECUTE an existing compliance report definition.
    
    This tool RUNS the actual compliance check and generates a timestamped result.
    The report definition must already exist (created via 'configure_nso_compliance_report').
    
    PURPOSE: Perform the compliance audit NOW and generate a report showing:
    - Which devices are IN-SYNC vs OUT-OF-SYNC with NSO
    - Which devices VIOLATE compliance templates (Golden Config deviations)
    - Service synchronization status
    
    OUTPUT FORMATS:
    - text: Human-readable plain text (default, best for quick review)
    - html: Web-viewable report with formatting (best for sharing)
    - xml: DocBook XML format (best for automation/parsing)
    - sqlite: Database format (best for historical analysis)
    
    Args:
        report_name: Name of the existing report definition to execute (must exist in NSO)
        outformat: Output format - 'text', 'html', 'xml', or 'sqlite' (default: 'text')
        title: Optional descriptive title for this run (e.g., "Q1 2025 Audit", "Pre-Change Check")
    
    Returns:
        success: True if report executed successfully
        report_name: Name of the executed report
        format: Output format used
        nso_output: Contains the report location URL and execution summary
    
    Example Usage:
        - "Run the weekly audit" → report_name="weekly-audit"
        - "Generate an HTML compliance report titled Q1 Review" → report_name="...", outformat="html", title="Q1 Review"
    """
    logger.info(f"LLM Tool Call: run_nso_compliance_report -> {report_name}")
    try:
        output = _manager.run_compliance_report(
            report_name=report_name,
            outformat=outformat,
            title=title
        )
        return {
            "success": True, 
            "report_name": report_name,
            "format": outformat,
            "nso_output": output
        }
    except NSOError as e:
        return {"success": False, "error": str(e)}


@tool
def list_nso_compliance_results() -> Dict[str, Any]:
    """
    Step 3 of Compliance Workflow: VIEW all historical compliance report RESULTS.
    
    This tool retrieves the LIST of all previously executed compliance reports stored in NSO.
    Use this to see what audits have been performed and their outcomes.
    
    PURPOSE: Get an overview of all compliance audit history including:
    - Report ID: Unique numeric identifier for each executed report
    - Report Name: The report definition that was executed
    - Title: The user-provided title for that execution
    - Time: When the report was generated
    - Who: Which user triggered the report
    - Compliance Status: 'compliant' or 'violations' detected
    - Location: URL to download/view the full report
    
    WHEN TO USE:
    - To find a specific report ID for detailed analysis
    - To check if a report has been run recently
    - To track compliance status over time
    - Before removing old reports
    
    Returns:
        success: True if query was successful
        data: Raw NSO output containing all report results with their metadata
    
    Example Usage:
        - "Show me all compliance reports" → list_nso_compliance_results()
        - "What audits have been run?" → list_nso_compliance_results()
    """
    logger.info("LLM Tool Call: list_nso_compliance_results")
    try:
        output = _manager.list_compliance_reports()
        return {"success": True, "data": output}
    except NSOError as e:
        return {"success": False, "error": str(e)}


@tool
def create_nso_compliance_template(
    template_name: str,
    device_template: str
) -> Dict[str, Any]:
    """
    Create a GOLDEN CONFIG compliance template from an existing NSO device template.
    
    Compliance templates define the EXPECTED configuration state that devices should match.
    They are used in compliance reports to detect configuration DRIFT from the standard.
    
    PURPOSE: Convert an NSO device template into a compliance template that can:
    - Check if devices match the expected configuration
    - Support regular expressions for flexible matching
    - Define variables that get values at report runtime
    - Detect deviations from network standards
    
    HOW IT WORKS:
    1. You have an existing NSO device template (e.g., "ntp-standard" that configures NTP servers)
    2. This tool converts it to a compliance template
    3. When a report runs, it checks if devices match this template configuration
    4. Deviations are reported as compliance violations
    
    WORKFLOW:
    1. First, ensure the device template exists in NSO
    2. Use this tool to create the compliance template
    3. Add the template to a report definition via 'configure_nso_compliance_report'
    4. Run the report to check devices against this Golden Config
    
    Args:
        template_name: Name for the new compliance template (e.g., "ntp-compliance", "acl-baseline")
        device_template: Name of the EXISTING NSO device template to copy from (must already exist in NSO)
    
    Returns:
        success: True if template was created and committed
        template: Name of the created compliance template
        nso_output: Raw NSO CLI output for debugging
    
    Example Usage:
        - "Create a compliance template for NTP from the ntp-config device template" 
          → template_name="ntp-compliance", device_template="ntp-config"
    """
    logger.info(f"LLM Tool Call: create_nso_compliance_template -> {template_name}")
    try:
        output = _manager.create_compliance_template(
            template_name=template_name,
            device_template=device_template
        )
        return {"success": True, "template": template_name, "nso_output": output}
    except NSOError as e:
        return {"success": False, "error": str(e)}


# Export the list of tools for LangChain Agent initialization
# These tools follow a typical compliance workflow:
# 1. configure_nso_compliance_report - Define what to audit
# 2. run_nso_compliance_report - Execute the audit
# 3. list_nso_compliance_results - View audit history
# 4. create_nso_compliance_template - Create Golden Config templates
nso_compliance_toolset = [
    configure_nso_compliance_report,
    run_nso_compliance_report,
    list_nso_compliance_results,
    create_nso_compliance_template
]