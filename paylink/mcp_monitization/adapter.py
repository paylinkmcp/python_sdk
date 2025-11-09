"""
Adapters for monetization workflows that leverage the Model Context Protocol.
"""

from paylink.client import PayLink
from paylink.config import PayLinkConfig


class McpMonitizationAdapter(PayLink):
    """
    Generic MCP monetization adapter.
    """

    def __init__(
        self,
        *,
        url: str,
        wallet_connection_string: str,
        transport: str,
    ):
        if not url:
            raise ValueError(
                "`url` is required when using McpMonitizationAdapter."
            )
        if not wallet_connection_string:
            raise ValueError(
                "`wallet_connection_string` is required when using McpMonitizationAdapter."
            )
        if not transport:
            raise ValueError("`transport` is required when using McpMonitizationAdapter.")

        self.wallet_connection_string = wallet_connection_string
        self.transport = transport

        config = PayLinkConfig.resolve(
            base_url=url,
            api_key=None,
            tracing=None,
            project=None,
            payment_provider=None,
            required_headers=[],
        )
        config.with_monitization(
            wallet_connection_string=self.wallet_connection_string,
            transport=self.transport,
        )

        super().__init__(config=config)
