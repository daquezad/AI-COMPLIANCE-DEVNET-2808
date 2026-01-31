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
from agents.compliance.tools.nso_tools import get_nso_report_details, trigger_nso_compliance_report

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
    summary: Optional[str] = Field(default=None, description="Executive summary from LLM analysis")
    remediation_plan: List[RemediationItem] = Field(default_factory=list, description="List of remediation items")
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
        - 'analyzer' if trigger_nso_compliance_report was called AND returned success
        - 'chatbot' for other tool calls or failed report execution
        """
        # Check if the last tool message contains a valid report result
        for msg in reversed(state.messages):
            if isinstance(msg, ToolMessage):
                try:
                    content = msg.content
                    if isinstance(content, str) and 'report_id' in content:
                        # Parse the tool result to extract report_id
                        import ast
                        result = ast.literal_eval(content)
                        
                        # Only route to analyzer if:
                        # 1. Tool execution was successful
                        # 2. report_id is present and valid
                        # 3. Analysis hasn't been completed yet
                        if result.get('success') == True and result.get('report_id') and not state.analysis_complete:
                            logger.info(f"Routing to analyzer - valid report_id: {result.get('report_id')}")
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
        Fetches report details using report_id (extracted from tool message)
        and uses LLM with structured output to analyze the compliance data.
        """
        # Extract report_id from the tool message
        report_id = state.report_id
        if not report_id:
            for msg in reversed(state.messages):
                if isinstance(msg, ToolMessage):
                    try:
                        import ast
                        result = ast.literal_eval(msg.content)
                        if result.get('report_id'):
                            report_id = result.get('report_id')
                            break
                    except:
                        pass
        
        if not report_id:
            return {
                "messages": [AIMessage(content="⚠️ No report ID found. Please trigger a compliance report first.")],
                "analysis_complete": False
            }
        
        logger.info(f"Analyzer: Processing report ID: {report_id}")
        
        try:
            # Fetch the report details using the NSO tool
            report_result = get_nso_report_details.invoke({"report_id": report_id})
            
            if not report_result.get('success'):
                return {
                    "messages": [AIMessage(content=f"⚠️ Failed to fetch report: {report_result.get('error')}")],
                    "analysis_complete": False
                }
            
            report_data = report_result.get('report', {})
            report_json = json.dumps(report_data, indent=2)
            
            # Use LLM with structured output to analyze the report
            analyzer_llm = self.llm.with_structured_output(AnalysisResult)
            
            analysis_prompt = ANALYZER_PROMPT.format(report_data=report_json)
            analysis_result = await analyzer_llm.ainvoke([
                SystemMessage(content=analysis_prompt)
            ])
            
            # Convert analysis result to remediation items with proper status
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
            
            logger.info(f"Analyzer: Found {len(remediation_plan)} remediation items")
            
            return {
                "report_id": report_id,
                "summary": analysis_result.summary,
                "remediation_plan": remediation_plan,
                "analysis_complete": True,
                "messages": [AIMessage(content=f"🔍 **Analysis Complete**\n\n**Devices:** {analysis_result.total_devices} total, {analysis_result.non_compliant_devices} non-compliant\n\nFound **{len(remediation_plan)}** remediation items. Building plan...")]
            }
            
        except Exception as e:
            logger.error(f"Analyzer error: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"⚠️ Analysis error: {str(e)}")],
                "analysis_complete": False
            }

    async def _planner_node(self, state: GraphState) -> Dict[str, Any]:
        """
        Builds the remediation plan table and handles user interaction.
        Uses state.summary and state.remediation_plan to present options.
        """
        logger.info("Planner: Building remediation plan")
        
        # Build the Markdown table from remediation_plan
        if state.remediation_plan and state.analysis_complete:
            table_rows = []
            for item in state.remediation_plan:
                critical_marker = "🚨 Yes" if item.critical else "⚪ No"
                table_rows.append(
                    f"| {item.id} | {critical_marker} | {item.action} | {item.target} | {item.details} | {item.schedule} | [{item.status}] |"
                )
            
            table = """
**📋 Remediation Selection Table:**

| # | Critical | Action | Target | Details | Schedule / Frequency | Status |
|---|----------|--------|--------|---------|----------------------|--------|
""" + "\n".join(table_rows)

            planner_context = f"""
**Executive Summary:** {state.summary}

{table}

---
🎯 **Next Steps:**
1. Review the items above and approve the ones you want to execute.
2. Specify a schedule: **Immediate**, specific time (e.g., "2026-02-01 02:00 UTC"), or frequency (e.g., "Weekly Mon 02:00").
3. Say "Approve #1, #2" or "Approve all" to proceed.
"""
        else:
            planner_context = state.summary or "Analysis pending..."

        # Create the system message with context
        sys_msg = SystemMessage(content=SYSTEM_PROMPT)
        
        # Add context about current state
        context_msg = SystemMessage(content=f"""
CURRENT ANALYSIS STATE:
- Report ID: {state.report_id}
- Summary: {state.summary or 'Not yet analyzed'}
- Remediation Items: {len(state.remediation_plan)} items
- Analysis Complete: {state.analysis_complete}

Present the following to the user:
{planner_context}
""")

        try:
            response = await self.llm_with_tools.ainvoke([sys_msg, context_msg] + state.messages)
            return {"messages": [response]}
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