from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence


class ConnectorError(RuntimeError):
    """Base exception for connector failures."""


class ConnectorCredentialsError(ConnectorError):
    """Raised when a connector cannot run because credentials are missing."""

    def __init__(self, message: str, missing: Sequence[str]) -> None:
        super().__init__(message)
        self.missing = tuple(missing)


@dataclass
class ConnectorResponse:
    """Lightweight response structure returned by connectors."""

    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class BaseConnector:
    """Base class that handles credential checks and mock fallbacks."""

    tool_id: str = ""
    requires_credentials: Sequence[str] = ()
    description: str = ""

    def __init__(self, *, allow_mock: bool = True) -> None:
        self.allow_mock = allow_mock

    # ------------------------------------------------------------------ #
    # Credential handling
    # ------------------------------------------------------------------ #
    def has_credentials(self) -> bool:
        return all(os.getenv(name) for name in self.requires_credentials)

    def missing_credentials(self) -> List[str]:
        return [name for name in self.requires_credentials if not os.getenv(name)]

    # ------------------------------------------------------------------ #
    # Invocation
    # ------------------------------------------------------------------ #
    def __call__(self, **kwargs: Any) -> ConnectorResponse:
        if self.has_credentials():
            response = self._invoke_live(**kwargs)
            response.metadata.setdefault("mode", "live")
            return response

        if not self.allow_mock:
            missing = ", ".join(self.missing_credentials())
            raise ConnectorCredentialsError(
                f"{self.tool_id} missing credentials: {missing}", self.missing_credentials()
            )

        response = self._invoke_mock(**kwargs)
        response.metadata.setdefault("mode", "mock")

        warning = self._missing_credentials_warning()
        if warning and warning not in response.warnings:
            response.warnings.append(warning)
        return response

    # ------------------------------------------------------------------ #
    # Required overrides
    # ------------------------------------------------------------------ #
    def _invoke_live(self, **kwargs: Any) -> ConnectorResponse:
        raise NotImplementedError

    def _invoke_mock(self, **kwargs: Any) -> ConnectorResponse:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _missing_credentials_warning(self) -> str:
        missing = ", ".join(self.missing_credentials())
        if not missing:
            missing = "required credentials"
        return f"{self.tool_id} used mock mode because {missing} are not configured."


def sanitize_query(value: str) -> str:
    """Collapse whitespace so mock fallbacks produce stable keys."""
    return " ".join(value.split())
