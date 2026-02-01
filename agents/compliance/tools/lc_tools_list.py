"""
Consolidated tools list for the Compliance Agent.
"""
from agents.compliance.tools.nso_lc_tools import nso_tools
from agents.compliance.tools.cwm_lc_tools import cwm_tools
from agents.compliance.tools.compliance_lc_tools import nso_compliance_toolset
from agents.compliance.tools.remediation_lc_tools import remediation_tools

# Combined tools list for the agent
tools = nso_tools + cwm_tools + nso_compliance_toolset + remediation_tools