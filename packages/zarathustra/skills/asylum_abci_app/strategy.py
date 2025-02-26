"""This package contains a scaffold of a model."""

from enum import Enum
from typing import Any
from collections import deque

from aea.skills.base import Model

from packages.eightballer.protocols.chatroom.message import ChatroomMessage


class LLMActions(Enum):
    """LLMActions."""

    WORKFLOW = "workflow"
    REPLY = "reply"


class AsylumStrategy(Model):
    """This class models the AdvancedDataRequest skill."""

    pending_messages: deque[ChatroomMessage] = deque(maxlen=1000)
    llm_responses: deque[Any] = deque(maxlen=1000)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize dialogues."""

        Model.__init__(self, **kwargs)
