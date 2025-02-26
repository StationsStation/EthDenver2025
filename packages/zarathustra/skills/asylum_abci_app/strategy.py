"""This package contains a scaffold of a model."""

from typing import Any
from collections import deque

from aea.skills.base import Model

from packages.eightballer.protocols.chatroom.message import ChatroomMessage


class AsylumStrategy(Model):
    """This class models the AdvancedDataRequest skill."""

    pending_messages: deque[ChatroomMessage] = deque(maxlen=1000)
    llm_responses: deque[Any] = deque(maxlen=1000)

    pending_workflows = []
    telegram_responses = []

    workflows = {
        "create_new_repo": "create_new_repo.yaml",
        "lint": "lint_repo.yaml",
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize dialogues."""

        Model.__init__(self, **kwargs)
