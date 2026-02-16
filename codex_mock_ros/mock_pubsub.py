"""
Mock pub/sub layer with thread-safe dispatch and TRANSIENT_LOCAL emulation.
"""

from __future__ import annotations

import enum
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QoSReliability(enum.Enum):
    BEST_EFFORT = "best_effort"
    RELIABLE = "reliable"


class QoSDurability(enum.Enum):
    VOLATILE = "volatile"
    TRANSIENT_LOCAL = "transient_local"


@dataclass
class QoSProfile:
    reliability: QoSReliability = QoSReliability.RELIABLE
    durability: QoSDurability = QoSDurability.VOLATILE
    depth: int = 10


@dataclass
class _Subscription:
    topic: str
    callback: Callable[[Any], None]
    qos: QoSProfile


class MockMessageBus:
    """In-process message bus with topic-based pub/sub."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscriptions: Dict[str, List[_Subscription]] = {}
        self._last_messages: Dict[str, List[Any]] = {}

    def subscribe(
        self,
        topic: str,
        callback: Callable[[Any], None],
        qos: Optional[QoSProfile] = None,
    ) -> _Subscription:
        qos = qos or QoSProfile()
        sub = _Subscription(topic=topic, callback=callback, qos=qos)
        with self._lock:
            self._subscriptions.setdefault(topic, []).append(sub)
            # Deliver latched messages to TRANSIENT_LOCAL subscribers
            if qos.durability == QoSDurability.TRANSIENT_LOCAL:
                for msg in self._last_messages.get(topic, []):
                    try:
                        callback(msg)
                    except Exception:
                        logger.exception(
                            "Error delivering latched message on %s", topic
                        )
        logger.debug("Subscribed to %s (qos=%s)", topic, qos)
        return sub

    def unsubscribe(self, sub: _Subscription) -> None:
        with self._lock:
            subs = self._subscriptions.get(sub.topic, [])
            if sub in subs:
                subs.remove(sub)

    def publish(
        self,
        topic: str,
        message: Any,
        qos: Optional[QoSProfile] = None,
    ) -> None:
        qos = qos or QoSProfile()
        with self._lock:
            subscribers = list(self._subscriptions.get(topic, []))
            # Store for TRANSIENT_LOCAL
            buf = self._last_messages.setdefault(topic, [])
            buf.append(message)
            if len(buf) > qos.depth:
                buf.pop(0)

        logger.debug("Publishing on %s → %d subscriber(s)", topic, len(subscribers))
        for sub in subscribers:
            try:
                sub.callback(message)
            except Exception:
                logger.exception("Error in subscriber callback for %s", topic)

    def get_topic_names(self) -> List[str]:
        with self._lock:
            return list(self._subscriptions.keys())

    def get_subscriber_count(self, topic: str) -> int:
        with self._lock:
            return len(self._subscriptions.get(topic, []))
