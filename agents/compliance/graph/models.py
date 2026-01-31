"""
Pydantic models for the Compliance Graph state and structured outputs.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Violation(BaseModel):
    """
    Represents a single compliance violation.
    All fields are required for OpenAI structured output compatibility.
    """
    device: str = Field(..., description="The device name where the violation was found")
    rule: str = Field(..., description="The compliance rule that was violated")
    severity: str = Field(..., description="Severity level: 'critical', 'high', 'medium', or 'low'")
    message: str = Field(..., description="Description of the violation")


class RemediationItem(BaseModel):
    """
    Represents a single remediation action item.
    All fields are required for OpenAI structured output compatibility.
    """
    id: int = Field(..., description="Unique identifier for the remediation item")
    critical: bool = Field(..., description="Whether this item is critical (🚨)")
    action: str = Field(..., description="The remediation action to perform (e.g., 'apply-template', 'sync-to')")
    target: str = Field(..., description="The target device or resource (e.g., 'Core-R01')")
    details: str = Field(..., description="Additional details about the action")
    schedule: str = Field(..., description="Schedule/frequency for the action (e.g., 'Immediate', 'Weekly Mon 02:00')")
    status: str = Field(..., description="Current status: 'Pending 🟡', 'Approved ✅', 'Rejected ❌', or 'Executed ✅'")


class AnalysisResult(BaseModel):
    """
    Structured output from the LLM analysis of a compliance report.
    All fields are required for OpenAI structured output compatibility.
    """
    summary: str = Field(..., description="Executive summary of the compliance analysis")
    total_devices: int = Field(..., description="Total number of devices analyzed")
    compliant_devices: int = Field(..., description="Number of compliant devices")
    non_compliant_devices: int = Field(..., description="Number of non-compliant devices")
    violations: List[Violation] = Field(..., description="List of violations found")
    remediation_items: List[RemediationItem] = Field(..., description="Proposed remediation actions")
