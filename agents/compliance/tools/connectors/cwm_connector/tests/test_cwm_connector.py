#!/usr/bin/env python3
"""
Test script for CWM (Crosswork Workflow Manager) Connector functions.

Run this script to test connectivity and API calls to CWM:
    PYTHONPATH=. python agents/compliance/tools/connectors/cwm_connector/tests/test_cwm_connector.py
    uv run python agents/compliance/tools/connectors/cwm_connector/tests/test_cwm_connector.py --execute --create-job
    """
import sys
import json


def test_list_workflows():
    """Test listing all CWM workflows."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import list_cwm_workflows
    
    print("=" * 60)
    print("1. Testing list_cwm_workflows()")
    print("=" * 60)
    
    result = list_cwm_workflows()
    
    if result.get("success"):
        print("✅ SUCCESS: Retrieved workflows list")
        workflows = result.get("workflows", [])
        print(f"   Found {len(workflows) if isinstance(workflows, list) else 'N/A'} workflows")
        
        # Show workflow IDs and names for easy reference
        if isinstance(workflows, list) and workflows:
            print("\n   Available workflows:")
            print("   " + "-" * 50)
            for wf in workflows[:10]:  # Show first 10
                wf_id = wf.get("id", wf.get("workflowId", "N/A"))
                wf_name = wf.get("name", wf.get("workflowName", "N/A"))
                wf_version = wf.get("version", wf.get("workflowVersion", ""))
                print(f"   • {wf_name} (v{wf_version})")
                print(f"     ID: {wf_id}")
            if len(workflows) > 10:
                print(f"   ... and {len(workflows) - 10} more")
            print("   " + "-" * 50)
        
        print(f"\n   Full response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        if len(json.dumps(result)) > 1500:
            print("   ... [truncated]")
        return True, workflows
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False, []


def test_get_workflow(workflow_id: str):
    """Test getting a specific workflow by ID."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import get_cwm_workflow
    
    print("\n" + "=" * 60)
    print(f"2. Testing get_cwm_workflow('{workflow_id}')")
    print("=" * 60)
    
    result = get_cwm_workflow(workflow_id)
    
    if result.get("success"):
        print("✅ SUCCESS: Retrieved workflow details")
        workflow = result.get("workflow", {})
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        if len(json.dumps(result)) > 1500:
            print("   ... [truncated]")
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_execute_workflow(workflow_id: str, inputs: dict = None):
    """Test executing a workflow (use with caution!)."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import execute_cwm_workflow
    
    print("\n" + "=" * 60)
    print(f"3. Testing execute_cwm_workflow('{workflow_id}')")
    print("=" * 60)
    
    if inputs:
        print(f"   Inputs: {json.dumps(inputs)}")
    
    # Safety prompt
    confirm = input("\n⚠️  This will EXECUTE a workflow. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped execution test.")
        return None
    
    result = execute_cwm_workflow(workflow_id, inputs)
    
    if result.get("success"):
        print("✅ SUCCESS: Workflow execution started")
        print(f"   Execution ID: {result.get('execution_id')}")
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_query_inventory():
    """Test querying inventory nodes."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import query_inventory_nodes
    
    print("\n" + "=" * 60)
    print("4. Testing query_inventory_nodes()")
    print("=" * 60)
    
    result = query_inventory_nodes()
    
    if result.get("error"):
        print(f"❌ FAILED: {result.get('error')}")
        return False
    else:
        print("✅ SUCCESS: Retrieved inventory nodes")
        print(f"   Total count: {result.get('total_count', 'N/A')}")
        print(f"   Result count: {result.get('result_count', 'N/A')}")
        data = result.get("data", [])
        print(f"   Data items: {len(data) if isinstance(data, list) else 'N/A'}")
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        if len(json.dumps(result, default=str)) > 1500:
            print("   ... [truncated]")
        return True


def test_create_job(job_name: str, workflow_name: str, workflow_version: str, data: dict = None, tags: list = None):
    """Test creating a CWM job."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import create_cwm_job
    
    print("\n" + "=" * 60)
    print(f"5. Testing create_cwm_job()")
    print("=" * 60)
    print(f"   Job Name: {job_name}")
    print(f"   Workflow: {workflow_name} v{workflow_version}")
    if data:
        print(f"   Data: {json.dumps(data)}")
    if tags:
        print(f"   Tags: {tags}")
    
    # Safety prompt
    confirm = input("\n⚠️  This will CREATE a job in CWM. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped job creation test.")
        return None
    
    result = create_cwm_job(
        job_name=job_name,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        data=data,
        tags=tags
    )
    
    if result.get("success"):
        print("✅ SUCCESS: Job created")
        print(f"   Job ID: {result.get('job_id')}")
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_schedule_workflow(
    schedule_id: str,
    workflow_name: str,
    workflow_version: str,
    job_name: str,
    cron_expressions: list,
    timezone: str = "UTC",
    tags: list = None,
    note: str = None
):
    """Test scheduling a CWM workflow."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import schedule_cwm_workflow
    
    print("\n" + "=" * 60)
    print(f"6. Testing schedule_cwm_workflow()")
    print("=" * 60)
    print(f"   Schedule ID: {schedule_id}")
    print(f"   Workflow: {workflow_name} v{workflow_version}")
    print(f"   Job Name: {job_name}")
    print(f"   Cron: {cron_expressions}")
    print(f"   Timezone: {timezone}")
    if tags:
        print(f"   Tags: {tags}")
    if note:
        print(f"   Note: {note}")
    
    # Safety prompt
    confirm = input("\n⚠️  This will CREATE a schedule in CWM. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped schedule creation test.")
        return None
    
    result = schedule_cwm_workflow(
        schedule_id=schedule_id,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        job_name=job_name,
        cron_expressions=cron_expressions,
        timezone=timezone,
        tags=tags,
        note=note
    )
    
    if result.get("success"):
        print("✅ SUCCESS: Schedule created")
        print(f"   Schedule ID: {result.get('schedule_id')}")
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_connection():
    """Test basic connection to CWM."""
    from config.config import CWM_HOST, CWM_PORT, CWM_USERNAME
    
    print("=" * 60)
    print("CWM Connector Test Suite")
    print("=" * 60)
    print(f"Host: {CWM_HOST}")
    print(f"Port: {CWM_PORT}")
    print(f"Username: {CWM_USERNAME}")
    print("=" * 60)


if __name__ == "__main__":
    # Parse command line arguments
    workflow_id = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    
    # Test connection info
    test_connection()
    
    # Test 1: List workflows
    list_success, workflows = test_list_workflows()
    
    # Test 2: Get specific workflow (if ID provided or auto-select first)
    if workflow_id:
        test_get_workflow(workflow_id)
    elif workflows and isinstance(workflows, list) and len(workflows) > 0:
        # Auto-select first workflow for testing
        first_wf = workflows[0]
        auto_id = first_wf.get("id", first_wf.get("workflowId"))
        if auto_id:
            print(f"\n💡 Auto-selecting first workflow: {auto_id}")
            test_get_workflow(auto_id)
        else:
            print("\n⚠️  Could not extract workflow ID from first workflow")
    else:
        print("\n⚠️  Skipping get_cwm_workflow test (no workflow_id provided)")
        print("   Usage: python test_cwm_connector.py <workflow_id>")
    
    # Test 3: Query inventory
    test_query_inventory()
    
    # Test 4: Execute workflow (optional, requires confirmation)
    if workflow_id and "--execute" in sys.argv:
        test_execute_workflow(workflow_id)
    
    # Test 5: Create job (optional, requires --create-job flag)
    if "--create-job" in sys.argv:
        # Example job creation - customize as needed
        test_create_job(
            job_name="test API job",
            workflow_name="1.0",
            workflow_version="1.0",
            data={},
            tags=[ "AI-COMPLIANCE","daquezad","test"]
        )
    else:
        print("\n⚠️  Skipping create_cwm_job test (use --create-job flag to enable)")
    
    # Test 6: Schedule workflow (optional, requires --schedule flag)
    if "--schedule" in sys.argv:
        import uuid
        unique_id = f"ai-compliance-schedule-{uuid.uuid4().hex[:8]}"
        test_schedule_workflow(
            schedule_id=unique_id,
            workflow_name="1.0",
            workflow_version="1.0",
            job_name="exampleJob-daily",
            cron_expressions=["0 0 6 2 *"],  # At 6:00 AM on day 2 of the month
            timezone="UTC",
            tags=["devnet", "ai", "daquezad"],
            note="Daily run of example workflow"
        )
    else:
        print("\n⚠️  Skipping schedule_cwm_workflow test (use --schedule flag to enable)")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)
