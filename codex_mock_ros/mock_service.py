"""
Mock service layer — synchronous request/response pattern.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when a service call fails."""


class MockServiceRegistry:
    """In-process service request/response registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_service(
        self,
        service_name: str,
        handler: Callable[[Any], Any],
    ) -> None:
        with self._lock:
            if service_name in self._handlers:
                raise ValueError(f"Service already registered: {service_name}")
            self._handlers[service_name] = handler
        logger.debug("Registered service: %s", service_name)

    def unregister_service(self, service_name: str) -> None:
        with self._lock:
            self._handlers.pop(service_name, None)

    def call_service(self, service_name: str, request: Any) -> Any:
        with self._lock:
            handler = self._handlers.get(service_name)
        if handler is None:
            raise ServiceError(f"Service not found: {service_name}")
        try:
            return handler(request)
        except Exception as exc:
            raise ServiceError(
                f"Service {service_name} raised: {exc}"
            ) from exc

    def has_service(self, service_name: str) -> bool:
        with self._lock:
            return service_name in self._handlers

    def list_services(self) -> list[str]:
        with self._lock:
            return list(self._handlers.keys())
