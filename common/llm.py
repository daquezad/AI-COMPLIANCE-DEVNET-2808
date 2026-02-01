from config.config import LLM_MODEL
import litellm
from langchain_litellm import ChatLiteLLM

import common.chat_lite_llm_shim as chat_lite_llm_shim # our drop-in client

# Configure litellm retry settings for rate limits
litellm.num_retries = 3  # Retry up to 3 times
litellm.request_timeout = 120  # 2 minute timeout
litellm.retry_policy = {
    "RateLimitError": {"num_retries": 5, "retry_after": 60},  # Wait 60s on rate limit
}

def get_llm(streaming: bool = True):
  """
    Get the LLM provider based on the configuration using ChatLiteLLM
    
    Args:
        streaming: Whether to enable streaming mode. Set to False for structured outputs.
  """
  llm = ChatLiteLLM(
      model=LLM_MODEL, 
      streaming=streaming,
      max_retries=3,  # LangChain retry
  )
  if LLM_MODEL.startswith("oauth2/"):
      llm.client = chat_lite_llm_shim
  return llm