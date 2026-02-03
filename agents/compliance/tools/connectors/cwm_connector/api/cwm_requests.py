from typing import Any, Dict, List, Optional
import logging
import json
import urllib.parse
import random
from datetime import datetime
from agents.compliance.tools.connectors.cwm_connector.request_handler import CrossworkApiClient
from config.config import CWM_USERNAME, CWM_PASSWORD, CWM_HOST, CWM_PORT

logger = logging.getLogger("devnet.agents.compliance.tools.connectors.cwm_connector.cwm_requests")

_CLIENT: Optional[CrossworkApiClient] = None


def _get_client() -> CrossworkApiClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = CrossworkApiClient(
            base_url=f"https://{CWM_HOST}:{CWM_PORT}",
            auth_url=f"https://{CWM_HOST}:{CWM_PORT}/crosswork",
            username=CWM_USERNAME,
            password=CWM_PASSWORD,
            verify_ssl=False,  # make configurable
        )
    return _CLIENT


def query_inventory_nodes(query_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    client = _get_client()
    path = "crosswork/inventory/v1/nodes/query"
    payload: Dict[str, Any] = query_payload or {}

    response = client.post(path, data=payload)
    if response.status_code >= 400:
        text = getattr(response, "text", "")
        logger.error("Inventory query failed status=%s body=%s", response.status_code, text)
        return {"data": [], "total_count": 0, "result_count": 0, "error": text}

    # adjust based on your client's actual interface
    data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
    return data or {"data": [], "total_count": 0, "result_count": 0}


def list_cwm_workflows() -> Dict[str, Any]:
    """
    List all available workflows from Crosswork Workflow Manager (CWM).
    
    Returns:
        Dict containing workflow list or error information:
        - success: True if request succeeded
        - workflows: List of workflow definitions
        - error: Error message if failed
    """
    client = _get_client()
    path = "crosswork/cwm/v2/workflow"
    
    logger.info("Fetching CWM workflows list")
    
    try:
        response = client.get(path)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM workflow list failed status=%s body=%s", response.status_code, text)
            return {"success": False, "workflows": [], "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
        
        logger.info(f"Successfully retrieved CWM workflows")
        return {"success": True, "workflows": data, "error": None}
        
    except Exception as e:
        logger.error(f"Error fetching CWM workflows: {e}")
        return {"success": False, "workflows": [], "error": str(e)}


def get_cwm_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    Get details of a specific workflow from Crosswork Workflow Manager (CWM).
    
    Args:
        workflow_id: The ID of the workflow to retrieve
    
    Returns:
        Dict containing workflow details or error information:
        - success: True if request succeeded
        - workflow: Workflow definition details
        - error: Error message if failed
    """
    client = _get_client()
    path = f"crosswork/cwm/v2/workflow/{workflow_id}"
    
    logger.info(f"Fetching CWM workflow: {workflow_id}")
    
    try:
        response = client.get(path)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM workflow get failed status=%s body=%s", response.status_code, text)
            return {"success": False, "workflow": None, "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
        
        logger.info(f"Successfully retrieved CWM workflow: {workflow_id}")
        return {"success": True, "workflow": data, "error": None}
        
    except Exception as e:
        logger.error(f"Error fetching CWM workflow {workflow_id}: {e}")
        return {"success": False, "workflow": None, "error": str(e)}


def execute_cwm_workflow(workflow_id: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a workflow in Crosswork Workflow Manager (CWM).
    
    Args:
        workflow_id: The ID of the workflow to execute
        inputs: Optional dict of input parameters for the workflow
    
    Returns:
        Dict containing execution result or error information:
        - success: True if execution started successfully
        - execution_id: ID of the workflow execution instance
        - result: Execution response data
        - error: Error message if failed
    """
    client = _get_client()
    path = f"crosswork/cwm/v2/workflow/{workflow_id}/execute"
    payload = inputs or {}
    
    logger.info(f"Executing CWM workflow: {workflow_id}")
    
    try:
        response = client.post(path, data=payload)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM workflow execute failed status=%s body=%s", response.status_code, text)
            return {"success": False, "execution_id": None, "result": None, "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
        
        execution_id = data.get("executionId") or data.get("execution_id") or data.get("id")
        logger.info(f"Successfully started CWM workflow execution: {execution_id}")
        return {"success": True, "execution_id": execution_id, "result": data, "error": None}
        
    except Exception as e:
        logger.error(f"Error executing CWM workflow {workflow_id}: {e}")
        return {"success": False, "execution_id": None, "result": None, "error": str(e)}


def create_cwm_job(
    job_name: str,
    workflow_name: str,
    workflow_version: str = "1.0",
    data: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new job in Crosswork Workflow Manager (CWM).
    
    A job is an instance of a workflow execution with specific parameters.
    
    Args:
        job_name: Name for the job (e.g., "NTP Remediation Job")
        workflow_name: Name of the workflow to execute
        workflow_version: Version of the workflow (default: "1.0")
        data: Optional dict of input data/parameters for the job
        tags: Optional list of tags for the job (e.g., ["remediation", "ntp"])
    
    Returns:
        Dict containing job creation result:
        - success: True if job was created successfully
        - job_id: ID of the created job
        - result: Full response data from CWM
        - error: Error message if failed
    """
    client = _get_client()
    path = "crosswork/cwm/v2/job"
    
    payload = {
        "jobName": job_name,
        "workflowName": workflow_name,
        "workflowVersion": workflow_version,
        "data": data or {},
        "tags": tags or []
    }
    
    logger.info(f"Creating CWM job: {job_name} (workflow: {workflow_name} v{workflow_version})")
    
    try:
        response = client.post(path, data=payload)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM job creation failed status=%s body=%s", response.status_code, text)
            return {"success": False, "job_id": None, "result": None, "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
        
        job_id = data.get("jobId") or data.get("job_id") or data.get("id")
        logger.info(f"Successfully created CWM job: {job_id}")
        return {"success": True, "job_id": job_id, "result": data, "error": None}
        
    except Exception as e:
        logger.error(f"Error creating CWM job {job_name}: {e}")
        return {"success": False, "job_id": None, "result": None, "error": str(e)}


def schedule_cwm_workflow(
    schedule_id: str,
    workflow_name: str,
    workflow_version: str,
    job_name: str,
    cron_expressions: List[str],
    timezone: str = "UTC",
    overlap: int = 1,
    pause_on_failure: bool = True,
    paused: bool = False,
    trigger_immediately: bool = False,
    tags: Optional[List[str]] = None,
    note: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Schedule a workflow in Crosswork Workflow Manager (CWM).
    
    Creates a scheduled execution of a workflow based on cron expressions.
    
    Args:
        schedule_id: Unique identifier for the schedule (e.g., "unique-schedule-id-24")
        workflow_name: Name of the workflow to schedule
        workflow_version: Version of the workflow (e.g., "1.0")
        job_name: Name for the job instances (e.g., "exampleJob-daily")
        cron_expressions: List of cron expressions (e.g., ["0 0 6 * *"] for daily at 6 AM)
        timezone: Timezone name (default: "UTC")
        overlap: Number of overlapping executions allowed (default: 1)
        pause_on_failure: Whether to pause schedule on failure (default: True)
        paused: Whether the schedule starts paused (default: False)
        trigger_immediately: Whether to trigger immediately (default: False)
        tags: Optional list of tags (e.g., ["devnet", "ai"])
        note: Optional note/description for the schedule
    
    Returns:
        Dict containing schedule creation result:
        - success: True if schedule was created successfully
        - schedule_id: ID of the created schedule (with date prefix)
        - result: Full response data from CWM
        - error: Error message if failed
    """
    client = _get_client()
    path = "crosswork/cwm/v2/schedule"
    
    # Generate unique schedule_id with date prefix and random int
    date_prefix = datetime.now().strftime("%Y%m%d")
    random_suffix = random.randint(0, 99)
    unique_schedule_id = f"AI-{date_prefix}-{random_suffix}-{schedule_id}"
    
    payload = {
        "scheduleId": unique_schedule_id,
        "workflowName": workflow_name,
        "workflowVersion": workflow_version,
        "jobName": job_name,
        "spec": {
            "cronExpressions": cron_expressions,
            "timeZoneName": timezone
        },
        "overlap": overlap,
        "pauseOnFailure": pause_on_failure,
        "paused": paused,
        "triggerImmediately": trigger_immediately,
        "tags": tags or [],
        "note": note or "",
        "data": data or {}
    }
    
    logger.info(f"Creating CWM schedule: {unique_schedule_id} (workflow: {workflow_name} v{workflow_version})")
    
    try:
        response = client.post(path, data=payload)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM schedule creation failed status=%s body=%s", response.status_code, text)
            return {"success": False, "schedule_id": None, "result": None, "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
        
        schedule_id_result = data.get("scheduleId") or data.get("schedule_id") or unique_schedule_id
        logger.info(f"Successfully created CWM schedule: {schedule_id_result}")
        return {"success": True, "schedule_id": schedule_id_result, "result": data, "error": None}
        
    except Exception as e:
        logger.error(f"Error creating CWM schedule {unique_schedule_id}: {e}")
        return {"success": False, "schedule_id": None, "result": None, "error": str(e)}


# Predefined cron expressions for audit scheduling
# Standard 5-field cron format: minute hour day-of-month month day-of-week
AUDIT_CRON_SCHEDULES = {
    "DAILY": "0 6 * * *",        # Every day at 6:00 AM
    "WEEKLY": "0 6 * * 1",       # Every Monday at 6:00 AM
    "MONTHLY": "0 6 1 * *",      # 1st of every month at 6:00 AM
}


def schedule_compliance_audit(
    report_name: str,
    schedule_frequency: str,
    title: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    outformat: str = "html",
    timezone: str = "UTC",
    trigger_immediately: bool = False,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Schedule a compliance audit to run periodically using CWM.
    
    This function schedules the AUDIT_Compliance_Report workflow in CWM
    to run compliance reports on a recurring basis.
    
    Args:
        report_name: Name of the NSO compliance report to run
        schedule_frequency: Frequency of the audit. Must be one of:
                           - "DAILY": Run every day at 6:00 AM
                           - "WEEKLY": Run every Monday at 6:00 AM
                           - "MONTHLY": Run on the 1st of every month at 6:00 AM
        title: Optional title for the report (default: generated from report_name)
        from_time: Optional start time for historical data
        to_time: Optional end time for historical data
        outformat: Output format - 'html' or 'text' (default: 'html')
        timezone: Timezone for schedule execution (default: 'UTC')
        trigger_immediately: Whether to run immediately in addition to schedule (default: False)
        note: Optional note/description for the schedule
    
    Returns:
        Dict containing schedule creation result:
        - success: True if schedule was created successfully
        - schedule_id: ID of the created schedule
        - job_name: Generated job name
        - cron_expression: The cron expression used
        - result: Full response data from CWM
        - error: Error message if failed
    """
    # Validate schedule_frequency
    schedule_frequency_upper = schedule_frequency.upper()
    if schedule_frequency_upper not in AUDIT_CRON_SCHEDULES:
        return {
            "success": False,
            "schedule_id": None,
            "job_name": None,
            "cron_expression": None,
            "result": None,
            "error": f"Invalid schedule_frequency: '{schedule_frequency}'. Must be one of: DAILY, WEEKLY, MONTHLY"
        }
    
    cron_expression = AUDIT_CRON_SCHEDULES[schedule_frequency_upper]
    
    # Generate job name: AUDIT-{FREQUENCY}-{report_name or title}
    report_title = title if title else report_name
    job_name = f"AUDIT-{schedule_frequency_upper}-{report_title}".replace(" ", "_")
    
    # Generate schedule_id from report name
    schedule_id_suffix = f"audit-{report_name.lower().replace(' ', '-')}"
    
    # Generate note if not provided
    if not note:
        note = f"{schedule_frequency_upper} compliance audit for report: {report_name}"
    
    # Fixed values
    workflow_name = "AUDIT_Compliance_Report"
    workflow_version = "1.0"
    tags = ["AI", "AUDIT", "daquezad", "DEVNET"]
    
    # Build workflow input data
    workflow_data = {
        "report_name": report_name,
        "outformat": outformat,
    }
    if title:
        workflow_data["title"] = title
    if from_time:
        workflow_data["from_time"] = from_time
    if to_time:
        workflow_data["to_time"] = to_time
    
    logger.info(f"Scheduling compliance audit: {job_name} ({schedule_frequency_upper})")
    
    # Call the base schedule function
    result = schedule_cwm_workflow(
        schedule_id=schedule_id_suffix,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        job_name=job_name,
        cron_expressions=[cron_expression],
        timezone=timezone,
        tags=tags,
        note=note,
        trigger_immediately=trigger_immediately,
    )
    
    # Enhance result with audit-specific info
    result["job_name"] = job_name
    result["cron_expression"] = cron_expression
    result["schedule_frequency"] = schedule_frequency_upper
    result["report_name"] = report_name
    
    return result


def schedule_remediation_workflow(
    scheduled_datetime: str,
    description: str,
    devices: Optional[List[str]] = None,
    remediation_items: Optional[str] = None,
    timezone: str = "UTC"
) -> Dict[str, Any]:
    """
    Schedule a one-time remediation workflow at a specific date and time.
    
    This function schedules the FIX_Compliance_Remediation workflow in CWM
    to run once at the specified date and time. NO RECURRENCE.
    
    Args:
        scheduled_datetime: The date and time to run the remediation.
                           Format: "YYYY-MM-DD HH:MM" (e.g., "2026-02-15 10:30")
                           or ISO format "2026-02-15T10:30:00"
        description: Short description of the remediation action from the LLM.
                    This will be used as the note and part of the job name.
        devices: Optional list of devices targeted for remediation
        remediation_items: Optional JSON string with remediation details
        timezone: Timezone for schedule execution (default: 'UTC')
    
    Returns:
        Dict containing schedule creation result:
        - success: True if schedule was created successfully
        - schedule_id: ID of the created schedule
        - job_name: Generated job name
        - scheduled_datetime: The scheduled execution time
        - cron_expression: The cron expression used
        - result: Full response data from CWM
        - error: Error message if failed
    """
    # Parse the scheduled datetime
    try:
        # Support multiple formats
        dt_str = scheduled_datetime.replace("T", " ").strip()
        if len(dt_str.split(" ")) == 2:
            date_part, time_part = dt_str.split(" ")
            year, month, day = date_part.split("-")
            time_parts = time_part.split(":")
            hour = time_parts[0]
            minute = time_parts[1] if len(time_parts) > 1 else "0"
        else:
            return {
                "success": False,
                "schedule_id": None,
                "job_name": None,
                "scheduled_datetime": scheduled_datetime,
                "cron_expression": None,
                "result": None,
                "error": f"Invalid datetime format: '{scheduled_datetime}'. Use 'YYYY-MM-DD HH:MM' (e.g., '2026-02-15 10:30')"
            }
    except Exception as e:
        return {
            "success": False,
            "schedule_id": None,
            "job_name": None,
            "scheduled_datetime": scheduled_datetime,
            "cron_expression": None,
            "result": None,
            "error": f"Failed to parse datetime '{scheduled_datetime}': {str(e)}"
        }
    
    # Create cron expression for specific date/time
    # Format: minute hour day month day-of-week
    cron_expression = f"{minute} {hour} {day} {month} *"
    
    # Generate job name from description (sanitized)
    desc_short = description[:30].replace(" ", "_").replace("-", "_")
    job_name = f"REMEDIATION-{year}{month}{day}-{desc_short}"
    
    # Generate schedule_id
    schedule_id_suffix = f"remediation-{year}{month}{day}-{hour}{minute}"
    
    # Fixed values
    workflow_name = "FIX_Compliance_Remediation"
    workflow_version = "2.0"
    tags = ["AI", "REMEDIATION", "daquezad"]
    
    # Build workflow input data - only include remediation_plan for the workflow
    workflow_data = {}
    
    if remediation_items:
        # Parse remediation_items if it's a JSON string
        parsed_plan = remediation_items
        if isinstance(remediation_items, str):
            try:
                parsed_plan = json.loads(remediation_items)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse remediation_items as JSON: {remediation_items[:100]}...")
                parsed_plan = remediation_items
        
        # Extract the items array if the structure is {"items": [...]}
        if isinstance(parsed_plan, dict) and "items" in parsed_plan:
            workflow_data["remediation_plan"] = parsed_plan["items"]
        elif isinstance(parsed_plan, list):
            # Already an array, use directly
            workflow_data["remediation_plan"] = parsed_plan
        else:
            # Use as-is (might be the full dict)
            workflow_data["remediation_plan"] = parsed_plan
    
    # Note is the description from LLM
    note = f"One-time remediation: {description}"
    
    logger.info(f"Scheduling remediation workflow: {job_name} at {scheduled_datetime}")
    
    # Call the base schedule function
    result = schedule_cwm_workflow(
        schedule_id=schedule_id_suffix,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        job_name=job_name,
        cron_expressions=[cron_expression],
        timezone=timezone,
        tags=tags,
        note=note,
        trigger_immediately=False,  # Never trigger immediately for scheduled remediation
        data=workflow_data,
    )
    
    # Enhance result with remediation-specific info
    result["job_name"] = job_name
    result["scheduled_datetime"] = scheduled_datetime
    result["cron_expression"] = cron_expression
    result["description"] = description
    
    return result


def cancel_cwm_job_run(job_id: str, run_id: str) -> Dict[str, Any]:
    """
    Cancel a running job execution in Crosswork Workflow Manager (CWM).
    
    Args:
        job_id: The ID of the job (e.g., "5f0d02a9-004f-4af3-b1d2-8dcf5c6d6ed2")
        run_id: The ID of the specific run to cancel (e.g., "58eb5e15-fed6-47cb-9611-10d2c98de010")
    
    Returns:
        Dict containing cancellation result:
        - success: True if cancellation was successful
        - job_id: The job ID
        - run_id: The run ID
        - result: Full response data from CWM
        - error: Error message if failed
    """
    client = _get_client()
    path = f"crosswork/cwm/v2/job/{job_id}/runs/{run_id}/cancel"
    
    logger.info(f"Cancelling CWM job run: job_id={job_id}, run_id={run_id}")
    
    try:
        response = client.post(path, data={})
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM job cancellation failed status=%s body=%s", response.status_code, text)
            return {"success": False, "job_id": job_id, "run_id": run_id, "result": None, "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or {})
        
        logger.info(f"Successfully cancelled CWM job run: job_id={job_id}, run_id={run_id}")
        return {"success": True, "job_id": job_id, "run_id": run_id, "result": data, "error": None}
        
    except Exception as e:
        logger.error(f"Error cancelling CWM job run job_id={job_id}, run_id={run_id}: {e}")
        return {"success": False, "job_id": job_id, "run_id": run_id, "result": None, "error": str(e)}


def list_cwm_schedules(prefix_filter: Optional[str] = "AI", tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    List scheduled workflows from Crosswork Workflow Manager (CWM).
    
    Retrieves all schedules and optionally filters by ID prefix.
    Returns simplified data with ID, Note, and Spec for each schedule.
    
    Args:
        prefix_filter: Optional prefix to filter schedule IDs (default: "AI").
                       Set to None or empty string to return all schedules.
        tags: Optional list of tags to filter by (e.g., ["devnet"])
    
    Returns:
        Dict containing:
        - success: True if request succeeded
        - total_count: Total number of schedules before filtering
        - filtered_count: Number of schedules after filtering
        - schedules: List of filtered schedules with ID, Note, Spec, NextActionTimes
        - error: Error message if failed
    """
    client = _get_client()
    path = "crosswork/cwm/v2/schedule"
    
    # Prepare payload for tags filter if provided
    payload = {}
    if tags:
        payload["tags"] = ",".join(tags) if isinstance(tags, list) else tags
    
    logger.info(f"Fetching CWM schedules list (prefix_filter={prefix_filter}, tags={tags})")
    
    try:
        response = client.get(path, params=payload if payload else None)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM schedules list failed status=%s body=%s", response.status_code, text)
            return {"success": False, "total_count": 0, "filtered_count": 0, "schedules": [], "error": text}
        
        data = response.json() if callable(getattr(response, "json", None)) else (response.json or [])
        
        # Ensure data is a list
        schedules_list = data if isinstance(data, list) else []
        total_count = len(schedules_list)
        
        # Filter by prefix if specified
        if prefix_filter:
            filtered_schedules = [
                s for s in schedules_list 
                if s.get("ID", "").upper().startswith(prefix_filter.upper())
            ]
        else:
            filtered_schedules = schedules_list
        
        # Extract only ID, Note, Spec, and NextActionTimes
        simplified_schedules = []
        for schedule in filtered_schedules:
            simplified_schedules.append({
                "ID": schedule.get("ID"),
                "Note": schedule.get("Note", ""),
                "Spec": schedule.get("Spec", {}),
                "NextActionTimes": schedule.get("NextActionTimes", []),
                "Paused": schedule.get("Paused", False)
            })
        
        logger.info(f"Retrieved {total_count} schedules, {len(simplified_schedules)} match filter")
        return {
            "success": True,
            "total_count": total_count,
            "filtered_count": len(simplified_schedules),
            "schedules": simplified_schedules,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error fetching CWM schedules: {e}")
        return {"success": False, "total_count": 0, "filtered_count": 0, "schedules": [], "error": str(e)}


def delete_cwm_schedule(schedule_id: str, require_ai_prefix: bool = True) -> Dict[str, Any]:
    """
    Delete a scheduled workflow from Crosswork Workflow Manager (CWM).
    
    For safety, by default only schedules with IDs starting with 'AI' can be deleted.
    
    Args:
        schedule_id: The ID of the schedule to delete
        require_ai_prefix: If True (default), only allow deletion if ID starts with 'AI'
    
    Returns:
        Dict containing:
        - success: True if deletion was successful
        - schedule_id: The deleted schedule ID
        - error: Error message if failed
    """
    # Safety check: Only delete schedules starting with 'AI' by default
    if require_ai_prefix and not schedule_id.upper().startswith("AI"):
        error_msg = f"Safety check failed: Schedule ID '{schedule_id}' does not start with 'AI'. Set require_ai_prefix=False to override."
        logger.warning(error_msg)
        return {"success": False, "schedule_id": schedule_id, "error": error_msg}
    
    client = _get_client()
    path = f"crosswork/cwm/v2/schedule/{schedule_id}"
    
    logger.info(f"Deleting CWM schedule: {schedule_id}")
    
    try:
        response = client.delete(path)
        
        if response.status_code >= 400:
            text = getattr(response, "text", "")
            logger.error("CWM schedule deletion failed status=%s body=%s", response.status_code, text)
            return {"success": False, "schedule_id": schedule_id, "error": text}
        
        logger.info(f"Successfully deleted CWM schedule: {schedule_id}")
        return {"success": True, "schedule_id": schedule_id, "error": None}
        
    except Exception as e:
        logger.error(f"Error deleting CWM schedule {schedule_id}: {e}")
        return {"success": False, "schedule_id": schedule_id, "error": str(e)}



