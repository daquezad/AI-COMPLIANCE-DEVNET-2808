"""
CWM (Crosswork Workflow Manager) Tools for remediation execution.
These tools interact with CWM to execute and schedule remediation workflows.
"""
import json
import logging
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool

from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import (
    list_cwm_workflows as _list_cwm_workflows,
    get_cwm_workflow as _get_cwm_workflow,
    execute_cwm_workflow as _execute_cwm_workflow,
    create_cwm_job as _create_cwm_job,
    schedule_compliance_audit as _schedule_compliance_audit,
    schedule_remediation_workflow as _schedule_remediation_workflow,
    list_cwm_schedules as _list_cwm_schedules,
    delete_cwm_schedule as _delete_cwm_schedule,
)

logger = logging.getLogger("devnet.compliance.tools.cwm")


@tool
def execute_cwm_remediation_workflow(
    workflow_name: str,
    schedule_type: str,
    schedule_value: str,
    items: str
) -> dict:
    """
    Executes a CWM remediation workflow with the specified items and schedule.
    
    Args:
        workflow_name: Name of the workflow to execute (e.g., 'remediation_batch_exec')
        schedule_type: Type of schedule - 'immediate', 'once', or 'periodic'
        schedule_value: ISO-8601 timestamp for 'once', cron expression for 'periodic', or 'now' for immediate
        items: JSON string containing array of remediation items with id, critical, action, target, and params
    
    Returns:
        Dictionary containing the job/schedule ID and execution status.
    """
    logger.info(f"Executing CWM workflow: {workflow_name}")
    
    try:
        items_list = json.loads(items)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Invalid JSON format for items parameter"
        }
    
    # Mock implementation - in production, this would call CWM API
    if schedule_type == "immediate":
        job_id = f"JOB-{hash(workflow_name) % 100000:05d}"
        status = "Success"
        message = f"Workflow executed immediately. {len(items_list)} items processed."
    elif schedule_type == "once":
        job_id = f"SCHED-{hash(schedule_value) % 100000:05d}"
        status = "Scheduled"
        message = f"Workflow scheduled for {schedule_value}. {len(items_list)} items queued."
    elif schedule_type == "periodic":
        job_id = f"PERIODIC-{hash(schedule_value) % 100000:05d}"
        status = "Scheduled"
        message = f"Recurring workflow configured: {schedule_value}. {len(items_list)} items in rotation."
    else:
        return {
            "success": False,
            "error": f"Invalid schedule_type: {schedule_type}. Must be 'immediate', 'once', or 'periodic'"
        }
    
    return {
        "success": True,
        "job_id": job_id,
        "status": status,
        "message": message,
        "items_processed": len(items_list),
        "workflow_name": workflow_name,
        "schedule_info": {
            "type": schedule_type,
            "value": schedule_value
        }
    }


@tool
def get_cwm_job_status(job_id: str) -> dict:
    """
    Retrieves the current status of a CWM job or scheduled workflow.
    
    Args:
        job_id: The job or schedule ID to check (e.g., 'JOB-12345' or 'SCHED-99821')
    
    Returns:
        Dictionary containing the job status and details.
    """
    logger.info(f"Checking CWM job status: {job_id}")
    
    # Mock implementation
    if job_id.startswith("JOB-"):
        return {
            "success": True,
            "job_id": job_id,
            "status": "Completed",
            "progress": 100,
            "message": "All remediation actions completed successfully",
            "completed_at": "2026-01-31T08:15:00Z"
        }
    elif job_id.startswith("SCHED-") or job_id.startswith("PERIODIC-"):
        return {
            "success": True,
            "job_id": job_id,
            "status": "Active",
            "next_run": "2026-02-02T02:00:00Z",
            "message": "Schedule is active and queued for next execution"
        }
    else:
        return {
            "success": False,
            "error": f"Job '{job_id}' not found"
        }


@tool
def list_cwm_available_workflows() -> Dict[str, Any]:
    """
    List all available workflows from Crosswork Workflow Manager (CWM).
    
    Use this tool to discover what remediation workflows are available in CWM
    before executing them. Returns a list of workflow definitions with their IDs,
    names, descriptions, and required input parameters.
    
    Returns:
        Dictionary containing:
        - success: True if request succeeded
        - workflows: List of available workflow definitions
        - error: Error message if request failed
    
    ⚠️ DISPLAY AS TABLE:
    | # | Workflow ID | Name | Version | Description |
    |---|-------------|------|---------|-------------|
    | 1 | AUDIT_Compliance_Report | Audit | 1.0 | Run compliance audit |
    
    Example Usage:
        - "What workflows are available in CWM?"
        - "List all remediation workflows"
        - "Show me the available automation workflows"
    """
    logger.info("LLM Tool Call: list_cwm_available_workflows")
    return _list_cwm_workflows()


@tool
def get_cwm_workflow_details(workflow_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific CWM workflow.
    
    Use this tool to get the full definition of a workflow including:
    - Input parameters required
    - Workflow steps/tasks
    - Expected outputs
    - Description and documentation
    
    Args:
        workflow_id: The unique identifier of the workflow to retrieve
    
    Returns:
        Dictionary containing:
        - success: True if request succeeded
        - workflow: Full workflow definition and details
        - error: Error message if request failed
    
    Example Usage:
        - "Show me details of workflow XYZ"
        - "What inputs does the NTP remediation workflow need?"
    """
    logger.info(f"LLM Tool Call: get_cwm_workflow_details -> {workflow_id}")
    return _get_cwm_workflow(workflow_id)


@tool
def run_cwm_workflow(workflow_id: str, inputs: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a workflow in Crosswork Workflow Manager (CWM).
    
    This tool triggers the execution of a CWM workflow. Use 'list_cwm_available_workflows'
    first to discover available workflows and 'get_cwm_workflow_details' to understand
    the required input parameters.
    
    Args:
        workflow_id: The unique identifier of the workflow to execute
        inputs: Optional JSON string containing input parameters for the workflow.
                Format: '{"param1": "value1", "param2": "value2"}'
    
    Returns:
        Dictionary containing:
        - success: True if execution started successfully
        - execution_id: ID to track the workflow execution
        - result: Execution response data
        - error: Error message if execution failed
    
    Example Usage:
        - "Run the NTP remediation workflow for device router1"
        - "Execute workflow abc-123 with inputs {\"device\": \"switch1\"}"
    """
    logger.info(f"LLM Tool Call: run_cwm_workflow -> {workflow_id}")
    
    # Parse inputs if provided as JSON string
    input_dict = None
    if inputs:
        try:
            input_dict = json.loads(inputs)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "execution_id": None,
                "result": None,
                "error": f"Invalid JSON format for inputs: {str(e)}"
            }
    
    return _execute_cwm_workflow(workflow_id, input_dict)


@tool
def create_cwm_job(
    job_name: str,
    workflow_name: str,
    workflow_version: str = "1.0",
    data: Optional[str] = None,
    tags: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new job in Crosswork Workflow Manager (CWM).
    
    A job is an instance of a workflow execution with specific parameters.
    Use this tool to create and queue a remediation job for execution.
    
    Args:
        job_name: Name for the job (e.g., "NTP Remediation Job", "Config Backup")
        workflow_name: Name of the workflow to execute (use list_cwm_available_workflows to find available workflows)
        workflow_version: Version of the workflow (default: "1.0")
        data: Optional JSON string containing input data/parameters for the job
              Format: '{"device": "router1", "action": "remediate"}'
        tags: Optional JSON array string of tags for the job
              Format: '["remediation", "ntp", "critical"]'
    
    Returns:
        Dictionary containing:
        - success: True if job was created successfully
        - job_id: ID of the created job for tracking
        - result: Full response data from CWM
        - error: Error message if creation failed
    
    Example Usage:
        - "Create a job to remediate NTP on router1"
        - "Schedule a config backup job with tags production and critical"
    """
    logger.info(f"LLM Tool Call: create_cwm_job -> {job_name} (workflow: {workflow_name})")
    
    # Parse data if provided as JSON string
    data_dict = None
    if data:
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "job_id": None,
                "result": None,
                "error": f"Invalid JSON format for data: {str(e)}"
            }
    
    # Parse tags if provided as JSON string
    tags_list = None
    if tags:
        try:
            tags_list = json.loads(tags)
            if not isinstance(tags_list, list):
                tags_list = [tags_list]
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            tags_list = [t.strip() for t in tags.split(",")]
    
    return _create_cwm_job(
        job_name=job_name,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        data=data_dict,
        tags=tags_list
    )


@tool
def schedule_compliance_audit(
    report_name: str,
    schedule_frequency: str,
    title: Optional[str] = None,
    trigger_immediately: bool = False,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Schedule a recurring compliance audit to run automatically.
    
    USE THIS TOOL when the user wants to:
    - Schedule a compliance audit to run periodically (daily, weekly, monthly)
    - Set up automated compliance checks
    - Create a recurring compliance report schedule
    
    This schedules the AUDIT_Compliance_Report workflow in Crosswork Workflow Manager (CWM)
    to automatically run NSO compliance reports on a recurring basis.
    
    Args:
        report_name: Name of the NSO compliance report to schedule (must exist in NSO).
                     Use list_compliance_report_definitions to find available reports.
        schedule_frequency: How often to run the audit. MUST be one of:
                           - "DAILY": Run every day at 6:00 AM UTC
                           - "WEEKLY": Run every Monday at 6:00 AM UTC  
                           - "MONTHLY": Run on the 1st of every month at 6:00 AM UTC
        title: Optional custom title for the report (default: uses report_name)
        trigger_immediately: If True, runs the audit immediately AND schedules future runs.
                            If False (default), only schedules future runs.
        note: Optional description for the schedule (default: auto-generated)
    
    Returns:
        Dictionary containing:
        - success: True if schedule was created successfully
        - schedule_id: Unique ID of the created schedule (starts with 'AI-')
        - job_name: Generated job name (format: AUDIT-{FREQUENCY}-{report_name})
        - cron_expression: The cron expression used for scheduling
        - schedule_frequency: The frequency (DAILY/WEEKLY/MONTHLY)
        - report_name: The report being scheduled
        - error: Error message if scheduling failed
    
    Example Usage:
        - "Schedule a daily compliance audit for the ntp-audit report"
        - "Set up weekly automated compliance checks for device-baseline report"
        - "Create a monthly compliance audit schedule and run it now"
    
    Notes:
        - Only DAILY, WEEKLY, or MONTHLY frequencies are supported
        - Scheduled audits use fixed tags: AI, AUDIT, daquezad, DEVNET
        - Schedule IDs always start with 'AI-' for safety (can be deleted with delete_cwm_schedule)
    """
    logger.info(f"LLM Tool Call: schedule_compliance_audit -> {report_name} ({schedule_frequency})")
    
    return _schedule_compliance_audit(
        report_name=report_name,
        schedule_frequency=schedule_frequency,
        title=title,
        trigger_immediately=trigger_immediately,
        note=note
    )


@tool
def schedule_remediation_workflow(
    scheduled_datetime: str,
    description: str,
    devices: Optional[str] = None,
    remediation_items: Optional[str] = None
) -> Dict[str, Any]:
    """
    Schedule a ONE-TIME remediation workflow at a specific date and time.
    
    USE THIS TOOL when the user wants to:
    - Schedule a remediation to run at a specific future date/time
    - Plan a maintenance window for applying fixes
    - Schedule configuration changes for a specific time
    
    This schedules the FIX_Compliance_Remediation workflow in Crosswork Workflow Manager (CWM)
    to run ONCE at the specified date and time. NO RECURRENCE - this is for one-time execution only.
    
    Args:
        scheduled_datetime: The exact date and time to run the remediation.
                           Format: "YYYY-MM-DD HH:MM" (24-hour format)
                           Examples: "2026-02-15 10:30", "2026-03-01 06:00"
        description: Short, descriptive summary of the remediation action.
                    This should describe what will be fixed/remediated.
                    Examples:
                    - "Fix NTP configuration on router1 and router2"
                    - "Apply DNS baseline to all DC routers"
                    - "Remediate ACL violations on edge devices"
        devices: Optional JSON array of device names being remediated.
                Format: '["router1", "router2", "switch1"]'
        remediation_items: Optional JSON string with detailed remediation items.
                          Format: '{"items": [...], "action": "apply"}'
    
    Returns:
        Dictionary containing:
        - success: True if schedule was created successfully
        - schedule_id: Unique ID of the created schedule (starts with 'AI-')
        - job_name: Generated job name (format: REMEDIATION-{DATE}-{description})
        - scheduled_datetime: The scheduled execution time
        - cron_expression: The cron expression used
        - description: The remediation description
        - error: Error message if scheduling failed
    
    Example Usage:
        - "Schedule remediation for tomorrow at 6 AM to fix NTP on all routers"
        - "Plan a maintenance window on 2026-02-20 at 22:00 to apply ACL fixes"
        - "Schedule the DNS fix for next Monday at 10:30"
    
    Notes:
        - This is for ONE-TIME execution only, not recurring schedules
        - Use schedule_compliance_audit for recurring audits
        - Fixed tags: AI, REMEDIATION, daquezad
        - Workflow: FIX_Compliance_Remediation v1.0
        - Schedule IDs start with 'AI-' for safety
    """
    logger.info(f"LLM Tool Call: schedule_remediation_workflow -> {scheduled_datetime}")
    
    # Parse devices if provided as JSON string
    devices_list = None
    if devices:
        try:
            devices_list = json.loads(devices)
            if not isinstance(devices_list, list):
                devices_list = [devices_list]
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            devices_list = [d.strip() for d in devices.split(",")]
    
    # Transform remediation_items to the format expected by CWM workflow
    # Expected format: {"items": [{id, action, target, template_name/service_type/service_instance}, ...]}
    transformed_items = None
    if remediation_items:
        try:
            parsed = json.loads(remediation_items) if isinstance(remediation_items, str) else remediation_items
            
            # If it has 'details' field with actual item objects, use that
            if isinstance(parsed, dict) and "details" in parsed:
                details = parsed["details"]
                transformed = []
                for item in details:
                    action = item.get("action", "").lower()
                    transformed_item = {
                        "id": item.get("id"),
                        "action": action
                    }
                    
                    if action == "apply-template":
                        # Extract template_name from 'details' field
                        transformed_item["template_name"] = item.get("details", item.get("template_name", ""))
                        # Build target structure
                        target_device = item.get("target")
                        if target_device:
                            transformed_item["target"] = {"device_name": target_device}
                    
                    elif action == "re-deploy":
                        # Parse service path from 'details' (e.g., "vpn/l3vpn/ACME-L3VPN")
                        details_str = item.get("details", "")
                        if "/" in details_str:
                            parts = details_str.rsplit("/", 1)
                            service_path = parts[0] if len(parts) > 1 else ""
                            service_instance = parts[-1]
                            # Try to format service_type properly
                            if ":" not in service_path and "/" in service_path:
                                # e.g., "vpn/l3vpn" -> "l3vpn:vpn/l3vpn"
                                path_parts = service_path.split("/")
                                module = path_parts[-1]
                                transformed_item["service_type"] = f"{module}:{service_path}"
                            else:
                                transformed_item["service_type"] = service_path
                            transformed_item["service_instance"] = service_instance
                        else:
                            transformed_item["service_type"] = item.get("target", "")
                            transformed_item["service_instance"] = details_str
                    
                    elif action == "sync-to":
                        target_device = item.get("target")
                        if target_device:
                            transformed_item["target"] = {"device_names": [target_device] if isinstance(target_device, str) else target_device}
                    
                    transformed.append(transformed_item)
                
                transformed_items = json.dumps(transformed)
                logger.info(f"Transformed remediation items: {transformed_items[:200]}...")
            else:
                # Use as-is if already in expected format
                transformed_items = remediation_items
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to transform remediation_items: {e}")
            transformed_items = remediation_items

    return _schedule_remediation_workflow(
        scheduled_datetime=scheduled_datetime,
        description=description,
        devices=devices_list,
        remediation_items=transformed_items
    )


@tool
def list_cwm_schedules(prefix_filter: str = "AI") -> Dict[str, Any]:
    """
    List scheduled workflows from Crosswork Workflow Manager (CWM).
    
    USE THIS TOOL when the user wants to:
    - View all scheduled audits or remediations
    - Check existing schedules before creating new ones
    - Find schedule IDs for deletion
    
    By default, only shows schedules with IDs starting with 'AI' (created by this system).
    
    Args:
        prefix_filter: Filter schedules by ID prefix (default: "AI").
                      Set to empty string "" to show ALL schedules.
                      Examples: "AI" for AI-created, "AUDIT" for audit schedules
    
    Returns:
        Dictionary containing:
        - success: True if request succeeded
        - total_count: Total number of schedules in CWM
        - filtered_count: Number matching the prefix filter
        - schedules: List of schedules with ID, Note, Spec, NextActionTimes, Paused
        - error: Error message if failed
    
    ⚠️ DISPLAY AS TABLE:
    | # | Schedule ID | Note | Cron | Next Run | Status |
    |---|-------------|------|------|----------|--------|
    | 1 | AI-20260201-audit | Weekly audit | 0 6 * * 1 | Mon 06:00 | ▶️ Active |
    
    Example Usage:
        - "Show me all scheduled audits"
        - "List my scheduled remediations"
        - "What schedules are configured?"
    """
    logger.info(f"LLM Tool Call: list_cwm_schedules -> prefix_filter={prefix_filter}")
    
    return _list_cwm_schedules(prefix_filter=prefix_filter)


@tool
def delete_cwm_schedule(schedule_id: str) -> Dict[str, Any]:
    """
    Delete a scheduled workflow from Crosswork Workflow Manager (CWM).
    
    USE THIS TOOL when the user wants to:
    - Remove/cancel a scheduled audit or remediation
    - Delete an unwanted schedule
    - Clean up old schedules
    
    SAFETY: Only schedules with IDs starting with 'AI' can be deleted.
    This prevents accidental deletion of system schedules.
    
    Args:
        schedule_id: The ID of the schedule to delete.
                    Must start with 'AI' (case-insensitive).
                    Use list_cwm_schedules to find schedule IDs.
    
    Returns:
        Dictionary containing:
        - success: True if deletion was successful
        - schedule_id: The deleted schedule ID
        - error: Error message if deletion failed or ID doesn't start with 'AI'
    
    Example Usage:
        - "Delete the schedule AI-20260201-15-audit-ntp-report"
        - "Remove the scheduled remediation for tomorrow"
        - "Cancel the daily audit schedule"
    
    Notes:
        - Only AI-prefixed schedules can be deleted for safety
        - Use list_cwm_schedules first to find the schedule ID
        - Deletion is permanent and cannot be undone
    """
    logger.info(f"LLM Tool Call: delete_cwm_schedule -> {schedule_id}")
    
    return _delete_cwm_schedule(schedule_id=schedule_id)


# Export tools list
cwm_tools = [
    # execute_cwm_remediation_workflow,
    get_cwm_job_status,
    list_cwm_available_workflows,
    get_cwm_workflow_details,
    # run_cwm_workflow,
    # create_cwm_job,
    schedule_compliance_audit,
    schedule_remediation_workflow,
    list_cwm_schedules,
    delete_cwm_schedule,
]

