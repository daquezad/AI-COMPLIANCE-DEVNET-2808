"""
Consolidated tools list for the Compliance Agent.
"""
from agents.compliance.tools.nso_tools import (
    trigger_nso_compliance_report,
    get_nso_report_details,
    list_nso_compliance_reports,
    schedule_nso_compliance_report,
    nso_tools
)
from agents.compliance.tools.cwm_tools import (
    execute_cwm_remediation_workflow,
    get_cwm_job_status,
    cwm_tools
)


# Combined tools list for the agent
tools = nso_tools + cwm_tools