"""
Configuration helpers for the PayLink SDK.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except Exception:
    # It's okay if python-dotenv is not installed; env vars can be provided
    # by the surrounding environment.
    pass


def _normalise_payment_providers(providers: Optional[List[str]]) -> List[str]:
    if not providers:
        return []
    return [str(provider).strip() for provider in providers if str(provider).strip()]


def _is_mpesa_enabled(providers: List[str]) -> bool:
    return any(provider.lower() == "mpesa" for provider in providers)


@dataclass(frozen=True)
class MpesaSettings:
    business_shortcode: Optional[str]
    consumer_secret: Optional[str]
    consumer_key: Optional[str]
    callback_url: Optional[str]
    passkey: Optional[str]
    base_url: Optional[str]

    @classmethod
    def from_environment(cls) -> "MpesaSettings":
        return cls(
            business_shortcode=os.getenv("MPESA_BUSINESS_SHORTCODE"),
            consumer_secret=os.getenv("MPESA_CONSUMER_SECRET"),
            consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
            callback_url=os.getenv("MPESA_CALLBACK_URL"),
            passkey=os.getenv("MPESA_PASSKEY"),
            base_url=os.getenv("MPESA_BASE_URL"),
        )

    def ensure_complete(self) -> None:
        missing = [
            name
            for name, value in {
                "MPESA_BUSINESS_SHORTCODE": self.business_shortcode,
                "MPESA_CONSUMER_SECRET": self.consumer_secret,
                "MPESA_CONSUMER_KEY": self.consumer_key,
                "MPESA_CALLBACK_URL": self.callback_url,
                "MPESA_PASSKEY": self.passkey,
                "MPESA_BASE_URL": self.base_url,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing M-Pesa settings: {', '.join(missing)}")

    def as_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.business_shortcode:
            headers["MPESA_BUSINESS_SHORTCODE"] = self.business_shortcode
        if self.consumer_secret:
            headers["MPESA_CONSUMER_SECRET"] = self.consumer_secret
        if self.consumer_key:
            headers["MPESA_CONSUMER_KEY"] = self.consumer_key
        if self.callback_url:
            headers["MPESA_CALLBACK_URL"] = self.callback_url
        if self.passkey:
            headers["MPESA_PASSKEY"] = self.passkey
        if self.base_url:
            headers["MPESA_BASE_URL"] = self.base_url
        return headers

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "MPESA_BUSINESS_SHORTCODE": self.business_shortcode,
            "MPESA_CONSUMER_SECRET": self.consumer_secret,
            "MPESA_CONSUMER_KEY": self.consumer_key,
            "MPESA_CALLBACK_URL": self.callback_url,
            "MPESA_PASSKEY": self.passkey,
            "MPESA_BASE_URL": self.base_url,
        }


DEFAULT_REQUIRED_HEADERS = [
    "PAYLINK_API_KEY",
    "PAYLINK_PROJECT",
    "PAYLINK_TRACING",
    "PAYMENT_PROVIDER",
]


@dataclass
class PayLinkConfig:
    base_url: str
    api_key: Optional[str]
    tracing: Optional[str]
    project: Optional[str]
    payment_provider: List[str] = field(default_factory=list)
    required_headers: Optional[List[str]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    mpesa_settings: Optional[MpesaSettings] = None
    monitization_settings: Optional["MonitizationSettings"] = None

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
    ) -> "PayLinkConfig":
        resolved_api_key = api_key or os.getenv("PAYLINK_API_KEY")
        resolved_tracing = (tracing or os.getenv("PAYLINK_TRACING") or "").strip()
        resolved_project = project or os.getenv("PAYLINK_PROJECT")
        resolved_payment_provider = (
            _normalise_payment_providers(payment_provider)
            if payment_provider is not None
            else cls._providers_from_environment()
        )

        config = cls(
            base_url=base_url,
            api_key=resolved_api_key,
            tracing=resolved_tracing,
            project=resolved_project,
            payment_provider=resolved_payment_provider,
            required_headers=(
                required_headers
                if required_headers is not None
                else DEFAULT_REQUIRED_HEADERS.copy()
            ),
        )

        config.mpesa_settings = None
        config.monitization_settings = None
        if _is_mpesa_enabled(config.payment_provider):
            mpesa_settings = MpesaSettings.from_environment()
            mpesa_settings.ensure_complete()
            config.mpesa_settings = mpesa_settings

        config.headers = config._build_headers()
        return config

    @staticmethod
    def _providers_from_environment() -> List[str]:
        payload = os.getenv("PAYMENT_PROVIDER", "[]")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return _normalise_payment_providers(parsed)
        return []

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}

        if self.api_key:
            headers["PAYLINK_API_KEY"] = self.api_key
        if self.tracing and self.tracing.lower() == "enabled":
            headers["PAYLINK_TRACING"] = "enabled"
        if self.project:
            headers["PAYLINK_PROJECT"] = self.project
        if self.payment_provider:
            headers["PAYMENT_PROVIDER"] = json.dumps(self.payment_provider)

        if self.mpesa_settings:
            headers.update(self.mpesa_settings.as_headers())
        if self.monitization_settings:
            headers.update(self.monitization_settings.as_headers())

        return headers

    def mpesa_settings_dict(self) -> Dict[str, Optional[str]]:
        if not self.mpesa_settings:
            return {}
        return self.mpesa_settings.as_dict()

    def monitization_settings_dict(self) -> Dict[str, str]:
        if not self.monitization_settings:
            return {}
        return self.monitization_settings.as_dict()

    def with_monitization(
        self,
        *,
        wallet_connection_string: str,
        transport: str,
        required: Optional[List[str]] = None,
    ) -> "PayLinkConfig":
        settings = MonitizationSettings.ensure(
            wallet_connection_string=wallet_connection_string,
            transport=transport,
        )

        self.monitization_settings = settings
        if self.required_headers is not None:
            required_headers = self.required_headers.copy()
            required_headers.extend(
                header for header in settings.required_headers() if header not in required_headers
            )
            if required:
                required_headers.extend(
                    header for header in required if header not in required_headers
                )
            self.required_headers = required_headers

        self.headers.update(settings.as_headers())
        return self


@dataclass(frozen=True)
class MonitizationSettings:
    wallet_connection_string: str
    transport: str

    @staticmethod
    def ensure(
        *,
        wallet_connection_string: str,
        transport: str,
    ) -> "MonitizationSettings":
        if not wallet_connection_string:
            raise ValueError(
                "`wallet_connection_string` is required when configuring monetization."
            )
        if not transport:
            raise ValueError("`transport` is required when configuring monetization.")
        return MonitizationSettings(
            wallet_connection_string=wallet_connection_string,
            transport=transport,
        )

    def as_headers(self) -> Dict[str, str]:
        return {
            "WALLET_CONNECTION_STRING": self.wallet_connection_string,
            "MONITIZATION_TRANSPORT": self.transport,
        }

    def as_dict(self) -> Dict[str, str]:
        return {
            "WALLET_CONNECTION_STRING": self.wallet_connection_string,
            "MONITIZATION_TRANSPORT": self.transport,
        }

    def required_headers(self) -> List[str]:
        return ["WALLET_CONNECTION_STRING", "MONITIZATION_TRANSPORT"]

