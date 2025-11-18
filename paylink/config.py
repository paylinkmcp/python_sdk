from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional dotenv support
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv
except ImportError:  # only ignore missing library
    load_dotenv = None
else:
    load_dotenv(override=True)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAYLINK_API_KEY_HEADER = "PAYLINK_API_KEY"
PAYLINK_PROJECT_HEADER = "PAYLINK_PROJECT"
PAYLINK_TRACING_HEADER = "PAYLINK_TRACING"
PAYMENT_PROVIDER_HEADER = "PAYMENT_PROVIDER"

DEFAULT_REQUIRED_HEADERS: List[str] = [
    PAYLINK_API_KEY_HEADER,
    PAYLINK_PROJECT_HEADER,
    PAYLINK_TRACING_HEADER,
    PAYMENT_PROVIDER_HEADER,
]

MPESA_ENV_KEYS = {
    "MPESA_BUSINESS_SHORTCODE": "business_shortcode",
    "MPESA_CONSUMER_SECRET": "consumer_secret",
    "MPESA_CONSUMER_KEY": "consumer_key",
    "MPESA_CALLBACK_URL": "callback_url",
    "MPESA_PASSKEY": "passkey",
    "MPESA_BASE_URL": "base_url",
}


def _normalise_payment_providers(providers: Optional[List[str]]) -> List[str]:
    if not providers:
        return []
    return [str(p).strip() for p in providers if str(p).strip()]


def _is_mpesa_enabled(providers: List[str]) -> bool:
    return any(p.lower() == "mpesa" for p in providers)


# ---------------------------------------------------------------------------
# M-Pesa config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MpesaSettings:
    business_shortcode: Optional[str]
    consumer_secret: Optional[str]
    consumer_key: Optional[str]
    callback_url: Optional[str]
    passkey: Optional[str]
    base_url: Optional[str]

    @classmethod
    def from_environment(cls) -> MpesaSettings:
        kwargs = {
            attr_name: os.getenv(env_key)
            for env_key, attr_name in MPESA_ENV_KEYS.items()
        }
        return cls(**kwargs)  # type: ignore[arg-type]

    def ensure_complete(self) -> None:
        missing = [
            env_key
            for env_key, attr_name in MPESA_ENV_KEYS.items()
            if getattr(self, attr_name) in (None, "")
        ]
        if missing:
            raise ValueError(f"Missing M-Pesa settings: {', '.join(missing)}")

    def as_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        for env_key, attr_name in MPESA_ENV_KEYS.items():
            value = getattr(self, attr_name)
            if value:
                headers[env_key] = value
        return headers

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            env_key: getattr(self, attr_name)
            for env_key, attr_name in MPESA_ENV_KEYS.items()
        }


# ---------------------------------------------------------------------------
# Monetization config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MonetizationSettings:
    wallet_connection_string: str
    transport: str

    @staticmethod
    def ensure(
        *,
        wallet_connection_string: str,
        transport: str,
    ) -> MonetizationSettings:
        if not wallet_connection_string:
            raise ValueError("`wallet_connection_string` is required for monetization.")
        if not transport:
            raise ValueError("`transport` is required for monetization.")
        return MonetizationSettings(
            wallet_connection_string=wallet_connection_string,
            transport=transport,
        )

    def as_headers(self) -> Dict[str, str]:
        return {
            "WALLET_CONNECTION_STRING": self.wallet_connection_string,
            "MONETIZATION_TRANSPORT": self.transport,
        }

    def as_dict(self) -> Dict[str, str]:
        return {
            "WALLET_CONNECTION_STRING": self.wallet_connection_string,
            "MONETIZATION_TRANSPORT": self.transport,
        }

    def required_headers(self) -> List[str]:
        return ["WALLET_CONNECTION_STRING", "MONETIZATION_TRANSPORT"]


# ---------------------------------------------------------------------------
# Main PayLink config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PayLinkConfig:
    base_url: str
    api_key: Optional[str]
    tracing: Optional[str]
    project: Optional[str]
    payment_provider: List[str] = field(default_factory=list)
    required_headers: List[str] = field(default_factory=lambda: DEFAULT_REQUIRED_HEADERS.copy())
    headers: Dict[str, str] = field(default_factory=dict)
    mpesa_settings: Optional[MpesaSettings] = None
    monetization_settings: Optional[MonetizationSettings] = None

    # --------- Construction helpers ---------

    @classmethod
    def resolve(
        cls,
        *,
        base_url: str,
        api_key: Optional[str],
        tracing: Optional[str],
        project: Optional[str],
        payment_provider: Optional[List[str]],
        required_headers: Optional[List[str]],
    ) -> PayLinkConfig:
        resolved_api_key = api_key or os.getenv(PAYLINK_API_KEY_HEADER)
        resolved_tracing = (tracing or os.getenv(PAYLINK_TRACING_HEADER) or "").strip()
        resolved_project = project or os.getenv(PAYLINK_PROJECT_HEADER)
        resolved_payment_provider = (
            _normalise_payment_providers(payment_provider)
            if payment_provider is not None
            else cls._providers_from_environment()
        )

        mpesa_settings: Optional[MpesaSettings] = None
        if _is_mpesa_enabled(resolved_payment_provider):
            mpesa_settings = MpesaSettings.from_environment()
            mpesa_settings.ensure_complete()

        monetization_settings: Optional[MonetizationSettings] = None

        headers = cls._build_headers(
            api_key=resolved_api_key,
            tracing=resolved_tracing,
            project=resolved_project,
            payment_provider=resolved_payment_provider,
            mpesa_settings=mpesa_settings,
            monetization_settings=monetization_settings,
        )

        return cls(
            base_url=base_url,
            api_key=resolved_api_key,
            tracing=resolved_tracing,
            project=resolved_project,
            payment_provider=resolved_payment_provider,
            required_headers=(
                required_headers if required_headers is not None else DEFAULT_REQUIRED_HEADERS.copy()
            ),
            headers=headers,
            mpesa_settings=mpesa_settings,
            monetization_settings=monetization_settings,
        )

    @staticmethod
    def _providers_from_environment() -> List[str]:
        payload = os.getenv(PAYMENT_PROVIDER_HEADER, "[]")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return _normalise_payment_providers(parsed)
        return []

    @staticmethod
    def _build_headers(
        *,
        api_key: Optional[str],
        tracing: Optional[str],
        project: Optional[str],
        payment_provider: List[str],
        mpesa_settings: Optional[MpesaSettings],
        monetization_settings: Optional[MonetizationSettings],
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {}

        if api_key:
            headers[PAYLINK_API_KEY_HEADER] = api_key
        if tracing and tracing.lower() == "enabled":
            headers[PAYLINK_TRACING_HEADER] = "enabled"
        if project:
            headers[PAYLINK_PROJECT_HEADER] = project
        if payment_provider:
            headers[PAYMENT_PROVIDER_HEADER] = json.dumps(payment_provider)

        if mpesa_settings:
            headers.update(mpesa_settings.as_headers())
        if monetization_settings:
            headers.update(monetization_settings.as_headers())

        return headers

    # --------- Convenience accessors ---------

    def mpesa_settings_dict(self) -> Dict[str, Optional[str]]:
        return self.mpesa_settings.as_dict() if self.mpesa_settings else {}

    def monetization_settings_dict(self) -> Dict[str, str]:
        return self.monetization_settings.as_dict() if self.monetization_settings else {}

    # --------- Immutable "with_*" helpers ---------

    def with_monetization(
        self,
        *,
        wallet_connection_string: str,
        transport: str,
        required: Optional[List[str]] = None,
    ) -> PayLinkConfig:
        settings = MonetizationSettings.ensure(
            wallet_connection_string=wallet_connection_string,
            transport=transport,
        )

        # merge required headers
        required_headers = list(self.required_headers)
        for header in settings.required_headers():
            if header not in required_headers:
                required_headers.append(header)
        if required:
            for header in required:
                if header not in required_headers:
                    required_headers.append(header)

        headers = dict(self.headers)
        headers.update(settings.as_headers())

        return PayLinkConfig(
            base_url=self.base_url,
            api_key=self.api_key,
            tracing=self.tracing,
            project=self.project,
            payment_provider=list(self.payment_provider),
            required_headers=required_headers,
            headers=headers,
            mpesa_settings=self.mpesa_settings,
            monetization_settings=settings,
        )
