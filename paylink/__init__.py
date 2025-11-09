"""
PayLink Python SDK

A Python SDK for interacting with PayLink MCP (Model Context Protocol) servers.
"""

from .client import PayLink
from .mcp_monitization import McpMonitizationAdapter, PaymentError, require_payment
from .mpesa_tools import MpesaTools

__version__ = "0.1.3"
__author__ = "PayLink"
__email__ = "paylinkmcp@gmail.com"
__all__ = ["PayLink", "MpesaTools", "McpMonitizationAdapter", "PaymentError", "require_payment"]
