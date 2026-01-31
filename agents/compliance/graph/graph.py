import logging
import json
from typing import Annotated, Dict, Any, List, Union

from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

# Mocking/Importing based on your environment
from ioa_observe.sdk.decorators import agent, graph
from common.llm import get_llm
from agents.prompts.prompts import SYSTEM_PROMPT

# IMPORTANT: Import your actual tools here
# from agents.compliance.tools import compliance_tools 
# For this example, we'll assume a list named 'tools' exists
tools = [] # Replace with: from your_tool_module import tools

logger = logging.getLogger("devnet.compliance.chat.graph")
logging.basicConfig(level=logging.INFO)

# ---------------- GRAPH STATE ----------------

class GraphState(BaseModel):
    """
    Represents the state of our conversation.
    Uses Annotated with add_messages to handle history merging.
    """
    messages: Annotated[list, add_messages] = []

# ---------------- AGENT ----------------

@agent(name="compliance_agent")
class ComplianceGraph:
    """
    A Human-in-the-Loop chat agent with Tool-calling capabilities.
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

    @graph(name="chat_graph")
    def build_graph(self) -> CompiledStateGraph:
        """
        Constructs a stateful graph: Chatbot <-> Tools.
        """
        workflow = StateGraph(GraphState)

        # Add functional nodes
        workflow.add_node("chatbot", self._chatbot_node)
        
        # Add ToolNode if tools exist
        if self.tools:
            workflow.add_node("tools", ToolNode(self.tools))

        # Define Logic Flow
        workflow.add_edge(START, "chatbot")

        if self.tools:
            # If LLM calls a tool, go to 'tools' node, else END
            workflow.add_conditional_edges(
                "chatbot",
                tools_condition,
            )
            # After tool execution, go back to chatbot to summarize results
            workflow.add_edge("tools", "chatbot")
        else:
            workflow.add_edge("chatbot", END)

        # Persistence for Human-in-the-loop
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    # ---------------- NODES ----------------

    async def _chatbot_node(self, state: GraphState) -> Dict[str, Any]:
        """
        Processes conversation and decides next action (Response or Tool Call).
        """
        sys_msg = SystemMessage(content=(SYSTEM_PROMPT
        ))

        try:
            # Use the tool-bound LLM
            response = await self.llm_with_tools.ainvoke([sys_msg] + state.messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Chatbot node error: {e}", exc_info=True)
            return {"messages": [AIMessage(content="⚠️ I encountered an error processing your request.")]}

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
        Streams response chunks and tool execution status.
        """
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=prompt)]}
        frontend_node = "compliance-chat"

        async for event in self.graph.astream_events(input_data, config, version="v2"):
            event_type = event.get("event")
            
            # 1. Handle Text Streaming
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {
                        "node": frontend_node,
                        "status": "streaming",
                        "message": chunk.content 
                    }
            
            # 2. Handle Tool Execution Visibility
            elif event_type == "on_tool_start":
                tool_name = event.get("name")
                yield {
                    "node": "tools",
                    "status": "start",
                    "message": f"🔧 Calling tool: {tool_name}..."
                }

            elif event_type == "on_chain_start" and event.get("name") == "chatbot":
                yield {"node": frontend_node, "status": "start", "message": ""}
                
            elif event_type == "on_chain_end" and event.get("name") == "chatbot":
                yield {"node": frontend_node, "status": "end", "message": ""}