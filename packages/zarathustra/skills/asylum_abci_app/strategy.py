"""This package contains a scaffold of a model."""

from enum import Enum
from typing import Any
from collections import deque

from aea.skills.base import Model

from packages.eightballer.protocols.chatroom.message import ChatroomMessage


MAX_QUEUE_LENGTH = 1_000


class LLMActions(Enum):
    """LLMActions."""

    WORKFLOW = "workflow"
    REPLY = "reply"


class AsylumStrategy(Model):
    """This class models the AdvancedDataRequest skill."""

    pending_telegram_messages: deque[ChatroomMessage] = deque(maxlen=MAX_QUEUE_LENGTH)
    llm_responses: deque[tuple[LLMActions, str]] = deque(maxlen=MAX_QUEUE_LENGTH)
    pending_workflows: deque[str] = deque(maxlen=MAX_QUEUE_LENGTH)
    telegram_responses: deque[str] = deque(maxlen=MAX_QUEUE_LENGTH)

    workflows = {
        "create_new_repo": "create_new_repo.yaml",
        "lint": "lint_repo.yaml",
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize dialogues."""

        Model.__init__(self, **kwargs)
