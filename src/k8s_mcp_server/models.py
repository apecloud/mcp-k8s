"""Pydantic models for the K8s MCP Server API."""

from typing import Dict, Any, Literal, Optional

from pydantic import BaseModel, Field


class ErrorDetails(BaseModel):
    """Structured error details."""

    message: str = Field(..., description="A human-readable error message.")
    code: str = Field(..., description="A machine-readable error code (e.g., 'EXECUTION_ERROR').")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details about the error.")


class CommandResult(BaseModel):
    """Represents the final result of a command execution."""

    status: Literal["error", "success"] = Field(..., description="The final status of the command.")
    output: str = Field(..., description="The combined stdout and stderr, or an error message.")
    error: Optional[ErrorDetails] = Field(None, description="Structured error information, present if status is 'error'.")
    exit_code: Optional[int] = Field(None, description="The exit code of the command, if it was executed.") 