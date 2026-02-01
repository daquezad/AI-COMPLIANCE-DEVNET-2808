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


# Export tools list
cwm_tools = [
    execute_cwm_remediation_workflow,
    get_cwm_job_status,
    list_cwm_available_workflows,
    get_cwm_workflow_details,
    run_cwm_workflow,
    create_cwm_job,
]
