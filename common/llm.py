from config.config import LLM_MODEL
import litellm
from langchain_litellm import ChatLiteLLM

import common.chat_lite_llm_shim as chat_lite_llm_shim # our drop-in client

def get_llm(streaming: bool = True):
  """
    Get the LLM provider based on the configuration using ChatLiteLLM
    
    Args:
        streaming: Whether to enable streaming mode. Set to False for structured outputs.
  """
  llm = ChatLiteLLM(model=LLM_MODEL, streaming=streaming)
  if LLM_MODEL.startswith("oauth2/"):
      llm.client = chat_lite_llm_shim
  return llm