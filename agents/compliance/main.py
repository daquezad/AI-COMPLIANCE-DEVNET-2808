# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi.responses import StreamingResponse

from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from ioa_observe.sdk.tracing import session_start


from agents.compliance.graph.graph import ComplianceGraph 
from agents.compliance.graph import shared 


from config.config import DEFAULT_MESSAGE_TRANSPORT, TRANSPORT_SERVER_ENDPOINT, COMPLIANCE_AGENT_PORT, COMPLIANCE_AGENT_IP
from config.logging_config import setup_logging

# -------------------- Logging --------------------
setup_logging()
logger = logging.getLogger("devnet.compliance.main")

# -------------------- Environment --------------------
load_dotenv()

# -------------------- Agntcy Factory --------------------
shared.set_factory(AgntcyFactory("devnet.compliance_agent", enable_tracing=False))

# -------------------- FastAPI --------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Graph --------------------
compliance_graph = ComplianceGraph()

# -------------------- Models --------------------
class PromptRequest(BaseModel):
    prompt: str
    thread_id: Optional[str] = "default_session" 

# -------------------- HTTP Endpoints --------------------
@app.post("/agent/prompt/stream")
async def handle_stream_prompt(request: PromptRequest):
    session_start()
    thread_id = request.thread_id

    async def stream_generator():
        try:
            async for chunk in compliance_graph.streaming_serve(
                request.prompt, 
                thread_id=thread_id
            ):
                # Extract message content
                message_content = chunk.get("message", "")
                node_id = chunk.get("node", "agent")
                status = chunk.get("status", "streaming")
                
                # Log for debugging (only log non-empty messages to avoid spam)
                # if message_content:
                #     logger.info(f"[STREAM] Sending to frontend - node: {node_id}, status: {status}, message length: {len(message_content)}")
                #     logger.debug(f"[STREAM] Message preview: {message_content[:100]}...")
                
                # Ensure we pass 'status' and 'message' to the frontend
                yield json.dumps({
                    "response": message_content,
                    "node": node_id,
                    "status": status,
                    "thread_id": thread_id
                }) + "\n"
        except Exception as e:
            logger.error(f"Error in stream: {e}", exc_info=True)
            error_msg = f"Streaming error: {type(e).__name__}: {str(e)}"
            yield json.dumps({"response": error_msg, "status": "error", "thread_id": thread_id}) + "\n"

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/transport/config")
async def get_config():
    return {"transport": DEFAULT_MESSAGE_TRANSPORT.upper()}

# -------------------- Main --------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host=COMPLIANCE_AGENT_IP, port=COMPLIANCE_AGENT_PORT, reload=True)
