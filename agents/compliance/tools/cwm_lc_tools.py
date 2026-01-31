"""
CWM (Crosswork Workflow Manager) Tools for remediation execution.
These tools interact with CWM to execute and schedule remediation workflows.
"""
import json
import logging
from typing import List, Optional
from langchain_core.tools import tool

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


# Export tools list
cwm_tools = [
    execute_cwm_remediation_workflow,
    get_cwm_job_status
]
