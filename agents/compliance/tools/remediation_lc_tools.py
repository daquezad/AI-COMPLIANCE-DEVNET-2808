"""
Remediation Execution Tools for NSO compliance remediation.
These tools execute remediation actions: sync-to, re-deploy, apply-template via RESTCONF API.

The main entry point is execute_remediation_plan which processes a batch of remediation actions.
Individual actions (sync-to, re-deploy, apply-template) are internal helpers called by the batch executor.
"""
import json
import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

from agents.compliance.tools.connectors.nso_connector_rest import (
    sync_to_device,
    redeploy_service,
    apply_compliance_template,
    check_device_sync_status
)

logger = logging.getLogger("devnet.compliance.tools.remediation")


# =============================================================================
# INTERNAL REMEDIATION HANDLERS (called by execute_remediation_plan)
# =============================================================================

def _execute_sync_to(target: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a sync-to action on NSO devices (NSO → Device).
    
    Args:
        target: Dictionary containing one of:
            - device_name or device: Single device name
            - device_names: List of device names
    
    Returns:
        Dictionary with execution result
    """
    device_name = target.get("device_name") or target.get("device")
    device_names = target.get("device_names", [])
    
    if device_name:
        logger.info(f"Executing sync-to on device: {device_name}")
        result = sync_to_device(device_name)
        if result.get("success"):
            return {
                "success": True,
                "action": "sync-to",
                "device": device_name,
                "message": f"✅ Successfully synced to device '{device_name}'"
            }
        else:
            return {
                "success": False,
                "action": "sync-to",
                "device": device_name,
                "error": result.get("error"),
                "message": f"❌ Failed to sync to device '{device_name}'"
            }
    elif device_names:
        # Execute sync-to for multiple devices
        logger.info(f"Executing sync-to on {len(device_names)} devices: {device_names}")
        results = []
        for dev in device_names:
            results.append(sync_to_device(dev))
        all_success = all(r.get("success") for r in results)
        return {
            "success": all_success,
            "action": "sync-to",
            "devices": device_names,
            "results": results,
            "message": f"{'✅' if all_success else '❌'} Synced to {len(device_names)} device(s)"
        }
    else:
        return {"success": False, "error": "No device specified for sync-to action"}


def _execute_redeploy(service_type: str, service_instance: str) -> Dict[str, Any]:
    """
    Execute a re-deploy action on an NSO service.
    
    Args:
        service_type: The service type/model (e.g., "loopback-tunisie")
        service_instance: The service instance name (e.g., "TEST-Loopback")
    
    Returns:
        Dictionary with execution result
    """
    logger.info(f"Executing re-deploy on service: {service_type}/{service_instance}")
    
    # Pass service_type and service_instance separately - redeploy_service builds the correct path
    result = redeploy_service(service_type, service_instance)
    
    if result.get("success"):
        return {
            "success": True,
            "action": "re-deploy",
            "service_type": service_type,
            "service_instance": service_instance,
            "message": f"✅ Successfully re-deployed service '{service_type}/{service_instance}'"
        }
    else:
        return {
            "success": False,
            "action": "re-deploy",
            "service_type": service_type,
            "service_instance": service_instance,
            "error": result.get("error"),
            "message": f"❌ Failed to re-deploy service '{service_type}/{service_instance}'"
        }


def _execute_apply_template(template_name: str, target: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an apply-template action on NSO devices.
    
    Args:
        template_name: Name of the compliance template to apply
        target: Dictionary containing device_name, device_names (list), or device_group
    
    Returns:
        Dictionary with execution result
    """
    # Handle single device
    device_name = target.get("device_name") or target.get("device")
    
    # Handle multiple devices
    device_names = target.get("device_names", [])
    
    # Handle device group
    device_group = target.get("device_group")
    
    if device_name:
        # Single device execution
        logger.info(f"Applying template '{template_name}' to device: {device_name}")
        result = apply_compliance_template(device_name, template_name)
        
        if result.get("success"):
            return {
                "success": True,
                "action": "apply-template",
                "device": device_name,
                "template": template_name,
                "message": f"✅ Successfully applied template '{template_name}' to device '{device_name}'"
            }
        else:
            return {
                "success": False,
                "action": "apply-template",
                "device": device_name,
                "template": template_name,
                "error": result.get("error"),
                "message": f"❌ Failed to apply template '{template_name}' to device '{device_name}'"
            }
    
    elif device_names:
        # Multiple devices execution
        results = []
        failed = []
        
        for dev in device_names:
            logger.info(f"Applying template '{template_name}' to device: {dev}")
            result = apply_compliance_template(dev, template_name)
            
            if result.get("success"):
                results.append(f"✅ {dev}")
            else:
                failed.append(f"❌ {dev}: {result.get('error', 'Unknown error')}")
        
        success = len(failed) == 0
        return {
            "success": success,
            "action": "apply-template",
            "devices": device_names,
            "template": template_name,
            "successful": results,
            "failed": failed,
            "message": f"Applied template '{template_name}' to {len(results)}/{len(device_names)} devices" + 
                       (f". Failed: {', '.join(failed)}" if failed else "")
        }
    
    elif device_group:
        # Device group execution - apply to all devices in the group
        logger.info(f"Applying template '{template_name}' to device group: {device_group}")
        
        # Get devices from the group
        from agents.compliance.tools.connectors.nso_connector_rest.api.nso_config import get_devices_group
        group_result = get_devices_group(device_group)
        
        if not group_result.get("success"):
            return {
                "success": False,
                "action": "apply-template",
                "device_group": device_group,
                "template": template_name,
                "error": group_result.get("error", "Failed to get device group"),
                "message": f"❌ Failed to get devices from group '{device_group}'"
            }
        
        devices = group_result.get("devices", [])
        if not devices:
            return {
                "success": False,
                "action": "apply-template",
                "device_group": device_group,
                "template": template_name,
                "error": "No devices found in group",
                "message": f"❌ No devices found in group '{device_group}'"
            }
        
        # Apply to all devices in group
        results = []
        failed = []
        
        for dev in devices:
            logger.info(f"Applying template '{template_name}' to device: {dev}")
            result = apply_compliance_template(dev, template_name)
            
            if result.get("success"):
                results.append(f"✅ {dev}")
            else:
                failed.append(f"❌ {dev}: {result.get('error', 'Unknown error')}")
        
        success = len(failed) == 0
        return {
            "success": success,
            "action": "apply-template",
            "device_group": device_group,
            "devices": devices,
            "template": template_name,
            "successful": results,
            "failed": failed,
            "message": f"Applied template '{template_name}' to {len(results)}/{len(devices)} devices in group '{device_group}'" + 
                       (f". Failed: {', '.join(failed)}" if failed else "")
        }
    
    else:
        return {"success": False, "error": "No device specified for apply-template action. Provide 'device_name', 'device_names', or 'device_group' in target."}


def _check_device_sync(device_name: str) -> Dict[str, Any]:
    """
    Check if a device is in sync with NSO.
    
    Args:
        device_name: Name of the device to check
    
    Returns:
        Dictionary with sync status
    """
    logger.info(f"Checking sync status for device: {device_name}")
    result = check_device_sync_status(device_name)
    
    if result.get("success"):
        data = result.get("data", {})
        in_sync = "in-sync" in str(data).lower()
        return {
            "success": True,
            "device": device_name,
            "in_sync": in_sync,
            "message": f"Device '{device_name}' is {'in sync ✅' if in_sync else 'OUT OF SYNC ⚠️'}"
        }
    else:
        return {
            "success": False,
            "device": device_name,
            "error": result.get("error"),
            "message": f"❌ Failed to check sync status for '{device_name}'"
        }


# =============================================================================
# LANGCHAIN TOOL - BATCH REMEDIATION EXECUTOR
# =============================================================================

@tool
def execute_remediation_plan(remediation_plan_json: str) -> Dict[str, Any]:
    """
    Execute a remediation plan containing multiple remediation actions.
    
    This tool processes a JSON array of remediation actions generated by the planner.
    Each action specifies what type of remediation to perform (sync-to, re-deploy, 
    or apply-template) and the corresponding targets/parameters.
    
    Args:
        remediation_plan_json: JSON string containing an array of remediation actions.
            Each action must have:
            - id: Unique identifier for the action
            - action: One of "sync-to", "re-deploy", or "apply-template"
            
            For "sync-to" actions:
            - target: Object with one of: device_names (list), device_group (str), or device_name (str)
            
            For "re-deploy" actions:
            - service_type: The service type/path (e.g., "/ncs:services/loopback-demo:loopback-demo
")
            - service_instance: The service instance name
            
            For "apply-template" actions:
            - template_name: Name of the template to apply
            - target: Object with one of: device_names (list), device_group (str), or device_name (str)
    
    Returns:
        Dictionary containing:
        - success: True if all actions were processed
        - total_actions: Number of actions in the plan
        - results: List of results for each action
        - errors: List of any errors encountered
    
    Example Input:
        [
            {
                "id": 1,
                "action": "sync-to",
                "target": {"device_names": ["router1", "router2"]}
            },
            {
                "id": 2,
                "action": "re-deploy",
                "service_type": "/l3vpn:vpn/l3vpn",
                "service_instance": "ACME-L3VPN"
            },
            {
                "id": 3,
                "action": "apply-template",
                "template_name": "baseline-security",
                "target": {"device_group": "core-routers"}
            }
        ]
    
    Example Usage:
        - "Execute the remediation plan"
        - "Run all approved remediation actions"
        - "Apply the fixes from the compliance report"
    """
    logger.info("LLM Tool Call: execute_remediation_plan")
    
    # Parse JSON input
    try:
        actions = json.loads(remediation_plan_json)
        if not isinstance(actions, list):
            actions = [actions]  # Wrap single action in list
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON format: {str(e)}",
            "total_actions": 0,
            "results": [],
            "errors": [f"JSON parse error: {str(e)}"]
        }
    
    results = []
    errors = []
    
    for action_item in actions:
        action_id = action_item.get("id", "unknown")
        action_type = action_item.get("action", "").lower()
        
        logger.info(f"Processing action {action_id}: {action_type}")
        logger.info(f"Action item details: {json.dumps(action_item, indent=2)}")
        
        try:
            if action_type == "sync-to":
                target = action_item.get("target", {})
                if not target:
                    raise ValueError("sync-to action requires 'target' with device_names, device_group, or device_name")
                result = _execute_sync_to(target)
                
            elif action_type == "re-deploy":
                service_type = action_item.get("service_type")
                service_instance = action_item.get("service_instance")
                if not service_type or not service_instance:
                    raise ValueError("re-deploy action requires 'service_type' and 'service_instance'")
                
                # Handle case where LLM incorrectly puts "service_type/instance" in service_instance
                if "/" in service_instance:
                    # If service_instance contains a slash, extract just the instance name
                    parts = service_instance.split("/")
                    service_instance = parts[-1]  # Take the last part as the actual instance name
                    logger.info(f"Extracted instance name from path: {service_instance}")
                
                logger.info(f"Re-deploy: service_type={service_type}, service_instance={service_instance}")
                result = _execute_redeploy(service_type, service_instance)
                
            elif action_type == "apply-template":
                template_name = action_item.get("template_name")
                target = action_item.get("target", {})
                logger.info(f"apply-template: template_name={template_name}, target={target}")
                if not template_name:
                    raise ValueError("apply-template action requires 'template_name'")
                if not target:
                    raise ValueError("apply-template action requires 'target' with device_names, device_group, or device_name")
                result = _execute_apply_template(template_name, target)
                
            else:
                raise ValueError(f"Unknown action type: '{action_type}'. Must be one of: sync-to, re-deploy, apply-template")
            
            result["id"] = action_id
            results.append(result)
            logger.info(f"Action {action_id} completed: {result.get('status')}")
            
        except Exception as e:
            error_msg = f"Action {action_id} failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append({
                "id": action_id,
                "action": action_type,
                "status": "failed",
                "error": str(e)
            })
    
    success = len(errors) == 0
    return {
        "success": success,
        "total_actions": len(actions),
        "successful_actions": len([r for r in results if r.get("status") != "failed"]),
        "failed_actions": len(errors),
        "results": results,
        "errors": errors if errors else None,
        "message": f"Processed {len(actions)} action(s): {len(actions) - len(errors)} succeeded, {len(errors)} failed"
    }


# Export tools list - only the batch executor is exposed as a LangChain tool
remediation_tools = [
    execute_remediation_plan,
]
