/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React, { useState, useEffect, useRef } from "react"
import { Message } from "@/types/message"
import airplaneSvg from "@/assets/airplane.svg"
import { Trash2, ArrowDown } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import CoffeePromptsDropdown from "./Prompts/CoffeePromptsDropdown"
import LogisticsPromptsDropdown from "./Prompts/LogisticsPromptsDropdown"
import ProvisioningPromptsDropdown from "./Prompts/ProvisioningPromptsDropdown"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import UserMessage from "./UserMessage"
import ChatHeader from "./ChatHeader"
import AgentIcon from "@/assets/Icon-Chatbot-AI-Midnight.svg"

import { cn } from "@/utils/cn.ts"
import { logger } from "@/utils/logger"
import GroupCommunicationFeed from "./GroupCommunicationFeed"
import AuctionStreamingFeed from "./AuctionStreamingFeed"

interface ChatAreaProps {
  messages?: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  setButtonClicked: (clicked: boolean) => void
  setAiReplied: (replied: boolean) => void
  isBottomLayout: boolean
  showCoffeePrompts?: boolean
  showLogisticsPrompts?: boolean
  showProvisioningPrompts?: boolean
  showProgressTracker?: boolean
  showAuctionStreaming?: boolean
  showFinalResponse?: boolean
  onStreamComplete?: () => void
  onSenderHighlight?: (nodeId: string) => void
  pattern?: string
  graphConfig?: any
  onDropdownSelect?: (query: string) => void
  onUserInput?: (query: string) => void
  onApiResponse?: (response: string, isError?: boolean) => void
  onClearConversation?: () => void
  currentUserMessage?: string
  agentResponse?: string
  executionKey?: string
  isAgentLoading?: boolean
  apiError: boolean
  chatRef?: React.RefObject<HTMLDivElement | null>
  auctionState?: any
}

const ChatArea: React.FC<ChatAreaProps> = ({
  messages = [],
  setMessages,
  setButtonClicked,
  setAiReplied,
  isBottomLayout,
  showCoffeePrompts = false,
  showLogisticsPrompts = false,
  showProvisioningPrompts = false,
  showProgressTracker = false,
  showAuctionStreaming = false,
  showFinalResponse = false,
  onStreamComplete,
  onSenderHighlight,
  pattern,
  graphConfig,
  onDropdownSelect,
  onUserInput,
  onApiResponse,
  onClearConversation,
  currentUserMessage,
  agentResponse,
  executionKey,
  isAgentLoading,
  apiError,
  chatRef,
  auctionState,
}) => {
  const [content, setContent] = useState<string>("")
  const [loading, setLoading] = useState<boolean>(false)
  const [isMinimized, setIsMinimized] = useState<boolean>(false)
  const [showScrollButton, setShowScrollButton] = useState<boolean>(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const { sendMessageWithCallback } = useAgentAPI()

  // Show welcome message for provisioning pattern when component loads
  useEffect(() => {
    if (pattern === "provisioning" && messages.length === 0) {
      const welcomeMessage = {
        role: "assistant" as const,
        content: "**Welcome to the AI Compliance Assistant** 🛡️\n\nI'm here to help you with compliance-related questions and tasks.\n\n**How can I assist you today?**",
        id: "welcome-" + Date.now(),
        animate: false,
      }
      setMessages([welcomeMessage])
    }
  }, [pattern])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current && messages.length > 0) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  // Detect scroll position to show/hide scroll button
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
      setShowScrollButton(!isNearBottom && messages.length > 0)
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [messages.length])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const handleMinimize = () => {
    setIsMinimized(true)
  }

  const handleRestore = () => {
    setIsMinimized(false)
  }

  const handleDropdownQuery = (query: string) => {
    if (isMinimized) {
      setIsMinimized(false)
    }

    // Paste the selected prompt into the chat input instead of auto-sending
    setContent(query)
  }

  const processMessageWithQuery = async (
    messageContent: string,
  ): Promise<void> => {
    if (!messageContent.trim()) return

    setContent("")
    setLoading(true)
    setButtonClicked(true)

    await sendMessageWithCallback(
      messageContent,
      setMessages,
      {
        onSuccess: (response) => {
          setAiReplied(true)
          // For provisioning pattern, messages are already managed by streaming logic
          // Don't call onApiResponse to avoid overwriting streamed messages
          if (pattern !== "provisioning" && onApiResponse) {
            onApiResponse(response, false)
          }
        },
        onError: (error) => {
          logger.apiError("/agent/prompt", error)
          if (onApiResponse) {
            onApiResponse("Sorry, I encountered an error.", true)
          }
        },
        onNodeHighlight: onSenderHighlight,
      },
      pattern,
    )

    setLoading(false)
  }

  const processMessage = async (): Promise<void> => {
    if (isMinimized) {
      setIsMinimized(false)
    }

    if (onUserInput) {
      onUserInput(content)
    }

    if ((showAuctionStreaming || showProgressTracker) && onDropdownSelect) {
      setContent("")
      onDropdownSelect(content)
    } else {
      await processMessageWithQuery(content)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      processMessage()
    }
  }

  if (!isBottomLayout) {
    return null
  }

  return (
    <div
      ref={chatRef}
      className="relative flex w-full h-full flex-col overflow-hidden"
      style={{ backgroundColor: "var(--overlay-background)" }}
    >
      {currentUserMessage && (
        <ChatHeader
          onMinimize={isMinimized ? handleRestore : handleMinimize}
          onClearConversation={onClearConversation}
          isMinimized={isMinimized}
          showActions={!!agentResponse && !isAgentLoading}
        />
      )}

      {/* Scrollable messages area */}
      <div
        ref={scrollContainerRef}
        className="flex w-full flex-1 flex-col items-center gap-2 px-2 sm:px-4 md:px-6 lg:px-8 xl:px-12 py-2 overflow-y-auto relative pb-[140px]"
      >
        {/* Scroll to bottom button */}
        {showScrollButton && (
          <button
            onClick={scrollToBottom}
            className="fixed bottom-[160px] right-8 z-40 flex h-10 w-10 items-center justify-center rounded-full bg-accent-primary hover:bg-[#834DD7] shadow-lg transition-colors"
            title="Scroll to latest message"
          >
            <ArrowDown className="h-5 w-5 text-white" />
          </button>
        )}
        {/* Conversational Message History */}
        {!isMinimized && messages.length > 0 && pattern === "provisioning" && (
          <div className="mb-4 flex w-full max-w-[95%] sm:max-w-[90%] md:max-w-[85%] lg:max-w-[80%] xl:max-w-[1400px] flex-col gap-4 p-6">
            {messages.map((message, index) => (
              <div key={message.id} className="flex w-full flex-col gap-3 animate-fadeIn">
                {message.role === "user" ? (
                  <div className="flex w-full justify-end">
                    <div className="max-w-[85%] sm:max-w-[80%] md:max-w-[75%] rounded-2xl rounded-br-md bg-gradient-to-r from-[#834DD7] to-[#58C0D0] px-4 py-3 shadow-md">
                      <p className="text-white font-inter text-base leading-relaxed">{message.content}</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex w-full flex-row items-start gap-3">
                    <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-gradient-to-br from-[#0A60FF] to-[#02C8FF] shadow-lg">
                      <img
                        src={AgentIcon}
                        alt="Agent"
                        className="h-6 w-6 brightness-0 invert"
                      />
                    </div>
                    <div className="flex max-w-[90%] sm:max-w-[85%] flex-1 flex-col items-start justify-center rounded-2xl rounded-tl-md bg-chat-background px-4 py-3 shadow-sm border border-node-background/30">
                      <div className={cn(
                        "markdown-content break-words font-inter text-base leading-relaxed",
                        message.id === "loading-placeholder" && "thinking-message"
                      )}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Legacy Single Message Display (for non-conversational patterns) */}
        {currentUserMessage && pattern !== "provisioning" && (
          <div className="mb-4 flex w-full max-w-[880px] flex-col gap-3">
            {!isMinimized && <UserMessage content={currentUserMessage} />}

            {showProgressTracker && (
              <div className={`w-full ${isMinimized ? "hidden" : ""}`}>
                <GroupCommunicationFeed
                  isVisible={!isMinimized && showProgressTracker}
                  onComplete={onStreamComplete}
                  onSenderHighlight={onSenderHighlight}
                  graphConfig={graphConfig}
                  prompt={currentUserMessage || ""}
                  executionKey={executionKey}
                  apiError={apiError}
                />
              </div>
            )}

            {showAuctionStreaming && (
              <div className={`w-full ${isMinimized ? "hidden" : ""}`}>
                <AuctionStreamingFeed
                  isVisible={!isMinimized && showAuctionStreaming}
                  prompt={currentUserMessage || ""}
                  apiError={apiError}
                  auctionStreamingState={auctionState}
                />
              </div>
            )}

            {showFinalResponse &&
              (isAgentLoading || agentResponse) &&
              !isMinimized && (
                <div className="flex w-full flex-row items-start gap-1">
                  <div className="chat-avatar-container flex h-10 w-10 flex-none items-center justify-center rounded-full" style={{backgroundColor: '#FF9000'}}>
                    <img
                      src={AgentIcon}
                      alt="Agent"
                      className="h-[36px] w-[36px] brightness-0 invert"
                    />
                  </div>
                  <div className="flex max-w-[calc(100%-3rem)] flex-1 flex-col items-start justify-center rounded p-1 px-2">
                    <div className="markdown-content break-words font-inter text-sm font-normal leading-5">
                      {isAgentLoading ? (
                        <div className="thinking-message animate-pulse text-accent-primary">
                          Thinking..🧠
                        </div>
                      ) : (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {agentResponse}
                        </ReactMarkdown>
                      )}
                    </div>
                  </div>
                </div>
              )}
          </div>
        )}

        {showCoffeePrompts && (
          <div className="relative z-10 flex h-9 w-auto flex-row items-start gap-2 p-0 mb-2">
            <CoffeePromptsDropdown
              visible={true}
              onSelect={handleDropdownQuery}
              pattern={pattern}
            />
          </div>
        )}

        {showLogisticsPrompts && (
          <div className="relative z-10 flex h-9 w-auto flex-row items-start gap-2 p-0 mb-2">
            <LogisticsPromptsDropdown
              visible={true}
              onSelect={handleDropdownQuery}
            />
          </div>
        )}

        {showProvisioningPrompts && (
          <div className="relative z-10 flex h-9 w-auto flex-row items-start gap-2 p-0 mb-2">
            <ProvisioningPromptsDropdown
              visible={true}
              onSelect={handleDropdownQuery}
            />
          </div>
        )}
      </div>

      {/* Fixed input area at bottom */}
      <div className="absolute bottom-0 left-0 right-0 px-4 sm:px-6 md:px-10 lg:px-16 py-5 bg-overlay-background/95 backdrop-blur-md z-30">
        <div className="flex w-full justify-center">
          <div className="flex w-full max-w-[1800px] flex-row items-end gap-3">
            <div className="flex-1 min-h-[96px] rounded-xl border-2 border-white/30 bg-chat-input-background/90 backdrop-blur-sm px-5 py-4 focus-within:border-white/60 focus-within:shadow-[0_0_0_3px_rgba(255,255,255,0.1)] transition-all duration-200">
              <textarea
                className="w-full min-h-[64px] max-h-[150px] border-none bg-transparent font-inter text-[17px] font-medium leading-7 text-white outline-none placeholder:text-white/70 resize-none"
                placeholder="Ask me anything about compliance..."
                rows={3}
                value={content}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setContent(e.target.value)
                }
                onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    if (content.trim() && !loading) {
                      processMessage()
                    }
                  }
                }}
                disabled={loading}
              />
            </div>
            <div className="flex flex-col gap-2 pb-1">
              {messages.length > 0 && onClearConversation && (
                <button
                  onClick={onClearConversation}
                  className="flex h-14 w-14 cursor-pointer items-center justify-center rounded-full border-2 border-white/30 bg-chat-input-background/80 hover:bg-red-500/10 hover:border-red-400/50 hover:scale-105 transition-all duration-200"
                  title="Clear conversation"
                >
                  <Trash2 className="h-5 w-5 text-chat-text hover:text-red-400 transition-colors" />
                </button>
              )}
              <button
                onClick={() => {
                  if (content.trim() && !loading) {
                    processMessage()
                  }
                }}
                className="flex h-14 w-14 cursor-pointer items-center justify-center rounded-full border-2 border-white/30 bg-gradient-to-r from-[#834DD7] via-[#7670D5] to-[#58C0D0] shadow-lg hover:shadow-xl hover:scale-110 hover:brightness-110 transition-all duration-200"
              >
                <img src={airplaneSvg} alt="Send" className="h-6 w-6" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatArea
