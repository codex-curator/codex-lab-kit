"""
MockNode — ties together message bus, services, actions, and logging.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from .mock_pubsub import MockMessageBus, QoSProfile
from .mock_service import MockServiceRegistry
from .mock_action import MockActionServer, MockActionClient


class MockNode:
    """Lightweight node abstraction matching the rclpy.Node interface subset."""

    def __init__(
        self,
        node_name: str,
        bus: MockMessageBus,
        service_registry: MockServiceRegistry,
    ) -> None:
        self._name = node_name
        self._bus = bus
        self._service_registry = service_registry
        self._logger = logging.getLogger(f"ros2.{node_name}")
        self._action_servers: dict[str, MockActionServer] = {}

    @property
    def name(self) -> str:
        return self._name

    def get_logger(self) -> logging.Logger:
        return self._logger

    # --- Pub/Sub ---

    def create_publisher(self, topic: str, qos: Optional[QoSProfile] = None) -> "_MockPublisher":
        return _MockPublisher(self._bus, topic, qos or QoSProfile())

    def create_subscription(
        self,
        topic: str,
        callback: Callable[[Any], None],
        qos: Optional[QoSProfile] = None,
    ) -> Any:
        return self._bus.subscribe(topic, callback, qos)

    # --- Services ---

    def create_service(
        self,
        service_name: str,
        handler: Callable[[Any], Any],
    ) -> None:
        self._service_registry.register_service(service_name, handler)

    def call_service(self, service_name: str, request: Any) -> Any:
        return self._service_registry.call_service(service_name, request)

    # --- Actions ---

    def create_action_server(
        self,
        action_name: str,
        execute_callback: Callable,
    ) -> MockActionServer:
        server = MockActionServer(action_name, execute_callback)
        self._action_servers[action_name] = server
        return server

    def create_action_client(
        self,
        action_name: str,
    ) -> MockActionClient:
        server = self._action_servers.get(action_name)
        if server is None:
            raise ValueError(
                f"No action server registered for '{action_name}'. "
                "Create the server before the client."
            )
        return MockActionClient(server)

    def destroy(self) -> None:
        self._logger.info("Node '%s' destroyed.", self._name)


class _MockPublisher:
    """Thin wrapper returned by create_publisher."""

    def __init__(self, bus: MockMessageBus, topic: str, qos: QoSProfile) -> None:
        self._bus = bus
        self._topic = topic
        self._qos = qos

    def publish(self, message: Any) -> None:
        self._bus.publish(self._topic, message, self._qos)

    @property
    def topic(self) -> str:
        return self._topic
