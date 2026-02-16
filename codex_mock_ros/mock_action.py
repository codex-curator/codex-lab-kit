"""
Mock action server/client — async goal execution with feedback and cancellation.
"""

from __future__ import annotations

import enum
import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GoalStatus(enum.Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass
class GoalHandle:
    goal_id: str
    request: Any
    status: GoalStatus = GoalStatus.PENDING
    result: Any = None
    feedback_history: List[Any] = field(default_factory=list)
    _cancel_requested: bool = False

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    def request_cancel(self) -> None:
        self._cancel_requested = True


class MockActionServer:
    """Action server that executes goals in background threads."""

    def __init__(
        self,
        action_name: str,
        execute_callback: Callable[[GoalHandle, Callable[[Any], None]], Any],
    ) -> None:
        self.action_name = action_name
        self._execute_callback = execute_callback
        self._goals: Dict[str, GoalHandle] = {}
        self._lock = threading.Lock()
        logger.debug("ActionServer created: %s", action_name)

    def accept_goal(self, request: Any) -> GoalHandle:
        goal_id = str(uuid.uuid4())[:8]
        handle = GoalHandle(goal_id=goal_id, request=request)
        with self._lock:
            self._goals[goal_id] = handle
        logger.debug("Goal accepted: %s on %s", goal_id, self.action_name)

        thread = threading.Thread(
            target=self._run_goal,
            args=(handle,),
            daemon=True,
        )
        thread.start()
        return handle

    def _run_goal(self, handle: GoalHandle) -> None:
        handle.status = GoalStatus.EXECUTING

        def publish_feedback(feedback: Any) -> None:
            handle.feedback_history.append(feedback)
            logger.debug(
                "Feedback on %s/%s: %s",
                self.action_name,
                handle.goal_id,
                feedback,
            )

        try:
            result = self._execute_callback(handle, publish_feedback)
            if handle.cancel_requested:
                handle.status = GoalStatus.CANCELED
                handle.result = None
            else:
                handle.status = GoalStatus.SUCCEEDED
                handle.result = result
        except Exception as exc:
            handle.status = GoalStatus.FAILED
            handle.result = str(exc)
            logger.exception("Goal %s failed", handle.goal_id)

    def get_goal(self, goal_id: str) -> Optional[GoalHandle]:
        with self._lock:
            return self._goals.get(goal_id)


class MockActionClient:
    """Client for sending goals to a MockActionServer."""

    def __init__(self, server: MockActionServer) -> None:
        self._server = server

    def send_goal(
        self,
        request: Any,
        feedback_callback: Optional[Callable[[Any], None]] = None,
    ) -> GoalHandle:
        handle = self._server.accept_goal(request)
        if feedback_callback is not None:
            # Poll feedback in background
            thread = threading.Thread(
                target=self._relay_feedback,
                args=(handle, feedback_callback),
                daemon=True,
            )
            thread.start()
        return handle

    def _relay_feedback(
        self,
        handle: GoalHandle,
        callback: Callable[[Any], None],
    ) -> None:
        seen = 0
        while handle.status in (GoalStatus.PENDING, GoalStatus.EXECUTING):
            fb = handle.feedback_history[seen:]
            for item in fb:
                callback(item)
            seen += len(fb)
            threading.Event().wait(0.01)
        # Deliver any remaining feedback
        for item in handle.feedback_history[seen:]:
            callback(item)

    def cancel_goal(self, handle: GoalHandle) -> None:
        handle.request_cancel()
        logger.debug("Cancel requested for goal %s", handle.goal_id)

    def wait_for_result(self, handle: GoalHandle, timeout: float = 30.0) -> GoalHandle:
        deadline = threading.Event()
        deadline.wait(0)  # no-op
        import time

        start = time.monotonic()
        while handle.status in (GoalStatus.PENDING, GoalStatus.EXECUTING):
            if time.monotonic() - start > timeout:
                logger.warning("Timeout waiting for goal %s", handle.goal_id)
                break
            time.sleep(0.01)
        return handle
