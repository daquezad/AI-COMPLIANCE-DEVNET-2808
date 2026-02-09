import logging
from typing import List, Optional
from agents.compliance.tools.connectors.nso_connector_cli.nso_client_cli import NSOCLIClient


# Initialize the requested logger
logger = logging.getLogger("devnet.compliance.tools.nso")

class NSOComplianceManager:
    """
    Comprehensive manager for NSO Compliance Reporting and Templates.
    Methods are structured to be used as individual tools by an LLM agent.
    """

    def __init__(self, client: NSOCLIClient):
        self.client = client

    # =========================================================================
    # 1. COMPLIANCE REPORT CONFIGURATION (CRUD)
    # =========================================================================

    def configure_compliance_report(
        self,
        report_name: str,
        device_check_all: bool = False,
        device_check_devices: Optional[List[str]] = None,
        device_check_device_groups: Optional[List[str]] = None,
        device_check_select_xpath: Optional[str] = None,
        device_check_templates: Optional[List[str]] = None,
        device_current_out_of_sync: bool = True,
        device_historic_changes: bool = True,
        service_check_all: bool = False,
        service_check_services: Optional[List[str]] = None,
        service_check_service_types: Optional[List[str]] = None,
        service_check_select_xpath: Optional[str] = None,
        service_current_out_of_sync: bool = True,
        service_historic_changes: bool = True,
        dry_run: bool = False,
    ) -> str:
        """
        Configures or updates a compliance report definition in NSO.
        
        Args:
            report_name: Name of the compliance report
            device_check_all: Check all devices
            device_check_devices: List of specific devices to check
            device_check_device_groups: List of device groups to check
            device_check_select_xpath: XPath to select devices
            device_check_templates: List of compliance templates to check against
            device_current_out_of_sync: Check current sync status (default: True)
            device_historic_changes: Include historic changes (default: True)
            service_check_all: Check all services
            service_check_services: List of specific services to check
            service_check_service_types: List of service types to check
            service_check_select_xpath: XPath to select services
            service_current_out_of_sync: Check service sync status (default: True)
            service_historic_changes: Include service historic changes (default: True)
            dry_run: If True, preview changes without committing (default: False)
        
        Returns:
            NSO CLI output showing the configuration result or dry-run preview
        """
        base = f"compliance reports report {report_name}"
        cmds = []

        # Device Selection Logic
        if device_check_all:
            cmds.append(f"set {base} device-check all-devices")
        elif device_check_device_groups:
            for group in device_check_device_groups:
                cmds.append(f"set {base} device-check device-group {group}")
        elif device_check_devices:
            for dev in device_check_devices:
                cmds.append(f"set {base} device-check device {dev}")
        elif device_check_select_xpath:
            cmds.append(f"set {base} device-check select-devices {device_check_select_xpath}")

        # Device Options
        if any([device_check_all, device_check_devices, device_check_device_groups, device_check_select_xpath]):
            if not device_current_out_of_sync:
                cmds.append(f"set {base} device-check current-out-of-sync false")
            if not device_historic_changes:
                cmds.append(f"set {base} device-check historic-changes false")

        if device_check_templates:
            for tmpl in device_check_templates:
                cmds.append(f"set {base} device-check template {tmpl}")

        # Service Selection Logic
        if service_check_all:
            cmds.append(f"set {base} service-check all-services")
        if service_check_service_types:
            for stype in service_check_service_types:
                cmds.append(f"set {base} service-check service-type {stype}")
        # if service_check_services: #todo to be verified
        #     for svc in service_check_services:
        #         cmds.append(f"set {base} service-check service {svc}")
        # if service_check_select_xpath: #todo to be verified
        #     cmds.append(f"set {base} service-check select-services {service_check_select_xpath}")

        # Service Options
        if any([service_check_all, service_check_services, service_check_service_types, service_check_select_xpath]):
            if not service_current_out_of_sync:
                cmds.append(f"set {base} service-check current-out-of-sync false")
            if not service_historic_changes:
                cmds.append(f"set {base} service-check historic-changes false")

        # Validate that at least one check path is configured
        has_device_check = any([device_check_all, device_check_devices, device_check_device_groups, device_check_select_xpath])
        has_service_check = any([service_check_all, service_check_services, service_check_service_types, service_check_select_xpath])
        
        if not has_device_check and not has_service_check:
            raise ValueError(
                f"Report '{report_name}' has no targets configured. "
                "You must specify at least one of: device_check_all, device_check_devices, "
                "device_check_device_groups, service_check_all, or service_check_service_types. "
                "NSO will reject reports with 'invalid path' if no check targets are defined."
            )

        logger.info(f"Applying configuration for report definition: {report_name} (dry_run={dry_run})")
        return self.client.execute_config(cmds, dry_run=dry_run)

    def show_compliance_report_config(self, report_name: Optional[str] = None) -> str:
        """Shows the configuration of a specific report or all reports."""
        cmd = "show configuration compliance reports"
        if report_name:
            cmd += f" report {report_name}"
        return self.client.execute_read(cmd)

    def delete_compliance_report(self, report_name: str) -> str:
        """Deletes a compliance report definition."""
        logger.warning(f"Deleting compliance report definition: {report_name}")
        return self.client.execute_config([f"delete compliance reports report {report_name}"])

    def list_compliance_report_definitions(self) -> str:
        """
        Lists all compliance report DEFINITIONS (not results).
        
        Shows the configured reports with their status (running true/false).
        This is different from list_compliance_reports() which shows executed report results.
        
        Returns:
            NSO CLI output showing all report definitions and their running status.
            Example output:
                compliance reports report CUSTOM_COMPLIANCE_PYTHON
                 status running false
                compliance reports report weekly-audit
                 status running false
        """
        logger.info("Fetching all compliance report definitions.")
        return self.client.execute_read("show compliance reports")

    # =========================================================================
    # 2. EXECUTION AND RESULTS
    # =========================================================================

    def _validate_report_has_paths(self, report_name: str) -> None:
        """
        Validates that a report definition has at least one device-check or service-check path.
        Raises ValueError if the report is misconfigured.
        """
        try:
            config = self.show_compliance_report_config(report_name)
            
            # Check if report exists
            if "No entries found" in config or not config.strip():
                raise ValueError(
                    f"Report '{report_name}' does not exist. "
                    "Use 'configure_nso_compliance_report' to create it first with device or service targets."
                )
            
            # Check for device-check or service-check configuration
            has_device_check = "device-check" in config
            has_service_check = "service-check" in config
            
            if not has_device_check and not has_service_check:
                raise ValueError(
                    f"Report '{report_name}' has no targets configured (missing device-check or service-check). "
                    "NSO returns 'invalid path' for reports without targets. "
                    "Please reconfigure the report with 'configure_nso_compliance_report' and specify "
                    "device_check_all=True, device_check_devices, device_check_device_groups, "
                    "service_check_all=True, or service_check_service_types."
                )
        except Exception as e:
            if "ValueError" in str(type(e)):
                raise
            logger.warning(f"Could not validate report '{report_name}': {e}")
            # Continue anyway - let NSO report the actual error

    def run_compliance_report(
        self,
        report_name: str,
        title: Optional[str] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        outformat: str = "html",
    ) -> str:
        """Executes a compliance report and returns the result metadata."""
        # Validate report has proper configuration before running
        self._validate_report_has_paths(report_name)
        
        cmd_parts = [f"request compliance reports report {report_name} run"]
        if title: cmd_parts.append(f'title "{title}"')
        if from_time: cmd_parts.append(f"from {from_time}")
        if to_time: cmd_parts.append(f"to {to_time}")
        cmd_parts.append(f"outformat {outformat}")
        
        logger.info(f"Executing compliance report run: {report_name}")
        return self.client.execute_read(" ".join(cmd_parts))

    def list_compliance_reports(self) -> str:
        """Lists all historical compliance report results (IDs, status, URLs)."""
        logger.info("Fetching all compliance report results.")
        return self.client.execute_read("show compliance report-results")

    def remove_compliance_report_results(self, report_ids: str) -> str:
        """
        Removes specific report results from history.
        Args:
            report_ids: Single ID (e.g. "1") or range (e.g. "1..5").
        """
        logger.info(f"Removing report results: {report_ids}")
        return self.client.execute_read(f"request compliance report-results report {report_ids} remove")

    # =========================================================================
    # 3. COMPLIANCE TEMPLATES to ve
    # =========================================================================

    def create_compliance_template(
        self,
        template_name: str,
        device_template: Optional[str] = None,
        paths: Optional[List[str]] = None,
        match_rate: Optional[int] = None,
        exclude_service_config: bool = False,
        collapse_list_keys: Optional[str] = None,
    ) -> str:
        """Creates a compliance template from existing device config or templates."""
        cmd_parts = [f"compliance create-template name {template_name}"]
        if device_template:
            cmd_parts.append(f"device-template {device_template}")
        if paths:
            cmd_parts.append(f"path [ {' '.join(paths)} ]")
        if match_rate is not None:
            cmd_parts.append(f"match-rate {match_rate}")
        if exclude_service_config:
            cmd_parts.append("exclude-service-config")
        if collapse_list_keys:
            cmd_parts.append(f"collapse-list-keys {collapse_list_keys}")

        logger.info(f"Creating compliance template: {template_name}")
        return self.client.execute_config([" ".join(cmd_parts)])

    # def check_compliance_template(self, template_name: str, devices: List[str]) -> str:
    #     """Checks a template against specific devices in real-time (Testing)."""
    #     device_list = " ".join(devices)
    #     cmds = [
    #         f"edit compliance template {template_name}",
    #         f"request check device [ {device_list} ]",
    #         "top"
    #     ]
    #     logger.info(f"Checking template {template_name} against devices: {devices}")
    #     return self.client.execute_config(cmds)

    def show_compliance_templates(self, template_name: Optional[str] = None) -> str:
        """Shows configuration for one or all compliance templates."""
        cmd = "show running-config compliance template"
        if template_name:
            cmd += f" {template_name}"
        return self.client.execute_read(cmd)

    def list_compliance_templates(self) -> list[str]:
        """
        Lists all available compliance template names in NSO.
        
        Retrieves the compliance templates and parses them to return only the template names
        (without the 'compliance template ' prefix).
        
        Returns:
            List of compliance template names (e.g., ['ntp_dns', 'acl-baseline'])
        """
        logger.info("Fetching all compliance template names from NSO.")
        raw_output = self.client.execute_read("show compliance template")
        
        # Parse the output to extract just the template names
        # Input format: "compliance template ntp_dns"
        # Output format: "ntp_dns"
        template_names = []
        for line in raw_output.strip().split('\n'):
            line = line.strip()
            if line.startswith('compliance template '):
                # Remove the prefix to get just the template name
                template_name = line.replace('compliance template ', '')
                template_names.append(template_name)
        
        return template_names

    def delete_compliance_template(self, template_name: str) -> str:
        """Deletes a compliance template."""
        logger.warning(f"Deleting compliance template: {template_name}")
        return self.client.execute_config([f"delete compliance template {template_name}"])

    # =========================================================================
    # 4. SERVICE 
    # =========================================================================

    def list_service_types(self) -> list[str]:
        """
        Lists all available service types in NSO.
        
        Retrieves the service types and parses them to return only the service names
        (without the 'services service-type /ncs:services/' prefix).
        
        Returns:
            List of service type names (e.g., ['loopback-demo:loopback-demo', 'loopback-tunisie:loopback-tunisie'])
        """
        logger.info("Fetching all service types from NSO.")
        raw_output = self.client.execute_read("show services service-type")
        
        # Parse the output to extract just the service names
        # Input format: "services service-type /ncs:services/loopback-demo:loopback-demo"
        # Output format: "loopback-demo:loopback-demo"
        service_types = []
        for line in raw_output.strip().split('\n'):
            line = line.strip()
            if line.startswith('services service-type'):
                # Remove the prefix to get just the service name
                service_name = line.replace('services service-type ', '')
                service_types.append(service_name)
        
        return service_types

    def list_device_groups(self) -> list[str]:
        """
        Lists all available device groups in NSO.
        
        Retrieves the device groups and parses them to return only the group names.
        
        Returns:
            List of device group names (e.g., ['dc-core', 'wan-routers', 'all-devices'])
        """
        logger.info("Fetching all device groups from NSO.")
        raw_output = self.client.execute_read("show devices device-group | tab | de-select member")
        
        # Parse the output to extract just the device group names
        # The output is a table with 'NAME' column header
        device_groups = []
        lines = raw_output.strip().split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines, header lines, and separator lines
            if not line or line.startswith('NAME') or line.startswith('-'):
                continue
            # The group name is the first (and only) column
            device_groups.append(line)
        
        return device_groups