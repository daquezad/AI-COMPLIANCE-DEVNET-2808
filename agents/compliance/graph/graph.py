import logging
import uuid
import json
from typing import Annotated, Optional, Dict, Any, List, Union

from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

# Mocking/Importing based on original context
from ioa_observe.sdk.decorators import agent, graph
from common.llm import get_llm

logger = logging.getLogger("devnet.provisioning.chat.graph")
logging.basicConfig(level=logging.INFO)

# ---------------- HELPER FUNCTIONS ----------------

def filter_tool_messages(messages: list) -> list:
    """
    Prevents 'tool without tool_calls' errors by ensuring ToolMessages 
    only exist if preceded by an AIMessage with tool_calls.
    """
    return [msg for msg in messages if not isinstance(msg, ToolMessage)]

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
    A simplified Human-in-the-Loop chat agent for network provisioning.
    """

    def __init__(self):
        self.llm = get_llm(streaming=True)
        self.graph = self.build_graph()

    @graph(name="chat_graph")
    def build_graph(self) -> CompiledStateGraph:
        """
        Constructs a simple stateful chat graph with memory persistence.
        """
        workflow = StateGraph(GraphState)

        # Define the single functional node
        workflow.add_node("chatbot", self._chatbot_node)

        # Set simple linear flow
        workflow.set_entry_point("chatbot")
        workflow.add_edge("chatbot", END)

        # MemorySaver enables Human-in-the-loop by persisting state via thread_id
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    # ---------------- NODES ----------------

    async def _chatbot_node(self, state: GraphState) -> Dict[str, Any]:
        """
        Processes the conversation history and generates an LLM response.
        """
        # Filter messages to ensure LLM compatibility
        clean_messages = filter_tool_messages(state.messages)
        
        # System prompt to define behavior
        sys_msg = SystemMessage(content=(
            "You are a Cisco Network Assistant. Help the user with provisioning tasks. "
            "Be concise, professional, and ask for clarification if requirements are missing."
            "Add a lot of emojis"
        ))

        try:
            # Invoke LLM with the full history
            response = await self.llm.ainvoke([sys_msg] + clean_messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Chatbot node error: {e}", exc_info=True)
            error_msg = AIMessage(content="I'm sorry, I encountered an internal error. Please try again.")
            return {"messages": [error_msg]}

    # ---------------- SERVE HELPERS ----------------

    async def serve(self, prompt: str, thread_id: str = "default") -> str:
        """
        Synchronous execution for a single turn in the conversation.
        """
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=prompt)]}
        
        try:
            result = await self.graph.ainvoke(input_data, config)
            messages = result.get("messages", [])
            
            if messages and isinstance(messages[-1], AIMessage):
                return messages[-1].content
            return "No response generated."
        except Exception as e:
            logger.error(f"Serve error: {e}")
            return f"Error: {str(e)}"

    async def streaming_serve(self, prompt: str, thread_id: str = "default"):
        """
        Streams the chatbot response token-by-token for better UX.
        """
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=prompt)]}
        
        # Frontend node mapping
        frontend_node = "provisioning-chat"

        async for event in self.graph.astream_events(input_data, config, version="v2"):
            event_type = event.get("event")
            
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {
                        "node": frontend_node,
                        "status": "streaming",
                        "message": chunk.content 
                    }
            
            elif event_type == "on_chain_start" and event.get("name") == "chatbot":
                yield {"node": frontend_node, "status": "start", "message": ""}
                
            elif event_type == "on_chain_end" and event.get("name") == "chatbot":
                yield {"node": frontend_node, "status": "end", "message": ""}