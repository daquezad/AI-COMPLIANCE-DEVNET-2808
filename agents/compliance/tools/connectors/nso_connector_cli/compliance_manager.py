import logging
from typing import List, Optional
from agents.compliance.tools.connectors.nso_connector_cli.nso_client_cli import NSOClient


# Initialize the requested logger
logger = logging.getLogger("devnet.compliance.tools.nso")

class NSOComplianceManager:
    """
    Comprehensive manager for NSO Compliance Reporting and Templates.
    Methods are structured to be used as individual tools by an LLM agent.
    """

    def __init__(self, client: NSOClient):
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
    ) -> str:
        """Configures or updates a compliance report definition in NSO."""
        base = f"compliance reports report {report_name}"
        cmds = []

        # Device Selection Logic
        if device_check_all:
            cmds.append(f"set {base} device-check all-devices")
        elif device_check_devices:
            for dev in device_check_devices:
                cmds.append(f"set {base} device-check device {dev}")
        elif device_check_device_groups:
            for group in device_check_device_groups:
                cmds.append(f"set {base} device-check device-group {group}")
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
        if service_check_services:
            for svc in service_check_services:
                cmds.append(f"set {base} service-check service {svc}")
        if service_check_service_types:
            for stype in service_check_service_types:
                cmds.append(f"set {base} service-check service-type {stype}")
        if service_check_select_xpath:
            cmds.append(f"set {base} service-check select-services {service_check_select_xpath}")

        # Service Options
        if any([service_check_all, service_check_services, service_check_service_types, service_check_select_xpath]):
            if not service_current_out_of_sync:
                cmds.append(f"set {base} service-check current-out-of-sync false")
            if not service_historic_changes:
                cmds.append(f"set {base} service-check historic-changes false")

        logger.info(f"Applying configuration for report definition: {report_name}")
        return self.client.execute_config(cmds)

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

    # =========================================================================
    # 2. EXECUTION AND RESULTS
    # =========================================================================

    def run_compliance_report(
        self,
        report_name: str,
        title: Optional[str] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        outformat: str = "text",
    ) -> str:
        """Executes a compliance report and returns the result metadata."""
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
    # 3. COMPLIANCE TEMPLATES
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

    def check_compliance_template(self, template_name: str, devices: List[str]) -> str:
        """Checks a template against specific devices in real-time (Testing)."""
        device_list = " ".join(devices)
        cmds = [
            f"edit compliance template {template_name}",
            f"request check device [ {device_list} ]",
            "top"
        ]
        logger.info(f"Checking template {template_name} against devices: {devices}")
        return self.client.execute_config(cmds)

    def show_compliance_templates(self, template_name: Optional[str] = None) -> str:
        """Shows configuration for one or all compliance templates."""
        cmd = "show configuration compliance template"
        if template_name:
            cmd += f" {template_name}"
        return self.client.execute_read(cmd)

    def delete_compliance_template(self, template_name: str) -> str:
        """Deletes a compliance template."""
        logger.warning(f"Deleting compliance template: {template_name}")
        return self.client.execute_config([f"delete compliance template {template_name}"])