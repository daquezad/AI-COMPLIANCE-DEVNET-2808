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


def test_cancel_job_run(job_id: str, run_id: str):
    """Test cancelling a CWM job run."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import cancel_cwm_job_run
    
    print("\n" + "=" * 60)
    print(f"7. Testing cancel_cwm_job_run()")
    print("=" * 60)
    print(f"   Job ID: {job_id}")
    print(f"   Run ID: {run_id}")
    
    # Safety prompt
    confirm = input("\n⚠️  This will CANCEL a running job in CWM. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped job cancellation test.")
        return None
    
    result = cancel_cwm_job_run(job_id=job_id, run_id=run_id)
    
    if result.get("success"):
        print("✅ SUCCESS: Job run cancelled")
        print(f"   Job ID: {result.get('job_id')}")
        print(f"   Run ID: {result.get('run_id')}")
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_list_schedules(prefix_filter: str = "AI"):
    """Test listing CWM scheduled workflows."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import list_cwm_schedules
    
    print("\n" + "=" * 60)
    print(f"8. Testing list_cwm_schedules(prefix_filter='{prefix_filter}')")
    print("=" * 60)
    
    result = list_cwm_schedules(prefix_filter=prefix_filter)
    
    if result.get("success"):
        print("✅ SUCCESS: Retrieved schedules list")
        print(f"   Total schedules: {result.get('total_count')}")
        print(f"   Filtered (prefix='{prefix_filter}'): {result.get('filtered_count')}")
        
        schedules = result.get("schedules", [])
        if schedules:
            print("\n   Filtered Schedules:")
            print("   " + "-" * 50)
            for s in schedules:
                print(f"   • ID: {s.get('ID')}")
                print(f"     Note: {s.get('Note') or '(none)'}")
                print(f"     Paused: {s.get('Paused')}")
                next_times = s.get('NextActionTimes', [])
                if next_times:
                    print(f"     Next Run: {next_times[0]}")
                print()
            print("   " + "-" * 50)
        
        print(f"\n   Full response preview:")
        print(json.dumps(result, indent=2, default=str)[:2000])
        if len(json.dumps(result, default=str)) > 2000:
            print("   ... [truncated]")
        return True, schedules
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False, []


def test_delete_schedule(schedule_id: str):
    """Test deleting a CWM schedule (only if ID starts with 'AI')."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import delete_cwm_schedule
    
    print("\n" + "=" * 60)
    print(f"9. Testing delete_cwm_schedule('{schedule_id}')")
    print("=" * 60)
    
    # Check if ID starts with AI
    if not schedule_id.upper().startswith("AI"):
        print(f"   ⚠️  Schedule ID '{schedule_id}' does not start with 'AI'")
        print("   For safety, only AI-prefixed schedules can be deleted.")
        return False
    
    print(f"   Schedule ID: {schedule_id}")
    
    # Safety prompt
    confirm = input("\n⚠️  This will DELETE the schedule from CWM. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped schedule deletion test.")
        return None
    
    result = delete_cwm_schedule(schedule_id=schedule_id)
    
    if result.get("success"):
        print("✅ SUCCESS: Schedule deleted")
        print(f"   Deleted ID: {result.get('schedule_id')}")
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_schedule_compliance_audit(report_name: str, schedule_frequency: str, title: str = None):
    """Test scheduling a compliance audit."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import schedule_compliance_audit
    
    print("\n" + "=" * 60)
    print(f"10. Testing schedule_compliance_audit()")
    print("=" * 60)
    print(f"   Report Name: {report_name}")
    print(f"   Frequency: {schedule_frequency}")
    if title:
        print(f"   Title: {title}")
    
    # Validate frequency
    valid_frequencies = ["DAILY", "WEEKLY", "MONTHLY"]
    if schedule_frequency.upper() not in valid_frequencies:
        print(f"\n   ❌ Invalid frequency: {schedule_frequency}")
        print(f"   Must be one of: {valid_frequencies}")
        return False
    
    # Safety prompt
    confirm = input("\n⚠️  This will SCHEDULE a compliance audit in CWM. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped audit scheduling test.")
        return None
    
    result = schedule_compliance_audit(
        report_name=report_name,
        schedule_frequency=schedule_frequency,
        title=title,
        trigger_immediately=False
    )
    
    if result.get("success"):
        print("✅ SUCCESS: Compliance audit scheduled")
        print(f"   Schedule ID: {result.get('schedule_id')}")
        print(f"   Job Name: {result.get('job_name')}")
        print(f"   Cron Expression: {result.get('cron_expression')}")
        print(f"   Frequency: {result.get('schedule_frequency')}")
        print(f"\n   Response preview:")
        print(json.dumps(result, indent=2, default=str)[:1500])
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


def test_schedule_remediation(scheduled_datetime: str, description: str, devices: list = None):
    """Test scheduling a one-time remediation workflow."""
    from agents.compliance.tools.connectors.cwm_connector.api.cwm_requests import schedule_remediation_workflow
    
    print("\n" + "=" * 60)
    print(f"11. Testing schedule_remediation_workflow()")
    print("=" * 60)
    print(f"   Scheduled DateTime: {scheduled_datetime}")
    print(f"   Description: {description}")
    if devices:
        print(f"   Devices: {devices}")
    
    # Safety prompt
    confirm = input("\n⚠️  This will SCHEDULE a one-time remediation in CWM. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("   Skipped remediation scheduling test.")
        return None
    
    result = schedule_remediation_workflow(
        scheduled_datetime=scheduled_datetime,
        description=description,
        devices=devices
    )
    
    if result.get("success"):
        print("✅ SUCCESS: Remediation scheduled")
        print(f"   Schedule ID: {result.get('schedule_id')}")
        print(f"   Job Name: {result.get('job_name')}")
        print(f"   Scheduled Time: {result.get('scheduled_datetime')}")
        print(f"   Cron Expression: {result.get('cron_expression')}")
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
            workflow_name="FIX_Compliance_Remediation",
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
            workflow_name="AUDIT_Compliance_Report",
            workflow_version="1.0",
            job_name="exampleJob-daily",
            cron_expressions=["0 0 6 2 *"],  # At 6:00 AM on day 2 of the month
            timezone="UTC",
            tags=["DEVNET", "AI", "daquezad"],
            note="Daily run of example workflow"
        )
    else:
        print("\n⚠️  Skipping schedule_cwm_workflow test (use --schedule flag to enable)")
    
    # Test 7: Cancel job run (optional, requires --cancel flag with job_id and run_id)
    if "--cancel" in sys.argv:
        # Find job_id and run_id from command line args
        cancel_idx = sys.argv.index("--cancel")
        if len(sys.argv) > cancel_idx + 2:
            cancel_job_id = sys.argv[cancel_idx + 1]
            cancel_run_id = sys.argv[cancel_idx + 2]
            test_cancel_job_run(job_id=cancel_job_id, run_id=cancel_run_id)
        else:
            print("\n⚠️  --cancel requires job_id and run_id: --cancel <job_id> <run_id>")
    else:
        print("\n⚠️  Skipping cancel_cwm_job_run test (use --cancel <job_id> <run_id> to enable)")
    
    # Test 8: List schedules (optional, --list-schedules [prefix])
    if "--list-schedules" in sys.argv:
        # Check if a custom prefix was provided
        list_idx = sys.argv.index("--list-schedules")
        if len(sys.argv) > list_idx + 1 and not sys.argv[list_idx + 1].startswith("--"):
            prefix = sys.argv[list_idx + 1]
        else:
            prefix = "AI"  # Default to AI prefix
        test_list_schedules(prefix_filter=prefix)
    else:
        print("\n⚠️  Skipping list_cwm_schedules test (use --list-schedules [prefix] to enable)")
    
    # Test 9: Delete schedule (optional, --delete-schedule <schedule_id>)
    if "--delete-schedule" in sys.argv:
        del_idx = sys.argv.index("--delete-schedule")
        if len(sys.argv) > del_idx + 1 and not sys.argv[del_idx + 1].startswith("--"):
            del_schedule_id = sys.argv[del_idx + 1]
            test_delete_schedule(schedule_id=del_schedule_id)
        else:
            print("\n⚠️  --delete-schedule requires schedule_id: --delete-schedule <schedule_id>")
    else:
        print("\n⚠️  Skipping delete_cwm_schedule test (use --delete-schedule <schedule_id> to enable)")
    
    # Test 10: Schedule compliance audit (optional, --schedule-audit <report_name> <frequency>)
    if "--schedule-audit" in sys.argv:
        audit_idx = sys.argv.index("--schedule-audit")
        if len(sys.argv) > audit_idx + 2 and not sys.argv[audit_idx + 1].startswith("--"):
            audit_report_name = sys.argv[audit_idx + 1]
            audit_frequency = sys.argv[audit_idx + 2]
            # Optional title as third argument
            audit_title = None
            if len(sys.argv) > audit_idx + 3 and not sys.argv[audit_idx + 3].startswith("--"):
                audit_title = sys.argv[audit_idx + 3]
            test_schedule_compliance_audit(
                report_name=audit_report_name,
                schedule_frequency=audit_frequency,
                title=audit_title
            )
        else:
            print("\n⚠️  --schedule-audit requires report_name and frequency: --schedule-audit <report_name> <DAILY|WEEKLY|MONTHLY> [title]")
    else:
        print("\n⚠️  Skipping schedule_compliance_audit test (use --schedule-audit <report_name> <DAILY|WEEKLY|MONTHLY> to enable)")
    
    # Test 11: Schedule remediation (optional, --schedule-remediation <datetime> <description>)
    if "--schedule-remediation" in sys.argv:
        rem_idx = sys.argv.index("--schedule-remediation")
        if len(sys.argv) > rem_idx + 2 and not sys.argv[rem_idx + 1].startswith("--"):
            rem_datetime = sys.argv[rem_idx + 1]
            rem_description = sys.argv[rem_idx + 2]
            # Optional devices as third argument (comma-separated)
            rem_devices = None
            if len(sys.argv) > rem_idx + 3 and not sys.argv[rem_idx + 3].startswith("--"):
                rem_devices = [d.strip() for d in sys.argv[rem_idx + 3].split(",")]
            test_schedule_remediation(
                scheduled_datetime=rem_datetime,
                description=rem_description,
                devices=rem_devices
            )
        else:
            print("\n⚠️  --schedule-remediation requires datetime and description:")
            print("   --schedule-remediation '2026-02-15 10:30' 'Fix NTP config' [device1,device2]")
    else:
        print("\n⚠️  Skipping schedule_remediation_workflow test (use --schedule-remediation to enable)")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)
