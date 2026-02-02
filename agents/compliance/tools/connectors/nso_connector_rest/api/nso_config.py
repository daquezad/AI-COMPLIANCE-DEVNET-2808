"""
NSO RESTCONF API functions for device and configuration management.

This module provides functions to interact with NSO via RESTCONF API
for general functionalities like getting devices, groups, and syncing.
"""
import logging
from typing import Optional, Dict, List, Any

from config.config import (
    NSO_USERNAME,
    NSO_PASSWORD,
    NSO_HOST_DOWNLOAD,
    NSO_JSONRPC_PORT,
    NSO_PROTOCOL
)
from agents.compliance.tools.connectors.nso_connector_rest.request_handler import (
    SimpleHttpClient,
    Response
)

logger = logging.getLogger("devnet.compliance.tools.nso.rest.config")


def get_nso_rest_client() -> SimpleHttpClient:
    """
    Factory function to create an NSO RESTCONF client with default settings.
    
    Returns:
        SimpleHttpClient configured for NSO RESTCONF API
    """
    base_url = f"{NSO_PROTOCOL}://{NSO_HOST_DOWNLOAD}:{NSO_JSONRPC_PORT}/restconf/data"
    return SimpleHttpClient(
        username=NSO_USERNAME,
        password=NSO_PASSWORD,
        base_url=base_url
    )


def get_devices_group() -> Dict[str, Any]:
    """
    Get the list of device groups from NSO.
    
    Returns:
        Dict containing device groups or error information
    """
    client = get_nso_rest_client()
    response = client.get("tailf-ncs:devices/device-group")
    
    if response.ok:
        return {"success": True, "data": response.json}
    else:
        logger.error("Failed to get device groups: %s", response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def get_devices_list() -> Dict[str, Any]:
    """
    Get the list of all devices from NSO.
    
    Returns:
        Dict containing device names or error information
    """
    client = get_nso_rest_client()
    response = client.get("tailf-ncs:devices/device?fields=name")
    
    if response.ok:
        return {"success": True, "data": response.json}
    else:
        logger.error("Failed to get devices list: %s", response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def get_device_details(device_name: str) -> Dict[str, Any]:
    """
    Get details for a specific device.
    
    Args:
        device_name: Name of the device to query
        
    Returns:
        Dict containing device details or error information
    """
    client = get_nso_rest_client()
    response = client.get(f"tailf-ncs:devices/device={device_name}")
    
    if response.ok:
        return {"success": True, "data": response.json}
    else:
        logger.error("Failed to get device details for %s: %s", device_name, response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def sync_from_device(device_name: str) -> Dict[str, Any]:
    """
    Sync configuration FROM a device to NSO (device → NSO).
    
    Args:
        device_name: Name of the device to sync from
        
    Returns:
        Dict containing sync result or error information
    """
    client = get_nso_rest_client()
    response = client.post(f"tailf-ncs:devices/device={device_name}/sync-from")
    
    if response.ok:
        logger.info("Successfully synced from device: %s", device_name)
        return {"success": True, "data": response.json, "message": f"Synced from {device_name}"}
    else:
        logger.error("Failed to sync from device %s: %s", device_name, response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def sync_to_device(device_name: str) -> Dict[str, Any]:
    """
    Sync configuration TO a device from NSO (NSO → device).
    
    Args:
        device_name: Name of the device to sync to
        
    Returns:
        Dict containing sync result or error information
    """
    client = get_nso_rest_client()
    response = client.post(f"tailf-ncs:devices/device={device_name}/sync-to")
    
    if response.ok:
        logger.info("Successfully synced to device: %s", device_name)
        return {"success": True, "data": response.json, "message": f"Synced to {device_name}"}
    else:
        logger.error("Failed to sync to device %s: %s", device_name, response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def check_device_sync_status(device_name: str) -> Dict[str, Any]:
    """
    Check the sync status of a device.
    
    Args:
        device_name: Name of the device to check
        
    Returns:
        Dict containing sync status or error information
    """
    client = get_nso_rest_client()
    response = client.post(f"tailf-ncs:devices/device={device_name}/check-sync")
    
    if response.ok:
        return {"success": True, "data": response.json}
    else:
        logger.error("Failed to check sync for device %s: %s", device_name, response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def get_compliance_reports_list() -> Dict[str, Any]:
    """
    Get the list of configured compliance reports from NSO.
    
    Returns:
        Dict containing compliance reports or error information
    """
    client = get_nso_rest_client()
    response = client.get("tailf-ncs:compliance/reports/report")
    
    if response.ok:
        return {"success": True, "data": response.json}
    else:
        logger.error("Failed to get compliance reports: %s", response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def redeploy_service(service_type: str, service_instance: str) -> Dict[str, Any]:
    """
    Redeploy a service in NSO.
    
    Args:
        service_type: The service type (e.g., "loopback-tunisie")
        service_instance: The service instance name (e.g., "TEST-Loopback")
        
    Returns:
        Dict containing redeploy result or error information
    """
    client = get_nso_rest_client()
    
    # Correct path format: tailf-ncs:services/{service-type}:{service-type}={instance}/re-deploy
    # Example: tailf-ncs:services/loopback-tunisie:loopback-tunisie=TEST-Loopback/re-deploy
    service_path = f"tailf-ncs:services/{service_type}:{service_type}={service_instance}/re-deploy"
    
    logger.info(f"Re-deploying service at path: {service_path}")
    response = client.post(service_path)
    
    if response.ok:
        logger.info("Successfully redeployed service: %s/%s", service_type, service_instance)
        return {"success": True, "data": response.json, "message": f"Redeployed {service_type}/{service_instance}"}
    else:
        logger.error("Failed to redeploy service %s/%s: %s", service_type, service_instance, response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def apply_compliance_template(device_name: str, template_name: str) -> Dict[str, Any]:
    """
    Apply a device template to bring a device into compliance.
    
    NOTE: NSO compliance templates are for CHECKING compliance, not applying config.
    To fix compliance violations, we apply a DEVICE TEMPLATE with the correct config.
    
    Args:
        device_name: Name of the device
        template_name: Name of the device template to apply
        
    Returns:
        Dict containing result or error information
    """
    client = get_nso_rest_client()
    
    # NSO device templates are applied via the data endpoint with XML payload
    # Path: /restconf/data/tailf-ncs:devices/device={device}/apply-template/
    base_url = client._base_url
    
    import requests
    
    url = f"{base_url}/tailf-ncs:devices/device={device_name}/apply-template/"
    
    # Use XML payload format
    payload = f"<input>\r\n    <template-name>{template_name}</template-name>\r\n</input>"
    
    response = requests.post(
        url,
        data=payload,
        auth=client.session.auth,
        headers={
            'Content-Type': 'application/yang-data+xml',
            'Accept': 'application/yang-data+xml'
        }
    )
    
    if response.ok:
        logger.info("Successfully applied template %s to device %s", template_name, device_name)
        return {"success": True, "data": response.text if response.text else None, "message": f"Applied {template_name} to {device_name}"}
    else:
        logger.error("Failed to apply template %s to %s: %s (status: %d)", template_name, device_name, response.text, response.status_code)
        return {"success": False, "error": response.text, "status_code": response.status_code}


def get_device_templates() -> Dict[str, Any]:
    """
    Get the list of available device templates from NSO.
    
    Device templates are used to apply configuration to devices.
    
    Returns:
        Dict containing device templates list or error information
    """
    client = get_nso_rest_client()
    response = client.get("tailf-ncs:devices/template")
    
    if response.ok:
        templates = response.json.get("tailf-ncs:template", [])
        template_names = [t.get("name") for t in templates if t.get("name")]
        logger.info("Found %d device templates: %s", len(template_names), template_names)
        return {"success": True, "templates": template_names, "count": len(template_names)}
    else:
        logger.error("Failed to get device templates: %s", response.text)
        return {"success": False, "error": response.text, "status_code": response.status_code}
