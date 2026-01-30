/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React, { useState, useEffect } from "react"
import {
  PatternType,
  PATTERNS,
  getApiUrlForPattern,
} from "@/utils/patternUtils"
import SidebarItem from "./sidebarItem"
import SidebarDropdown from "./SidebarDropdown"

interface SidebarProps {
  selectedPattern: PatternType
  onPatternChange: (pattern: PatternType) => void
}

const Sidebar: React.FC<SidebarProps> = ({
  selectedPattern,
  onPatternChange,
}) => {
  const [isPublishSubscribeExpanded, setIsPublishSubscribeExpanded] =
    useState(true)
  const [
    isPublishSubscribeStreamingExpanded,
    setIsPublishSubscribeStreamingExpanded,
  ] = useState(true)
  const [isProvisioningExpanded, setIsProvisioningExpanded] = useState(true)
  const [transport, setTransport] = useState<string>("")

  useEffect(() => {
    const fetchTransportConfig = async () => {
      // Only fetch transport config for patterns that need it (not provisioning)
      if (selectedPattern === PATTERNS.PROVISIONING) {
        return
      }
      
      try {
        const response = await fetch(
          `${getApiUrlForPattern(PATTERNS.PUBLISH_SUBSCRIBE)}/transport/config`,
        )
        const data = await response.json()
        if (data.transport) {
          setTransport(data.transport)
        }
      } catch (error) {
        console.error("Error fetching transport config:", error)
      }
    }

    fetchTransportConfig()
  }, [selectedPattern])

  const handlePublishSubscribeToggle = () => {
    setIsPublishSubscribeExpanded(!isPublishSubscribeExpanded)
  }

  const handlePublishSubscribeStreamingToggle = () => {
    setIsPublishSubscribeStreamingExpanded(!isPublishSubscribeStreamingExpanded)
  }

  const handleProvisioningToggle = () => {
    setIsProvisioningExpanded(!isProvisioningExpanded)
  }

  return (
    <div className="flex h-full w-64 flex-none flex-col gap-5 border-r border-sidebar-border bg-sidebar-background font-inter lg:w-[320px]">
      <div className="flex h-full flex-1 flex-col gap-5 p-4">
        <div className="flex flex-col">
          <div className="flex min-h-[36px] w-full items-center gap-2 rounded py-2 pl-2 pr-5">
            <span className="flex-1 font-inter text-base font-semibold leading-5 tracking-[0.25px] text-sidebar-text">
              AI Compliance Assistant
            </span>
          </div>

          <div className="flex flex-col mt-2">
            <div>
              <SidebarDropdown
                title="Compliance"
                isExpanded={isProvisioningExpanded}
                onToggle={handleProvisioningToggle}
              >
                <SidebarItem
                  title="Compliance Chat"
                  isSelected={selectedPattern === PATTERNS.PROVISIONING}
                  onClick={() => onPatternChange(PATTERNS.PROVISIONING)}
                />
              </SidebarDropdown>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Sidebar
