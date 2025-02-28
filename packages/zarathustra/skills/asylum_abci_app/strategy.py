"""This package contains a scaffold of a model."""

from enum import Enum
from pathlib import Path
from typing import Any
from collections import deque

from aea.skills.base import Model

from packages.eightballer.protocols.chatroom.message import ChatroomMessage


MESSAGE_HISTORY_SIZE = 10
MAX_QUEUE_LENGTH = 1_000


class LLMActions(Enum):
    """LLMActions."""

    WORKFLOW = "workflow"
    REPLY = "reply"


class AsylumStrategy(Model):
    """This class models the AdvancedDataRequest skill."""

    user_persona: str
    new_users: deque[dict] = deque(maxlen=MAX_QUEUE_LENGTH)
    pending_telegram_messages: deque[ChatroomMessage] = deque(maxlen=MAX_QUEUE_LENGTH)
    current_telegram_thread: deque[ChatroomMessage] = deque(maxlen=MESSAGE_HISTORY_SIZE)
    llm_responses: deque[tuple[LLMActions, str]] = deque(maxlen=MAX_QUEUE_LENGTH)
    pending_workflows: deque[str] = deque(maxlen=MAX_QUEUE_LENGTH)
    telegram_responses: deque[str] = deque(maxlen=MAX_QUEUE_LENGTH)
    data_dir: str

    workflows = {
        "create_new_repo": "create_new_repo.yaml",
        "lint": "lint_repo.yaml",
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize dialogues."""
        self.data_dir= Path(kwargs.pop("data_dir", "data"))
        self.user_persona = ""
        Model.__init__(self, **kwargs)


class AgentPersona(Model):
    """AgentPersona."""

    github_username: str
    role: str
    github_repositories: list[str]
    github_pat: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize agent persona."""
        for key, value in self.__annotations__.items():
            if key in kwargs:
                value = kwargs[key]
                if not value:
                    raise ValueError(f"Missing required parameter: {key} of type {value}")
                setattr(self, key, kwargs[key])
                continue
            raise ValueError(f"Missing required parameter: {key} of type {value}")
        Model.__init__(self, **kwargs)
