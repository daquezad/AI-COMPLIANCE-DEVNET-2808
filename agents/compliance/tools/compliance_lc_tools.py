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
import tempfile
import os
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool

from agents.compliance.tools.connectors.nso_connector_cli.nso_client_cli import NSOCLIClient
from agents.compliance.tools.connectors.nso_connector_cli.compliance_manager import NSOComplianceManager
from agents.compliance.tools.connectors.nso_connector_cli.exeptions import NSOCLIError
from agents.compliance.tools.connectors.nso_connector_jsonrpc.report_downloader import (
    download_and_preprocess_report,
    get_report_downloader,
    preprocess_compliance_report
)
from agents.compliance.tools.connectors.nso_connector_rest import get_compliance_reports_list


# from exceptions import NSOCLIError

# Initialize Logger
logger = logging.getLogger("devnet.compliance.tools.nso")

# --- INITIALIZATION ---
# NSOCLIClient will auto-generate testbed from environment variables if no path is provided
# Required env vars: NSO_HOST, NSO_PORT, NSO_USERNAME, NSO_PASSWORD
_client = NSOCLIClient()  # Uses environment variables for connection settings
_manager = NSOComplianceManager(_client)

# =============================================================================
# LANGCHAIN TOOLS FOR NSO COMPLIANCE REPORTING
# =============================================================================

@tool
def configure_nso_compliance_report(
    report_name: str,
    device_check_all: bool = False,
    device_check_devices: Optional[List[str]] = None,
    device_check_device_groups: Optional[List[str]] = None,
    device_check_templates: Optional[List[str]] = None,
    service_check_all: bool = False,
    service_check_service_types: Optional[List[str]] = None,
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
    - device_check_device_groups=["dc-core", "wan-routers"]: Audit devices in specific device groups.
      Use 'list_nso_device_groups' tool first to discover available device groups.
    
    COMPLIANCE TEMPLATES:
    - device_check_templates=["ntp-standard", "acl-baseline"]: Check devices against 
      these Golden Config templates to find configuration drift
    
    SERVICE SELECTION (choose one or combine):
    - service_check_all=True: Verify all NSO service instances are in-sync
    - service_check_service_types=["/ncs:services/loopback:loopback"]: Check specific service types only
      Use 'list_nso_service_types' tool first to discover available service types.
    
    Args:
        report_name: Unique identifier for this report definition (e.g., "weekly-audit", "dc-core-check")
        device_check_all: True to include ALL devices. Mutually exclusive with device_check_devices/device_check_device_groups.
        device_check_devices: List of specific device names to audit. Mutually exclusive with device_check_all/device_check_device_groups.
        device_check_device_groups: List of NSO device group names to audit. Use 'list_nso_device_groups' to discover available groups. Mutually exclusive with device_check_all/device_check_devices.
        device_check_templates: List of compliance template names to validate devices against.
        service_check_all: True to verify all service instances are synchronized.
        service_check_service_types: List of service type paths to check (e.g., ["/ncs:services/loopback:loopback"]).
            Use 'list_nso_service_types' to discover available service types first.
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
            device_check_device_groups=device_check_device_groups,
            device_check_templates=device_check_templates,
            service_check_all=service_check_all,
            service_check_service_types=service_check_service_types,
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
    outformat: str = "html",
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
    - ALWAYS ask for the name of the report_name
    
    OUTPUT FORMATS:
    - text: Human-readable plain text (default, best for quick review)
    - html: Web-viewable report with formatting (best for sharing)
    - xml: DocBook XML format (best for automation/parsing)
    - sqlite: Database format (best for historical analysis)
    
    Args:
        report_name: Name of the existing report definition to execute (must exist in NSO)
        outformat: Output format - 'text', 'html', 'xml', or 'sqlite' (default: 'html')
        title: Optional descriptive title for this run (e.g., "Q1 2025 Audit", "Pre-Change Check")
    
    Returns:
        success: True if report executed successfully
        report_name: Name of the executed report. Proposed by user or by AI acccordingly.
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
    except NSOCLIError as e:
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
        - "Show me all compliance reports results" → list_nso_compliance_results()
        - "What audits have been run?" → list_nso_compliance_results()
    """
    logger.info("LLM Tool Call: list_nso_compliance_results")
    try:
        output = _manager.list_compliance_reports()
        return {"success": True, "data": output}
    except NSOCLIError as e:
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


@tool
def delete_nso_compliance_report(report_name: str) -> Dict[str, Any]:
    """
    Delete a compliance report DEFINITION from NSO.
    
    This tool removes a compliance report configuration from NSO. Use this when:
    - A report is no longer needed
    - You want to clean up test reports
    - You need to recreate a report with different settings
    
    ⚠️ WARNING: This is a DESTRUCTIVE operation that cannot be undone.
    The report definition will be permanently removed from NSO.
    
    NOTE: This does NOT delete historical report RESULTS (the executed audit data).
    To remove report results, use a separate cleanup tool.
    
    Args:
        report_name: Name of the compliance report definition to delete (e.g., "weekly-audit", "test-report")
    
    Returns:
        success: True if report was deleted successfully
        message: Status message confirming deletion
        report_name: Name of the deleted report
        nso_output: Raw NSO CLI output for debugging
    
    Example Usage:
        - "Delete the test-audit report" → report_name="test-audit"
        - "Remove the old IOS-XR compliance report" → report_name="IOS-XR"
    """
    logger.info(f"LLM Tool Call: delete_nso_compliance_report -> {report_name}")
    try:
        output = _manager.delete_compliance_report(report_name)
        return {
            "success": True,
            "message": f"Report '{report_name}' has been deleted from NSO.",
            "report_name": report_name,
            "nso_output": output
        }
    except Exception as e:
        return {"success": False, "error": str(e), "report_name": report_name}


@tool
def list_nso_compliance_report_definitions() -> Dict[str, Any]:
    """
    List all compliance report DEFINITIONS configured in NSO via RESTCONF API.
    
    This tool shows all the report configurations (WHAT to audit), NOT the historical
    execution results. Use this to see which reports are available to run.
    
    DIFFERENCE FROM list_nso_compliance_results:
    - list_nso_compliance_report_definitions: Shows CONFIGURED reports (the templates)
    - list_nso_compliance_results: Shows EXECUTED report results (historical audits)
    
    PURPOSE: Discover which compliance reports are configured in NSO, including:
    - Report names available for execution
    - Device checks configuration
    - Service checks configuration
    - Compliance templates assigned
    
    WHEN TO USE:
    - "What reports can I run?" → Use this tool
    - "Show me all configured compliance reports"
    - "List available report definitions"
    - Before running a report to verify it exists
    - Before deleting a report to confirm its name
    
    Returns:
        success: True if query was successful
        data: NSO output showing all report definitions
        reports: List of report names (if successful)
    
    Example Response:
        {
            "success": true,
            "data": { "tailf-ncs:report": [...] },
            "reports": ["weekly-audit", "dc-core-check"]
        }
    """
    logger.info("LLM Tool Call: list_nso_compliance_report_definitions (RESTCONF)")
    try:
        result = get_compliance_reports_list()
        
        if result.get("success"):
            # Extract report names for easier access
            reports = []
            data = result.get("data", {})
            if data and "tailf-ncs:report" in data:
                reports = [r.get("name") for r in data["tailf-ncs:report"] if r.get("name")]
            
            return {
                "success": True,
                "data": data,
                "reports": reports,
                "count": len(reports)
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Error listing compliance report definitions: {e}")
        return {"success": False, "error": str(e)}


# OLD CLI-BASED IMPLEMENTATION - COMMENTED OUT
# @tool
# def list_nso_compliance_report_definitions_cli() -> Dict[str, Any]:
#     """
#     List all compliance report DEFINITIONS configured in NSO (CLI version).
#     
#     This tool shows all the report configurations (WHAT to audit), NOT the historical
#     execution results. Use this to see which reports are available to run.
#     
#     DIFFERENCE FROM list_nso_compliance_results:
#     - list_nso_compliance_report_definitions: Shows CONFIGURED reports (the templates)
#     - list_nso_compliance_results: Shows EXECUTED report results (historical audits)
#     
#     PURPOSE: Discover which compliance reports are configured in NSO, including:
#     - Report names available for execution
#     - Running status (whether a report is currently executing)
#     
#     WHEN TO USE:
#     - "What reports can I run?" → Use this tool
#     - "Show me all configured compliance reports"
#     - "List available report definitions"
#     - Before running a report to verify it exists
#     - Before deleting a report to confirm its name
#     
#     Returns:
#         success: True if query was successful
#         data: NSO output showing all report definitions with their status
#     
#     Example Output:
#         compliance reports report CUSTOM_COMPLIANCE_PYTHON
#          status running false
#         compliance reports report weekly-audit
#          status running false
#     """
#     logger.info("LLM Tool Call: list_nso_compliance_report_definitions")
#     try:
#         output = _manager.list_compliance_report_definitions()
#         return {"success": True, "data": output}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


@tool
def remove_nso_compliance_report_results(report_id: str) -> Dict[str, Any]:
    """
    Remove specific compliance report RESULTS from NSO history.
    
    This tool deletes executed report results (historical audit data), NOT the report
    definitions. Use this to clean up old audit results.
    
    DIFFERENCE FROM delete_nso_compliance_report:
    - remove_nso_compliance_report_results: Deletes EXECUTED audit results (history)
    - delete_nso_compliance_report: Deletes the report DEFINITION (configuration)
    
    ⚠️ WARNING: This is a DESTRUCTIVE operation that cannot be undone. ALWAYS ask for confirmation from user
    The report results will be permanently removed from NSO.
    
    Args:
        report_id: The ID of the report result to remove. This is typically a timestamp
                   in ISO format (e.g., "2026-01-31T15:07:26.424284+00:00") or a numeric
                   ID. You can also specify a range like "1..5" to remove multiple results.
    
    WORKFLOW:
    1. First use 'list_nso_compliance_results' to see all report results with their IDs
    2. Identify the report_id you want to remove
    3. Get user APPROVAL and inform it is a destructive operation
    4. Use this tool to remove it
    
    Returns:
        success: True if report results were removed successfully
        message: Status message confirming removal
        report_id: ID of the removed report results
        nso_output: Raw NSO CLI output for debugging
    
    Example Usage:
        - "Remove the report result from January 31st" → report_id="2026-01-31T15:07:26.424284+00:00"
        - "Delete report results 1 through 5" → report_id="1..5"
        - "Clean up old audit result ID 42" → report_id="42"
    """
    logger.info(f"LLM Tool Call: remove_nso_compliance_report_results -> {report_id}")
    try:
        output = _manager.remove_compliance_report_results(report_id)
        return {
            "success": True,
            "message": f"Report results '{report_id}' have been removed from NSO.",
            "report_id": report_id,
            "nso_output": output
        }
    except Exception as e:
        return {"success": False, "error": str(e), "report_id": report_id}


@tool
def list_nso_service_types() -> Dict[str, Any]:
    """
    List all available service types configured in NSO.
    
    This tool retrieves the list of NSO service types that can be used when configuring
    compliance reports with service checks. Use this to discover which services are
    available in your NSO instance.
    
    PURPOSE: Discover available service types for use in compliance report configuration.
    The returned service names can be used directly in the 'service_check_service_types'
    parameter of 'configure_nso_compliance_report'.
    
    WHEN TO USE:
    - Before configuring a compliance report with service checks
    - "What services are available in NSO?"
    - "List all service types I can audit"
    - "Show me the services for compliance checking"
    
    Returns:
        success: True if query was successful
        service_types: List of service type names (e.g., ['loopback-demo:loopback-demo'])
        count: Number of service types found
    
    Example Output:
        {
            "success": True,
            "service_types": [
                "loopback-demo:loopback-demo",
                "loopback-tunisie:loopback-tunisie"
            ],
            "count": 2
        }
    
    Example Usage in Workflow:
        1. Call list_nso_service_types() to see available services
        2. Use the service name in configure_nso_compliance_report:
           configure_nso_compliance_report(
               report_name="my-service-audit",
               service_check_service_types=["loopback-tunisie:loopback-tunisie"]
           )
    """
    logger.info("LLM Tool Call: list_nso_service_types")
    try:
        service_types = _manager.list_service_types()
        return {
            "success": True,
            "service_types": service_types,
            "count": len(service_types)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def list_nso_compliance_templates() -> Dict[str, Any]:
    """
    List all available compliance templates configured in NSO.
    
    This tool retrieves the list of compliance templates (Golden Configs) that can be used
    when configuring compliance reports. Use this to discover which templates are available
    for device compliance checking.
    
    PURPOSE: Discover available compliance templates for use in compliance report configuration.
    The returned template names can be used directly in the 'device_check_templates'
    parameter of 'configure_nso_compliance_report'.
    
    WHEN TO USE:
    - Before configuring a compliance report with template checks
    - "What compliance templates are available?"
    - "List all Golden Config templates"
    - "Show me the templates I can use for compliance checking"
    
    Returns:
        success: True if query was successful
        templates: List of compliance template names (e.g., ['ntp_dns', 'acl-baseline'])
        count: Number of templates found
    
    Example Output:
        {
            "success": True,
            "templates": ["ntp_dns", "acl-baseline"],
            "count": 2
        }
    
    Example Usage in Workflow:
        1. Call list_nso_compliance_templates() to see available templates
        2. Use the template name in configure_nso_compliance_report:
           configure_nso_compliance_report(
               report_name="my-device-audit",
               device_check_all=True,
               device_check_templates=["ntp_dns"]
           )
    """
    logger.info("LLM Tool Call: list_nso_compliance_templates")
    try:
        templates = _manager.list_compliance_templates()
        return {
            "success": True,
            "templates": templates,
            "count": len(templates)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def show_nso_compliance_template(template_name: str) -> Dict[str, Any]:
    """
    Show the detailed configuration of a specific compliance template (Golden Config).
    
    This tool retrieves the full configuration details of a compliance template,
    including its expressions, device settings, and matching criteria.
    
    PURPOSE: View the contents of a Golden Config template to understand:
    - What configuration items are being checked
    - What expressions/patterns are defined
    - How the template is structured
    
    WHEN TO USE:
    - "Show me the ntp_dns template configuration"
    - "What does the acl-baseline template check for?"
    - "Display the contents of template X"
    - Before modifying or using a template, to understand its structure
    
    WORKFLOW:
    1. First use 'list_nso_compliance_templates()' to see available templates
    2. Then use this tool to view details of a specific template
    
    Args:
        template_name: Name of the compliance template to show (e.g., "ntp_dns")
    
    Returns:
        success: True if query was successful
        template_name: Name of the template queried
        configuration: Full NSO configuration output for the template
    
    Example Usage:
        - "Show me the ntp_dns template" → template_name="ntp_dns"
    """
    logger.info(f"LLM Tool Call: show_nso_compliance_template -> {template_name}")
    try:
        output = _manager.show_compliance_templates(template_name=template_name)
        return {
            "success": True,
            "template_name": template_name,
            "configuration": output
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def show_nso_compliance_report_config(report_name: Optional[str] = None) -> Dict[str, Any]:
    """
    View the configuration of a compliance report definition in NSO.
    
    Use this tool to inspect HOW a compliance report is configured - what devices,
    device groups, templates, and services are included in the report definition.
    
    This shows the DEFINITION (configuration), not the execution results.
    For executed report results, use 'list_nso_compliance_results' instead.
    
    WHEN TO USE:
    - "Show me how the weekly-audit report is configured"
    - "What devices does the dc-compliance report check?"
    - "Display the configuration of report X"
    - Before modifying a report, to understand its current settings
    - To verify a report was configured correctly after creation
    
    Args:
        report_name: Name of a specific report to view. If None, shows ALL report configurations.
    
    Returns:
        success: True if query was successful
        report_name: Name of the report queried (or "all" if viewing all)
        configuration: NSO configuration output showing the report definition
    
    Example Usage:
        - "Show config for weekly-audit" → report_name="weekly-audit"
        - "Show all report configurations" → report_name=None
    """
    logger.info(f"LLM Tool Call: show_nso_compliance_report_config -> {report_name or 'all'}")
    try:
        output = _manager.show_compliance_report_config(report_name=report_name)
        return {
            "success": True,
            "report_name": report_name or "all",
            "configuration": output
        }
    except Exception as e:
        return {"success": False, "error": str(e), "report_name": report_name}


@tool
def list_nso_device_groups() -> Dict[str, Any]:
    """
    Discovery Tool: List all available device groups in NSO.
    
    Use this tool BEFORE configuring compliance reports with device_check_device_groups
    to discover which device groups are available in the NSO system.
    
    Device groups in NSO are logical groupings of devices (e.g., "dc-core", "wan-routers",
    "branch-switches") that can be used to scope compliance checks.
    
    WHEN TO USE:
    - Before creating a compliance report that targets device groups
    - "What device groups are available?"
    - "Show me the device groups in NSO"
    - "List all device groups"
    
    Returns:
        success: True if query was successful
        device_groups: List of device group names available in NSO
        count: Number of device groups found
    
    Example Usage:
        1. Call list_nso_device_groups() to see available groups
        2. Use returned group names in configure_nso_compliance_report(device_check_device_groups=[...])
    """
    logger.info("LLM Tool Call: list_nso_device_groups")
    try:
        device_groups = _manager.list_device_groups()
        return {
            "success": True,
            "device_groups": device_groups,
            "count": len(device_groups)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def download_nso_compliance_report(report_url_or_id: str) -> Dict[str, Any]:
    """
    Download and preprocess a compliance report from NSO for analysis.
    
    This tool downloads a compliance report file from NSO using JSON-RPC authentication,
    saves it to a temporary file, and returns the file path for the analyzer to process.
    
    IMPORTANT: The report content is NOT returned directly to save token usage.
    Instead, the file path is returned and the analyzer node will read from the file.
    
    Use this tool when:
    - User wants to analyze a specific report by ID
    - After running a compliance report, to fetch the full report content
    - "Analyze report ID 5"
    - "Download the compliance report from <URL>"
    
    Args:
        report_url_or_id: Either:
            - Full URL: "http://localhost:8080/compliance-reports/report_2025-10-09T13:48:32.html"
            - Report ID: "5" or "2025-10-09T13:48:32.663282+00:00.html"
    
    Returns:
        success: True if download was successful
        file_path: Path to the temp file containing preprocessed report (for analyzer node)
        report_id: The report identifier used
        size_chars: Size of preprocessed content in characters
        preview: First 500 characters of the report as a preview
    
    Example Usage:
        - "Download report 5 for analysis" → report_url_or_id="5"
        - "Analyze the compliance report at http://..." → report_url_or_id="http://..."
    """
    logger.info(f"LLM Tool Call: download_nso_compliance_report -> {report_url_or_id}")
    try:
        filepath, content = download_and_preprocess_report(report_url_or_id)
        
        if filepath and content:
            # Save content to a temp file to avoid token overload
            temp_dir = tempfile.gettempdir()
            # Sanitize report_id for filename
            safe_id = str(report_url_or_id).replace("/", "_").replace(":", "_").replace(".", "_")[:50]
            temp_file_path = os.path.join(temp_dir, f"compliance_report_{safe_id}.txt")
            
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Report saved to temp file: {temp_file_path} ({len(content)} chars)")
            
            # Return metadata only, not the full content
            return {
                "success": True,
                "file_path": temp_file_path,
                "report_id": report_url_or_id,
                "report_url": report_url_or_id if report_url_or_id.startswith("http") else None,
                "size_chars": len(content),
                "preview": content[:500] + "..." if len(content) > 500 else content,
                "message": f"Report downloaded and saved to {temp_file_path}. Ready for analysis by analyzer node."
            }
        else:
            return {
                "success": False,
                "error": "Failed to download report. Check if the report ID/URL is valid and NSO is accessible.",
                "report_id": report_url_or_id
            }
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        return {
            "success": False,
            "error": str(e),
            "report_id": report_url_or_id
        }


# Export the list of tools for LangChain Agent initialization
# These tools follow a typical compliance workflow:
# 1. configure_nso_compliance_report - Define what to audit
# 2. run_nso_compliance_report - Execute the audit
# 3. list_nso_compliance_results - View audit history (executed reports)
# 4. list_nso_compliance_report_definitions - View configured reports (what can be run)
# 5. create_nso_compliance_template - Create Golden Config templates
# 6. list_nso_compliance_templates - List available compliance templates
# 7. show_nso_compliance_template - Show details of a specific template
# 8. delete_nso_compliance_report - Remove report definitions
# 9. remove_nso_compliance_report_results - Remove executed report results (history)
# 10. list_nso_service_types - Discover available service types
# 11. list_nso_device_groups - Discover available device groups
# 12. show_nso_compliance_report_config - View report definition configuration
# 13. download_nso_compliance_report - Download and preprocess report for analysis
nso_compliance_toolset = [
    configure_nso_compliance_report,
    run_nso_compliance_report,
    list_nso_compliance_results,
    # list_nso_compliance_report_definitions, old ersion with cli 
    # create_nso_compliance_template, to be review 
    list_nso_compliance_templates,
    show_nso_compliance_template,
    show_nso_compliance_report_config,
    delete_nso_compliance_report,
    remove_nso_compliance_report_results,
    list_nso_service_types,
    list_nso_device_groups,
    download_nso_compliance_report,
]