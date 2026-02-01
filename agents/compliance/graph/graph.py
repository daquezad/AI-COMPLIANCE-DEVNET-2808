import logging
import json
from typing import Annotated, Dict, Any, List, Union, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

# Mocking/Importing based on your environment
from ioa_observe.sdk.decorators import agent, graph
from common.llm import get_llm
from agents.prompts.prompts import SYSTEM_PROMPT, ANALYZER_PROMPT
from agents.compliance.graph.models import RemediationItem, AnalysisResult
from agents.compliance.tools.lc_tools_list import tools
from agents.compliance.tools.nso_lc_tools import get_nso_report_details, trigger_nso_compliance_report
from agents.compliance.tools.connectors.nso_connector_jsonrpc.report_downloader import (
    download_and_preprocess_report,
    preprocess_compliance_report
)

logger = logging.getLogger("devnet.compliance.chat.graph")
logging.basicConfig(level=logging.INFO)

# ---------------- GRAPH STATE ----------------

class GraphState(BaseModel):
    """
    Represents the state of our conversation and analysis flow.
    Uses Annotated with add_messages to handle history merging.
    """
    messages: Annotated[list, add_messages] = []
    report_id: Optional[str] = Field(default=None, description="The NSO compliance report ID")
    report_url: Optional[str] = Field(default=None, description="URL to download the compliance report")
    report_file_path: Optional[str] = Field(default=None, description="Path to temp file containing preprocessed report")
    report_content: Optional[str] = Field(default=None, description="Downloaded and preprocessed report content")
    summary: Optional[str] = Field(default=None, description="Executive summary from LLM analysis")
    remediation_plan: List[RemediationItem] = Field(default_factory=list, description="List of remediation items")
    remediation_plan_json: Optional[str] = Field(default=None, description="JSON string of approved remediation actions for execution")
    pending_confirmation: bool = Field(default=False, description="Flag indicating user confirmation is pending before execution")
    analysis_complete: bool = Field(default=False, description="Flag indicating analysis is complete")



# ---------------- AGENT ----------------

@agent(name="compliance_agent")
class ComplianceGraph:
    """
    A multi-step compliance analysis agent with:
    - Report Generator: Triggers NSO compliance reports
    - Analyzer: Parses report data and identifies violations
    - Planner: Creates remediation plan with Human-in-the-loop approval
    - Tools: Execute NSO/CWM operations
    """

    def __init__(self):
        # Initialize LLM with streaming enabled
        self.llm = get_llm(streaming=True)
        
        # 1. Define Tools
        self.tools = tools 
        
        # 2. Bind tools to the LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

        self.graph = self.build_graph()

    @graph(name="compliance_graph")
    def build_graph(self) -> CompiledStateGraph:
        """
        Constructs the compliance analysis graph:
        START -> chatbot <-> tools
                    |
                    v (after trigger_nso_compliance_report tool)
                 analyzer -> planner <-> tools
        """
        workflow = StateGraph(GraphState)

        # Add all functional nodes
        workflow.add_node("chatbot", self._chatbot_node)
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("planner", self._planner_node)
        
        # Add ToolNode if tools exist
        if self.tools:
            workflow.add_node("tools", ToolNode(self.tools))

        # Entry point is chatbot
        workflow.add_edge(START, "chatbot")
        
        # Chatbot routes to: tools or END
        workflow.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        
        # After tools, check if we should go to analyzer or back to chatbot
        if self.tools:
            workflow.add_conditional_edges(
                "tools",
                self._route_after_tools,
                {
                    "analyzer": "analyzer",
                    "chatbot": "chatbot"
                }
            )

        # Analyzer goes to planner
        workflow.add_edge("analyzer", "planner")
        
        # Planner can call tools or end
        workflow.add_conditional_edges(
            "planner",
            tools_condition,
        )

        # Persistence for Human-in-the-loop
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    def _route_after_tools(self, state: GraphState) -> str:
        """
        Routes after tool execution:
        - 'analyzer' if trigger_nso_compliance_report or download_nso_compliance_report was called AND returned success
        - 'chatbot' for other tool calls or failed report execution
        """
        # Check if the last tool message contains a valid report result
        for msg in reversed(state.messages):
            if isinstance(msg, ToolMessage):
                try:
                    content = msg.content
                    # Check for report_id OR report_url OR content (from download tool)
                    if isinstance(content, str) and ('report_id' in content or 'report_url' in content or 'filepath' in content):
                        # Parse the tool result
                        import ast
                        result = ast.literal_eval(content)
                        
                        # Only route to analyzer if:
                        # 1. Tool execution was successful
                        # 2. report_id, report_url, or content is present
                        # 3. Analysis hasn't been completed yet
                        has_report_data = result.get('report_id') or result.get('report_url') or result.get('content')
                        if result.get('success') == True and has_report_data and not state.analysis_complete:
                            logger.info(f"Routing to analyzer - report_id: {result.get('report_id')}, has_content: {bool(result.get('content'))}")
                            return "analyzer"
                        elif result.get('success') == False:
                            logger.warning(f"Report execution failed: {result.get('error', 'Unknown error')}")
                            return "chatbot"
                except Exception as e:
                    logger.error(f"Error parsing tool result: {e}")
                    pass
                break
        
        return "chatbot"

    # ---------------- NODES ----------------

    async def _chatbot_node(self, state: GraphState) -> Dict[str, Any]:
        """
        Main chatbot node for general conversation and initial request handling.
        """
        sys_msg = SystemMessage(content=SYSTEM_PROMPT)

        try:
            response = await self.llm_with_tools.ainvoke([sys_msg] + state.messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Chatbot node error: {e}", exc_info=True)
            return {"messages": [AIMessage(content="⚠️ I encountered an error processing your request.")]}

    async def _analyzer_node(self, state: GraphState) -> Dict[str, Any]:
        """
        Analyzes compliance reports using LLM with structured output.
        
        This node can be triggered in two ways:
        1. After run_nso_compliance_report tool execution (extracts report_id/URL from tool message)
        2. Directly by user request to analyze a specific report ID
        
        Workflow:
        1. Extract report_id/URL/file_path from tool message or state
        2. Read report content from file (if file_path available) or download
        3. Pass preprocessed content to LLM for structured analysis
        4. Generate remediation plan and forward to planner node
        """
        # Extract report_id and report_url from the tool message or state
        report_id = state.report_id
        report_url = state.report_url
        report_content = state.report_content
        report_file_path = state.report_file_path
        
        # Try to extract from tool messages if not in state
        if not report_id or not report_url or not report_file_path:
            for msg in reversed(state.messages):
                if isinstance(msg, ToolMessage):
                    try:
                        import ast
                        result = ast.literal_eval(msg.content)
                        if result.get('report_id') and not report_id:
                            report_id = result.get('report_id')
                        if result.get('report_url') and not report_url:
                            report_url = result.get('report_url')
                        if result.get('file_path') and not report_file_path:
                            report_file_path = result.get('file_path')
                        if result.get('content') and not report_content:
                            report_content = result.get('content')
                        if report_id or report_url or report_file_path:
                            break
                    except:
                        pass
        
        # Also check user messages for explicit report ID requests
        if not report_id:
            for msg in reversed(state.messages):
                if isinstance(msg, HumanMessage):
                    content = msg.content.lower()
                    # Look for patterns like "analyze report 5" or "report id 5"
                    import re
                    match = re.search(r'(?:report\s*(?:id)?|analyze)\s*[:#]?\s*(\d+)', content)
                    if match:
                        report_id = match.group(1)
                        logger.info(f"Extracted report_id from user message: {report_id}")
                        break
        
        if not report_id and not report_url and not report_content and not report_file_path:
            return {
                "messages": [AIMessage(content="⚠️ No report ID or URL found. Please either:\n1. Run a compliance report first using `run_nso_compliance_report`\n2. Specify a report ID to analyze (e.g., 'analyze report 5')")],
                "analysis_complete": False
            }
        
        logger.info(f"Analyzer: Processing report ID: {report_id}, URL: {report_url}, File: {report_file_path}")
        
        try:
            # Step 1: Get report content - prioritize reading from file
            preprocessed_content = None
            
            # First, try to read from file_path (most efficient - no token transfer)
            if report_file_path:
                import os
                if os.path.exists(report_file_path):
                    logger.info(f"Reading report content from file: {report_file_path}")
                    with open(report_file_path, 'r', encoding='utf-8') as f:
                        preprocessed_content = f.read()
                    logger.info(f"Loaded report from file: {len(preprocessed_content)} chars")
                else:
                    logger.warning(f"Report file not found: {report_file_path}")
            
            # If no file content, try state content
            if not preprocessed_content and report_content:
                preprocessed_content = preprocess_compliance_report(report_content)
            
            # If still no content, download it
            if not preprocessed_content:
                logger.info(f"Downloading and preprocessing report from NSO...")
                
                # Use URL if available, otherwise use report_id
                download_target = report_url if report_url else report_id
                
                # download_and_preprocess_report handles both download AND preprocessing (HTML->text, removes Details section)
                filepath, preprocessed_content = download_and_preprocess_report(download_target)
                
                if not preprocessed_content:
                    # Fallback to the old method if download fails
                    logger.warning("Download failed, falling back to get_nso_report_details")
                    report_result = get_nso_report_details.invoke({"report_id": report_id})
                    
                    if not report_result.get('success'):
                        return {
                            "messages": [AIMessage(content=f"⚠️ Failed to fetch report: {report_result.get('error')}")],
                            "analysis_complete": False
                        }
                    
                    report_data = report_result.get('report', {})
                    preprocessed_content = json.dumps(report_data, indent=2)
                else:
                    logger.info(f"Report downloaded and preprocessed successfully. File: {filepath}, Content length: {len(preprocessed_content)} chars")
            else:
                # Content already exists in state, preprocess it
                preprocessed_content = preprocess_compliance_report(report_content)
            
            # Step 2: Use LLM with structured output to analyze the preprocessed report
            analyzer_llm = self.llm.with_structured_output(AnalysisResult)
            
            analysis_prompt = ANALYZER_PROMPT.format(report_data=preprocessed_content)
            logger.info(f"Sending preprocessed report to LLM for analysis ({len(preprocessed_content)} chars)")
            
            analysis_result = await analyzer_llm.ainvoke([
                SystemMessage(content=analysis_prompt)
            ])
            
            # Step 3: Convert analysis result to remediation items with proper status
            remediation_plan = []
            for item in analysis_result.remediation_items:
                remediation_item = RemediationItem(
                    id=item.id,
                    critical=item.critical,
                    action=item.action,
                    target=item.target,
                    details=item.details,
                    schedule="Immediate" if item.critical else "Scheduled",
                    status="Pending 🟡"
                )
                remediation_plan.append(remediation_item)
            
            logger.info(f"Analyzer: Found {len(remediation_plan)} remediation items. Forwarding to planner node.")
            
            # Step 4: Return state updates to be passed to planner node
            return {
                "report_id": report_id,
                "report_url": report_url,
                "report_file_path": report_file_path,
                "report_content": preprocessed_content,
                "summary": analysis_result.summary,
                "remediation_plan": remediation_plan,
                "analysis_complete": True,
                "messages": [AIMessage(content=f"🔍 **Analysis Complete**\n\n**Devices:** {analysis_result.total_devices} total, {analysis_result.non_compliant_devices} non-compliant\n\nFound **{len(remediation_plan)}** remediation items. Building remediation plan...")]
            }
            
        except Exception as e:
            logger.error(f"Analyzer error: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"⚠️ Analysis error: {str(e)}")],
                "analysis_complete": False
            }

    async def _planner_node(self, state: GraphState) -> Dict[str, Any]:
        """
        Builds the remediation plan table, generates remediation_plan_json,
        and requests user confirmation before execution.
        
        Flow:
        1. Display remediation table to user
        2. Generate remediation_plan_json from approved items
        3. Ask user: Execute NOW or SCHEDULE for later?
        4. Wait for confirmation before calling execute_remediation_plan or schedule_remediation_workflow
        """
        logger.info("Planner: Building remediation plan")
        
        # Build the Markdown table and JSON from remediation_plan
        if state.remediation_plan and state.analysis_complete:
            table_rows = []
            remediation_actions = []
            
            for item in state.remediation_plan:
                critical_marker = "🚨 Yes" if item.critical else "⚪ No"
                table_rows.append(
                    f"| {item.id} | {critical_marker} | {item.action} | {item.target} | {item.details} | {item.schedule} | [{item.status}] |"
                )
                
                # Build the JSON action for each item
                action_json = {
                    "id": item.id,
                    "action": item.action,
                    "critical": item.critical
                }
                
                # Add action-specific fields based on action type
                if item.action == "sync-to":
                    action_json["target"] = {"device_name": item.target}
                elif item.action == "re-deploy":
                    # Parse service info from details (format: "service_type/service_instance")
                    if "/" in item.details:
                        svc_type, svc_instance = item.details.split("/", 1)
                        action_json["service_type"] = svc_type.strip()
                        action_json["service_instance"] = svc_instance.strip()
                    else:
                        action_json["service_type"] = item.details
                        action_json["service_instance"] = item.target
                elif item.action == "apply-template":
                    action_json["template_name"] = item.details
                    action_json["target"] = {"device_name": item.target}
                
                remediation_actions.append(action_json)
            
            # Generate the JSON string
            remediation_plan_json = json.dumps(remediation_actions, indent=2)
            
            table = """
**📋 Remediation Plan:**

| # | Critical | Action | Target | Details | Schedule | Status |
|---|----------|--------|--------|---------|----------|--------|
""" + "\n".join(table_rows)

            planner_context = f"""
**Executive Summary:** {state.summary}

{table}

---
⚠️ **CONFIRMATION REQUIRED**

I have prepared **{len(remediation_actions)}** remediation action(s). Before executing, please confirm:

**Options:**
1. **Execute NOW** - Say "execute now" or "run immediately" to execute all actions right away
2. **Schedule for later** - Say "schedule for YYYY-MM-DD HH:MM" to schedule execution at a specific time
3. **Modify selection** - Say "remove #1, #3" to exclude specific items before execution

🔒 **No actions will be executed without your explicit confirmation.**
"""
            
            logger.info(f"Planner: Generated remediation_plan_json with {len(remediation_actions)} actions")
        else:
            planner_context = state.summary or "Analysis pending..."
            remediation_plan_json = None

        # Create the system message with context
        sys_msg = SystemMessage(content=SYSTEM_PROMPT)
        
        # Add context about current state including the JSON for tools
        context_msg = SystemMessage(content=f"""
CURRENT ANALYSIS STATE:
- Report ID: {state.report_id}
- Summary: {state.summary or 'Not yet analyzed'}
- Remediation Items: {len(state.remediation_plan)} items
- Analysis Complete: {state.analysis_complete}
- Pending Confirmation: True (awaiting user approval)

REMEDIATION PLAN JSON (use this with execute_remediation_plan or schedule_remediation_workflow):
```json
{remediation_plan_json}
```

IMPORTANT INSTRUCTIONS:
1. Present the remediation table to the user
2. WAIT for explicit user confirmation before executing
3. If user says "execute now" -> use execute_remediation_plan tool with the JSON above
4. If user says "schedule for <datetime>" -> use schedule_remediation_workflow tool
5. NEVER execute without confirmation

Present the following to the user:
{planner_context}
""")

        try:
            response = await self.llm_with_tools.ainvoke([sys_msg, context_msg] + state.messages)
            return {
                "messages": [response],
                "remediation_plan_json": remediation_plan_json,
                "pending_confirmation": True
            }
        except Exception as e:
            logger.error(f"Planner node error: {e}", exc_info=True)
            return {"messages": [AIMessage(content=f"⚠️ Planner error: {str(e)}")]}

    # ---------------- SERVE HELPERS ----------------

    async def serve(self, prompt: str, thread_id: str = "default") -> str:
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=prompt)]}
        
        try:
            result = await self.graph.ainvoke(input_data, config)
            messages = result.get("messages", [])
            if messages and isinstance(messages[-1], AIMessage):
                return messages[-1].content
            return "No response."
        except Exception as e:
            return f"Error: {str(e)}"

    async def streaming_serve(self, prompt: str, thread_id: str = "default"):
        """
        Streams response chunks to the frontend.
        Tool calls and node transitions are logged but not sent to the user.
        """
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=prompt)]}
        frontend_node = "compliance-chat"

        async for event in self.graph.astream_events(input_data, config, version="v2"):
            event_type = event.get("event")
            
            # 1. Handle Text Streaming - Only stream actual LLM content to user
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {
                        "node": frontend_node,
                        "status": "streaming",
                        "message": chunk.content 
                    }
            
            # 2. Log Tool Execution (not sent to frontend)
            elif event_type == "on_tool_start":
                tool_name = event.get("name")
                logger.info(f"🔧 Calling tool: {tool_name}")
            
            # 3. Log Node Transitions (not sent to frontend)
            elif event_type == "on_chain_start":
                node_name = event.get("name")
                if node_name == "analyzer":
                    logger.info("🔍 Analyzing compliance data...")
                elif node_name == "planner":
                    logger.info("📋 Building remediation plan...")
                elif node_name == "chatbot":
                    logger.info("💬 Processing in chatbot...")

            elif event_type == "on_chain_end":
                node_name = event.get("name")
                if node_name in ["analyzer", "planner", "chatbot"]:
                    logger.info(f"✅ {node_name} completed")