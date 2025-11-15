"""
Client extension for interacting with PayLink's M-Pesa tooling.
"""

from typing import List, Optional

from paylink.client import PayLink


class MpesaTools(PayLink):
    """
    Convenience client for interacting with PayLink's M-Pesa tooling.
    """

    def __init__(
        self,
        base_url: str = "http://3.107.114.80:5002/mcp",
        api_key: Optional[str] = None,
        tracing: Optional[str] = None,
        project: Optional[str] = None,
        payment_provider: Optional[List[str]] = None,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            tracing=tracing,
            project=project,
            payment_provider=payment_provider,
        )

