"""
NSO (Network Services Orchestrator) Tools for compliance report management.
These tools interact with NSO to trigger and retrieve compliance reports.
"""
import json
import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("devnet.compliance.tools.nso")

# Mock data for demonstration - replace with actual NSO API calls
MOCK_REPORTS = {
    "RPT-2026-001": {
        "id": "RPT-2026-001",
        "name": "Weekly Compliance Audit",
        "created_at": "2026-01-31T08:00:00Z",
        "status": "completed",
        "data": {
            "total_devices": 12,
            "compliant": 8,
            "non_compliant": 4,
            "devices": [
                {
                    "name": "Core-R01",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "OSPF_AUTH_REQUIRED", "severity": "critical", "message": "OSPF authentication not configured"},
                        {"rule": "NTP_SYNC", "severity": "medium", "message": "NTP not synchronized"}
                    ]
                },
                {
                    "name": "Edge-S02",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "CONFIG_SYNC", "severity": "high", "message": "Device out-of-sync with NSO"}
                    ]
                },
                {
                    "name": "Dist-R03",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "ACL_STANDARD", "severity": "critical", "message": "Missing standard ACL on management interface"},
                        {"rule": "SNMP_V3", "severity": "medium", "message": "SNMP v3 not enabled"}
                    ]
                },
                {
                    "name": "Access-S04",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "VLAN_NAMING", "severity": "low", "message": "VLAN naming convention not followed"}
                    ]
                },
                {"name": "Core-R02", "status": "compliant", "violations": []},
                {"name": "Edge-S01", "status": "compliant", "violations": []},
                {"name": "Dist-R04", "status": "compliant", "violations": []},
                {"name": "Access-S01", "status": "compliant", "violations": []},
                {"name": "Access-S02", "status": "compliant", "violations": []},
                {"name": "Access-S03", "status": "compliant", "violations": []},
                {"name": "WAN-R01", "status": "compliant", "violations": []},
                {"name": "WAN-R02", "status": "compliant", "violations": []}
            ]
        }
    },
    "RPT-2026-002": {
        "id": "RPT-2026-002",
        "name": "Security Baseline Check",
        "created_at": "2026-01-30T14:30:00Z",
        "status": "completed",
        "data": {
            "total_devices": 8,
            "compliant": 5,
            "non_compliant": 3,
            "devices": [
                {
                    "name": "FW-01",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "FIREWALL_RULES_AUDIT", "severity": "critical", "message": "Outdated firewall rules detected"},
                        {"rule": "IPS_SIGNATURES", "severity": "high", "message": "IPS signatures need update"}
                    ]
                },
                {
                    "name": "VPN-GW-01",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "IPSEC_POLICY", "severity": "critical", "message": "Weak IPSec encryption algorithm in use"}
                    ]
                },
                {
                    "name": "DMZ-SW-01",
                    "status": "non-compliant",
                    "violations": [
                        {"rule": "PORT_SECURITY", "severity": "high", "message": "Port security not enabled on access ports"}
                    ]
                },
                {"name": "FW-02", "status": "compliant", "violations": []},
                {"name": "VPN-GW-02", "status": "compliant", "violations": []},
                {"name": "DMZ-SW-02", "status": "compliant", "violations": []},
                {"name": "Core-FW-01", "status": "compliant", "violations": []},
                {"name": "Core-FW-02", "status": "compliant", "violations": []}
            ]
        }
    }
}


@tool
def trigger_nso_compliance_report(report_type: str = "weekly_audit") -> dict:
    """
    Triggers a new NSO compliance report and returns the report ID.
    
    Args:
        report_type: Type of compliance report to generate. Options: 'weekly_audit', 'security_baseline', 'full_audit'
    
    Returns:
        Dictionary containing the report_id and status of the triggered report.
    """
    logger.info(f"Triggering NSO compliance report: {report_type}")
    
    # Mock implementation - in production, this would call NSO API
    report_mapping = {
        "weekly_audit": "RPT-2026-001",
        "security_baseline": "RPT-2026-002",
        "full_audit": "RPT-2026-001"
    }
    
    report_id = report_mapping.get(report_type, "RPT-2026-001")
    
    return {
        "success": True,
        "report_id": report_id,
        "message": f"Compliance report '{report_type}' triggered successfully. Report ID: {report_id}",
        "estimated_completion": "2026-01-31T08:05:00Z"
    }


@tool
def get_nso_report_details(report_id: str) -> dict:
    """
    Retrieves the detailed content of an NSO compliance report by its ID.
    
    Args:
        report_id: The unique identifier of the compliance report (e.g., 'RPT-2026-001')
    
    Returns:
        Dictionary containing the full compliance report data including device statuses and violations.
    """
    logger.info(f"Fetching NSO report details for: {report_id}")
    
    if report_id in MOCK_REPORTS:
        return {
            "success": True,
            "report": MOCK_REPORTS[report_id]
        }
    else:
        return {
            "success": False,
            "error": f"Report '{report_id}' not found",
            "available_reports": list(MOCK_REPORTS.keys())
        }


@tool
def list_nso_compliance_reports() -> dict:
    """
    Lists all available NSO compliance reports.
    
    Returns:
        Dictionary containing a list of available reports with their IDs, names, and statuses.
    """
    logger.info("Listing all NSO compliance reports")
    
    reports = []
    for report_id, report_data in MOCK_REPORTS.items():
        reports.append({
            "id": report_id,
            "name": report_data["name"],
            "created_at": report_data["created_at"],
            "status": report_data["status"]
        })
    
    return {
        "success": True,
        "total_reports": len(reports),
        "reports": reports
    }


@tool
def schedule_nso_compliance_report(
    report_type: str,
    schedule_type: str,
    schedule_value: str,
    webex_room_id: str,
    notify_email: str = ""
) -> dict:
    """
    Schedules an NSO compliance report for future execution. Results will be delivered via Webex notification only.
    This tool does NOT return report data - it only schedules the report generation.
    
    Args:
        report_type: Type of compliance report. Options: 'weekly_audit', 'security_baseline', 'full_audit'
        schedule_type: Type of schedule - 'once' for one-time, 'periodic' for recurring
        schedule_value: ISO-8601 timestamp for 'once' (e.g., '2026-02-01T08:00:00Z'), or cron expression for 'periodic' (e.g., '0 8 * * MON' for every Monday at 8am)
        webex_room_id: The Webex room/space ID where the report notification will be sent
        notify_email: Optional email address for additional notification
    
    Returns:
        Dictionary containing the schedule ID and confirmation. Note: Report results will be sent to Webex only.
    """
    logger.info(f"Scheduling NSO compliance report: {report_type} with schedule: {schedule_type}")
    
    # Generate a mock schedule ID
    import hashlib
    schedule_id = f"SCHED-RPT-{hashlib.md5(f'{report_type}{schedule_value}'.encode()).hexdigest()[:8].upper()}"
    
    # Determine next run time based on schedule
    if schedule_type == "once":
        next_run = schedule_value
        recurrence = "One-time"
    elif schedule_type == "periodic":
        # Mock: calculate next run from cron (simplified)
        next_run = "2026-02-03T08:00:00Z"  # Mock next Monday
        recurrence = f"Recurring ({schedule_value})"
    else:
        return {
            "success": False,
            "error": f"Invalid schedule_type: {schedule_type}. Must be 'once' or 'periodic'"
        }
    
    return {
        "success": True,
        "schedule_id": schedule_id,
        "report_type": report_type,
        "schedule_type": schedule_type,
        "schedule_value": schedule_value,
        "next_run": next_run,
        "recurrence": recurrence,
        "notification": {
            "webex_room_id": webex_room_id,
            "email": notify_email if notify_email else None
        },
        "message": f"📅 Compliance report '{report_type}' has been scheduled. Schedule ID: {schedule_id}. "
                   f"Next run: {next_run}. Results will be delivered to Webex room: {webex_room_id}. "
                   f"⚠️ Note: This is a scheduled report - no immediate analysis will be performed."
    }


# Export tools list
nso_tools = [
    trigger_nso_compliance_report,
    get_nso_report_details,
    list_nso_compliance_reports,
    schedule_nso_compliance_report
]
