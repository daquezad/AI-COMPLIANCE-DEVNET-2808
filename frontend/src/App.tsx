/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React, { useState, useEffect, useRef, useCallback } from "react"
import { LOCAL_STORAGE_KEY } from "@/components/Chat/Messages"
import { logger } from "@/utils/logger"
import { useChatAreaMeasurement } from "@/hooks/useChatAreaMeasurement"

import {
  useStreamingStatus,
  useStreamingEvents,
  useStreamingError,
  useStreamingActions,
} from "@/stores/auctionStreamingStore"
import {
  useGroupIsStreaming,
  useGroupIsComplete,
  useGroupFinalResponse,
  useGroupError,
  useStartGroupStreaming,
  useGroupStreamingActions,
} from "@/stores/groupStreamingStore"

import Navigation from "@/components/Navigation/Navigation"
import MainArea from "@/components/MainArea/MainArea"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import ChatArea from "@/components/Chat/ChatArea"
import Sidebar from "@/components/Sidebar/Sidebar"
import { ThemeProvider } from "@/contexts/ThemeContext"
import { Message } from "./types/message"
import { getGraphConfig } from "@/utils/graphConfigs"
import { PATTERNS, PatternType } from "@/utils/patternUtils"
import { v4 as uuid } from "uuid"
import { Role } from "@/utils/const"
import { ChevronDown, ChevronUp, PanelLeftClose, PanelLeft } from "lucide-react"

const App: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(true)
  const { sendMessage, resetWebSocket } = useAgentAPI()

  const [selectedPattern, setSelectedPattern] = useState<PatternType>(
    PATTERNS.PROVISIONING,
  )

  const startStreaming = useStartGroupStreaming()

  const { connect, reset } = useStreamingActions()
  const status = useStreamingStatus()
  const events = useStreamingEvents()
  const error = useStreamingError()

  const groupIsStreaming = useGroupIsStreaming()
  const groupIsComplete = useGroupIsComplete()
  const groupFinalResponse = useGroupFinalResponse()
  const groupError = useGroupError()
  const { reset: resetGroup } = useGroupStreamingActions()
  const [aiReplied, setAiReplied] = useState<boolean>(false)
  const [buttonClicked, setButtonClicked] = useState<boolean>(false)
  const [currentUserMessage, setCurrentUserMessage] = useState<string>("")
  const [agentResponse, setAgentResponse] = useState<string>("")
  const [isAgentLoading, setIsAgentLoading] = useState<boolean>(false)
  const [apiError, setApiError] = useState<boolean>(false)
  const [groupCommResponseReceived, setGroupCommResponseReceived] =
    useState(false)
  const [highlightNodeFunction, setHighlightNodeFunction] = useState<
    ((nodeId: string) => void) | null
  >(null)
  const [showProgressTracker, setShowProgressTracker] = useState<boolean>(false)
  const [showAuctionStreaming, setShowAuctionStreaming] =
    useState<boolean>(false)
  const [showFinalResponse, setShowFinalResponse] = useState<boolean>(false)
  const [pendingResponse, setPendingResponse] = useState<string>("")
  const [executionKey, setExecutionKey] = useState<string>("")
  const streamCompleteRef = useRef<boolean>(false)
  const [isChatCollapsed, setIsChatCollapsed] = useState<boolean>(false)
  const [chatHeightVh, setChatHeightVh] = useState<number>(50) // Default 50vh
  const isResizingRef = useRef<boolean>(false)
  const resizeStartYRef = useRef<number>(0)
  const resizeStartHeightRef = useRef<number>(50)

  const handlePatternChange = useCallback(
    (pattern: PatternType) => {
      reset()
      setShowAuctionStreaming(false)

      resetGroup()
      setGroupCommResponseReceived(false)

      setShowFinalResponse(false)
      setAgentResponse("")
      setPendingResponse("")
      setIsAgentLoading(false)
      setApiError(false)
      setCurrentUserMessage("")

      setButtonClicked(false)
      setAiReplied(false)

      setSelectedPattern(pattern)
    },
    [reset, resetGroup],
  )
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  })

  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    if (selectedPattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING) {
      if (
        events.length > 0 &&
        status !== "connecting" &&
        status !== "streaming" &&
        isAgentLoading
      ) {
        setIsAgentLoading(false)
      }
    }
  }, [selectedPattern, events.length, status, isAgentLoading])

  // Reset animation states when pattern changes to prevent stale animations
  useEffect(() => {
    setButtonClicked(false)
    setAiReplied(false)
  }, [selectedPattern])

  const {
    height: chatHeight,
    isExpanded,
    chatRef,
  } = useChatAreaMeasurement({
    debounceMs: 100,
  })

  const chatHeightValue = currentUserMessage || agentResponse ? chatHeight : 76

  const handleUserInput = (query: string) => {
    setCurrentUserMessage(query)
    setIsAgentLoading(true)
    setButtonClicked(true)
    setApiError(false)

    if (
      selectedPattern !== PATTERNS.GROUP_COMMUNICATION &&
      selectedPattern !== PATTERNS.PUBLISH_SUBSCRIBE_STREAMING
    ) {
      setShowFinalResponse(true)
    }
  }

  const handleApiResponse = useCallback(
    (response: string, isError: boolean = false) => {
      setAgentResponse(response)
      setIsAgentLoading(false)

      if (selectedPattern === PATTERNS.GROUP_COMMUNICATION) {
        setApiError(isError)
        if (!isError) {
          setGroupCommResponseReceived(true)
        }
      }

      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: response,
          animate: !isError,
        }
        return updated
      })
    },
    [selectedPattern, setMessages],
  )

  useEffect(() => {
    if (selectedPattern === PATTERNS.GROUP_COMMUNICATION) {
      if (groupIsComplete && !groupIsStreaming) {
        if (groupFinalResponse) {
          setShowFinalResponse(true)
          handleApiResponse(groupFinalResponse, false)
        } else if (groupError) {
          const errorMsg = `Streaming error: ${groupError}`
          setShowFinalResponse(true)
          handleApiResponse(errorMsg, true)
        }
      }
    }
  }, [
    selectedPattern,
    groupIsComplete,
    groupIsStreaming,
    groupFinalResponse,
    groupError,
    handleApiResponse,
  ])

  const handleDropdownSelect = async (query: string) => {
    setCurrentUserMessage(query)
    setIsAgentLoading(true)
    setButtonClicked(true)
    setApiError(false)

    try {
      if (selectedPattern === PATTERNS.GROUP_COMMUNICATION) {
        const newExecutionKey = Date.now().toString()
        setExecutionKey(newExecutionKey)

        setShowFinalResponse(false)
        setAgentResponse("")
        setPendingResponse("")
        setGroupCommResponseReceived(false)
        streamCompleteRef.current = false
        resetGroup()

        try {
          await startStreaming(query)
        } catch (error) {
          logger.apiError("/agent/prompt/stream", error)
          const errorMsg = "Sorry, I encountered an error with streaming."
          setShowFinalResponse(true)
          handleApiResponse(errorMsg, true)
        }
      } else if (selectedPattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING) {
        setShowFinalResponse(false)
        setShowAuctionStreaming(true)
        setAgentResponse("")
        reset()

        await connect(query)
      } else {
        // Use WebSocket for provisioning pattern  
        setShowFinalResponse(true)
        
        const response = await sendMessageWithCallback(
          query,
          setMessages,
          {
            onSuccess: (response) => {
              setAiReplied(true)
              handleApiResponse(response, false)
            },
            onError: (error) => {
              logger.apiError("/agent/prompt", error)
              handleApiResponse("Sorry, I encountered an error.", true)
            },
            onNodeHighlight: (nodeId: string) => {
              if (highlightNodeFunction) {
                highlightNodeFunction(nodeId)
              }
            },
          },
          selectedPattern,
        )
      }
    } catch (error) {
      logger.apiError("/agent/prompt", error)
      handleApiResponse("Sorry, I encountered an error.", true)
      setShowProgressTracker(false)
    } finally {
      setIsAgentLoading(false)
    }
  }

  const handleStreamComplete = () => {
    streamCompleteRef.current = true

    if (selectedPattern === PATTERNS.GROUP_COMMUNICATION) {
      setShowFinalResponse(true)
      setIsAgentLoading(true)

      if (pendingResponse) {
        const isError =
          pendingResponse.includes("error") || pendingResponse.includes("Error")
        handleApiResponse(pendingResponse, isError)
        setPendingResponse("")
      }
    }
  }

  const handleClearConversation = () => {
    setMessages([])
    setCurrentUserMessage("")
    setAgentResponse("")
    setIsAgentLoading(false)
    setButtonClicked(false)
    setAiReplied(false)
    setGroupCommResponseReceived(false)
    setShowFinalResponse(false)
    setPendingResponse("")

    // Reset WebSocket connection for provisioning pattern
    if (selectedPattern === PATTERNS.PROVISIONING) {
      resetWebSocket()
    }

    resetGroup()
  }

  const handleNodeHighlightSetup = useCallback(
    (highlightFunction: (nodeId: string) => void) => {
      setHighlightNodeFunction(() => highlightFunction)
    },
    [],
  )

  const handleSenderHighlight = useCallback(
    (nodeId: string) => {
      if (highlightNodeFunction) {
        highlightNodeFunction(nodeId)
      }
    },
    [highlightNodeFunction],
  )

  // Resize handlers for chat area
  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!isResizingRef.current) return
    
    const deltaY = resizeStartYRef.current - e.clientY // Inverted because we're resizing from top
    const viewportHeight = window.innerHeight
    const deltaPercent = (deltaY / viewportHeight) * 100
    const newHeight = Math.max(20, Math.min(80, resizeStartHeightRef.current + deltaPercent))
    
    setChatHeightVh(newHeight)
  }, [])

  const handleResizeEnd = useCallback(() => {
    isResizingRef.current = false
    document.removeEventListener('mousemove', handleResizeMove)
    document.removeEventListener('mouseup', handleResizeEnd)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }, [handleResizeMove])

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isResizingRef.current = true
    resizeStartYRef.current = e.clientY
    resizeStartHeightRef.current = chatHeightVh
    document.addEventListener('mousemove', handleResizeMove)
    document.addEventListener('mouseup', handleResizeEnd)
    document.body.style.cursor = 'row-resize'
    document.body.style.userSelect = 'none'
  }, [chatHeightVh, handleResizeMove, handleResizeEnd])

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      document.removeEventListener('mousemove', handleResizeMove)
      document.removeEventListener('mouseup', handleResizeEnd)
    }
  }, [handleResizeMove, handleResizeEnd])

  useEffect(() => {
    setCurrentUserMessage("")
    setAgentResponse("")
    setIsAgentLoading(false)
    setButtonClicked(false)
    setAiReplied(false)
    setShowFinalResponse(false)
    setPendingResponse("")

    if (selectedPattern === PATTERNS.GROUP_COMMUNICATION) {
      setShowProgressTracker(true)
      resetGroup()
    } else {
      setShowProgressTracker(false)
      setShowAuctionStreaming(false)
      setGroupCommResponseReceived(false)
    }
  }, [selectedPattern, resetGroup])

  return (
    <ThemeProvider>
      <div className="bg-primary-bg flex h-screen w-screen flex-col overflow-hidden">
        <Navigation />

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar Toggle Button when collapsed */}
          {isSidebarCollapsed && (
            <button
              onClick={() => setIsSidebarCollapsed(false)}
              className="flex h-full w-10 flex-none items-start justify-center border-r border-sidebar-border bg-sidebar-background pt-4 hover:bg-sidebar-background/80 transition-colors"
              title="Show sidebar"
            >
              <PanelLeft className="h-5 w-5 text-sidebar-text" />
            </button>
          )}

          {/* Sidebar with collapse button */}
          {!isSidebarCollapsed && (
            <div className="relative">
              <Sidebar
                selectedPattern={selectedPattern}
                onPatternChange={handlePatternChange}
              />
              <button
                onClick={() => setIsSidebarCollapsed(true)}
                className="absolute right-2 top-3 rounded-md p-1 text-sidebar-text hover:bg-sidebar-background/80 transition-colors"
                title="Hide sidebar"
              >
                <PanelLeftClose className="h-5 w-5" />
              </button>
            </div>
          )}

          <div className="flex flex-1 flex-col border-l border-action-background bg-app-background overflow-hidden">
            <div className="relative flex-1 overflow-hidden">
              <MainArea
                pattern={selectedPattern}
                buttonClicked={buttonClicked}
                setButtonClicked={setButtonClicked}
                aiReplied={aiReplied}
                setAiReplied={setAiReplied}
                chatHeight={chatHeightValue}
                isExpanded={isExpanded}
                groupCommResponseReceived={groupCommResponseReceived}
                onNodeHighlight={handleNodeHighlightSetup}
              />
            </div>

            <div className="flex w-full flex-none flex-col bg-overlay-background" style={{ height: isChatCollapsed ? '48px' : `${chatHeightVh}vh` }}>
              {/* Resize Handle */}
              {!isChatCollapsed && (
                <div
                  onMouseDown={handleResizeStart}
                  className="flex h-1 w-full cursor-row-resize items-center justify-center bg-transparent hover:bg-accent-primary transition-colors group"
                  style={{ touchAction: 'none' }}
                  title="Drag to resize chat area"
                >
                  <div className="h-0.5 w-16 rounded-full bg-node-background group-hover:bg-accent-primary transition-colors" />
                </div>
              )}
              {/* Toggle Button */}
              <div className="flex w-full items-center justify-center border-b border-node-background bg-chat-background py-2">
                <button
                  onClick={() => setIsChatCollapsed(!isChatCollapsed)}
                  className="flex items-center gap-2 rounded-md px-4 py-1 text-chat-text hover:bg-chat-background-hover transition-colors"
                  title={isChatCollapsed ? "Show chat" : "Hide chat"}
                >
                  {isChatCollapsed ? (
                    <>
                      <ChevronUp className="h-5 w-5" />
                      <span className="text-sm font-medium">Show Chat</span>
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-5 w-5" />
                      <span className="text-sm font-medium">Hide Chat</span>
                    </>
                  )}
                </button>
              </div>
              {!isChatCollapsed && (
              <ChatArea
                messages={messages}
                setMessages={setMessages}
                setButtonClicked={setButtonClicked}
                setAiReplied={setAiReplied}
                isBottomLayout={true}
                showCoffeePrompts={
                  selectedPattern === PATTERNS.PUBLISH_SUBSCRIBE ||
                  selectedPattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING
                }
                showLogisticsPrompts={
                  selectedPattern === PATTERNS.GROUP_COMMUNICATION
                }
                showProvisioningPrompts={
                  selectedPattern === PATTERNS.PROVISIONING
                }
                showProgressTracker={showProgressTracker}
                showAuctionStreaming={showAuctionStreaming}
                showFinalResponse={showFinalResponse}
                onStreamComplete={handleStreamComplete}
                onSenderHighlight={handleSenderHighlight}
                pattern={selectedPattern}
                graphConfig={getGraphConfig(
                  selectedPattern,
                  groupCommResponseReceived,
                )}
                onDropdownSelect={handleDropdownSelect}
                onUserInput={handleUserInput}
                onApiResponse={handleApiResponse}
                onClearConversation={handleClearConversation}
                currentUserMessage={currentUserMessage}
                agentResponse={agentResponse}
                executionKey={executionKey}
                isAgentLoading={isAgentLoading}
                apiError={apiError}
                chatRef={chatRef}
                auctionState={{
                  events,
                  status,
                  error,
                }}
              />
              )}
            </div>
          </div>
        </div>
      </div>
    </ThemeProvider>
  )
}

export default App
