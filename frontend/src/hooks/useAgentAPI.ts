import React, { useRef, useState, useEffect } from "react"
import axios from "axios"
import { v4 as uuid } from "uuid"
import { Message } from "@/types/message"
import { Role } from "@/utils/const"
import { withRetry, RETRY_CONFIG } from "@/utils/retryUtils"
import { 
  shouldEnableRetries, 
  getApiUrlForPattern, 
  isProvisioningPattern 
} from "@/utils/patternUtils"

interface ApiResponse {
  response: string
}

interface UseAgentAPIReturn {
  loading: boolean
  sendMessage: (prompt: string, pattern?: string) => Promise<string>
  sendMessageWithCallback: (
    prompt: string,
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
    callbacks?: {
      onStart?: () => void
      onSuccess?: (response: string) => void
      onError?: (error: any) => void
      onRetryAttempt?: (
        attempt: number,
        error: Error,
        nextRetryAt: number,
      ) => void
      onNodeHighlight?: (nodeId: string) => void
    },
    pattern?: string,
  ) => Promise<void>
  cancel: () => void
  resetWebSocket: () => void
}

export const useAgentAPI = (): UseAgentAPIReturn => {
  const [loading, setLoading] = useState<boolean>(false)
  const abortRef = useRef<AbortController | null>(null)
  const requestIdRef = useRef<number>(0)
  const wsRef = useRef<WebSocket | null>(null)

  const resetWebSocket = () => {
    sessionStorage.removeItem('provisioning_thread_id')
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    requestIdRef.current += 1
  }

  const cancel = () => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    requestIdRef.current += 1
    setLoading(false)
  }

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  const sendMessage = async (prompt: string, pattern?: string): Promise<string> => {
    if (!prompt.trim()) throw new Error("Prompt cannot be empty")
    const apiUrl = getApiUrlForPattern(pattern)
    setLoading(true)
    const controller = new AbortController()
    abortRef.current = controller
    const myRequestId = requestIdRef.current + 1
    requestIdRef.current = myRequestId

    const makeApiCall = async (): Promise<string> => {
      const response = await axios.post<ApiResponse>(
        `${apiUrl}/agent/prompt`,
        { prompt },
        { signal: controller.signal },
      )
      return response.data.response
    }

    try {
      return shouldEnableRetries(pattern) ? await withRetry(makeApiCall) : await makeApiCall()
    } finally {
      if (requestIdRef.current === myRequestId) setLoading(false)
    }
  }

  const sendMessageWithCallback = async (
    prompt: string,
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
    callbacks?: {
      onStart?: () => void
      onSuccess?: (response: string) => void
      onError?: (error: any) => void
      onRetryAttempt?: (attempt: number, error: Error, delay: number) => void
      onNodeHighlight?: (nodeId: string) => void
    },
    pattern?: string
  ) => {
    const myRequestId = requestIdRef.current + 1
    requestIdRef.current = myRequestId

    const userMessage: Message = {
      role: Role.USER,
      content: prompt,
      id: uuid(),
      animate: false,
    }

    const loadingMessage: Message = {
      role: Role.ASSISTANT,
      content: "Thinking . . . 🧠",
      id: "loading-placeholder",
      animate: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setLoading(true)
    if (callbacks?.onStart) callbacks.onStart()

    // --- STREAMING IMPLEMENTATION (Provisioning Pattern) ---
    if (isProvisioningPattern(pattern)) {
      const apiUrl = getApiUrlForPattern(pattern)
      const controller = new AbortController()
      abortRef.current = controller
      
      const threadId = sessionStorage.getItem('provisioning_thread_id') || uuid()
      sessionStorage.setItem('provisioning_thread_id', threadId)

      // Stable ID for the assistant message we will append tokens to
      const activeAssistantMessageId = uuid()

      try {
        const response = await fetch(`${apiUrl}/agent/prompt/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, thread_id: threadId }),
          signal: controller.signal,
        })

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done || requestIdRef.current !== myRequestId) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.trim()) continue
            
            try {
              const data = JSON.parse(line)
              const chunk = data.response || ""
              const nodeId = data.node
              const status = data.status
              
              if (nodeId && callbacks?.onNodeHighlight) {
                callbacks.onNodeHighlight(nodeId)
              }
              
              // Only update UI if we have actual content (not just status updates)
              if (chunk) {
                setMessages((prevMessages: Message[]) => {
                  // 1. Remove the loading placeholder only when we have actual content
                  const filtered = prevMessages.filter(m => m.id !== "loading-placeholder");
                  
                  // 2. Check if the assistant message already exists in the list
                  const existingIndex = filtered.findIndex(m => m.id === activeAssistantMessageId);

                  if (existingIndex !== -1) {
                    // 3. Append token to existing message
                    const updated = [...filtered];
                    updated[existingIndex] = {
                      ...updated[existingIndex],
                      content: updated[existingIndex].content + chunk,
                      animate: false, // Disable re-animation for smooth streaming
                    };
                    return updated;
                  } else {
                    // 4. First token: Create the message object and remove placeholder
                    return [
                      ...filtered,
                      {
                        role: Role.ASSISTANT,
                        content: chunk,
                        id: activeAssistantMessageId,
                        animate: true,
                      }
                    ];
                  }
                })
              }
            } catch (parseError) {
              console.error("Error parsing stream line:", parseError)
            }
          }
        }

        if (requestIdRef.current === myRequestId) {
          setLoading(false)
          if (callbacks?.onSuccess) callbacks.onSuccess("Workflow completed")
        }
      } catch (error) {
        if (requestIdRef.current === myRequestId) {
          setMessages((prev) => [
            ...prev.filter(m => m.id !== "loading-placeholder"),
            { role: Role.ASSISTANT, content: "Error: Failed to fetch stream.", id: uuid(), animate: false }
          ])
          setLoading(false)
        }
        if (callbacks?.onError) callbacks.onError(error)
      }
      return
    }

    // --- STANDARD HTTP IMPLEMENTATION (Other Patterns) ---
    const apiUrl = getApiUrlForPattern(pattern)
    const controller = new AbortController()
    abortRef.current = controller

    const makeApiCall = async (): Promise<string> => {
      const response = await axios.post<ApiResponse>(
        `${apiUrl}/agent/prompt`,
        { prompt },
        { signal: controller.signal },
      )
      return response.data.response
    }

    const onRetryAttempt = (attempt: number) => {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1].content = `Retrying... (${attempt}/${RETRY_CONFIG.maxRetries})`
        return updated
      })
    }

    try {
      const responseText = shouldEnableRetries(pattern) 
        ? await withRetry(makeApiCall, onRetryAttempt) 
        : await makeApiCall()

      if (requestIdRef.current === myRequestId) {
        setMessages((prev) => {
          const updated = [...prev.filter(m => m.id !== "loading-placeholder")]
          return [...updated, { role: Role.ASSISTANT, content: responseText, id: uuid(), animate: true }]
        })
      }
      if (callbacks?.onSuccess) callbacks.onSuccess(responseText)
    } catch (error) {
      if (requestIdRef.current === myRequestId) {
        setMessages((prev) => [
          ...prev.filter(m => m.id !== "loading-placeholder"),
          { role: Role.ASSISTANT, content: "Sorry, I encountered an error.", id: uuid(), animate: false }
        ])
      }
      if (callbacks?.onError) callbacks.onError(error)
    } finally {
      if (requestIdRef.current === myRequestId) setLoading(false)
    }
  }

  return {
    loading,
    sendMessage,
    sendMessageWithCallback,
    cancel,
    resetWebSocket,
  }
}