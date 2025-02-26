"""This package contains a scaffold of a model."""

from enum import Enum
from typing import Any
from collections import deque

from pydantic import conlist
from aea.skills.base import Model

from packages.zarathustra.skills.asylum_abci_app import PydanticModel
from packages.eightballer.protocols.chatroom.message import ChatroomMessage


MAX_QUEUE_LENGTH = 1_000


class LLMActions(Enum):
    """LLMActions."""

    WORKFLOW = "workflow"
    REPLY = "reply"


class AsylumStrategy(Model):
    """This class models the AdvancedDataRequest skill."""

    new_users: deque[dict] = deque(maxlen=MAX_QUEUE_LENGTH)
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


class AgentPersona(Model, PydanticModel):
    """AgentPersona."""

    github_username: str
    role: str
    github_repositories: conlist(str, min_length=1)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize agent persona."""
        pydantic_kwargs = {k: kwargs.pop(k) for k in self.__fields__}
        PydanticModel.__init__(self, **pydantic_kwargs)
        Model.__init__(self, **kwargs)
