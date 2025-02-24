# ------------------------------------------------------------------------------
#
#   Copyright 2025 zarathustra
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains the classes required for llm_chat_completion dialogue management.

- LlmChatCompletionDialogue: The dialogue class maintains state of a dialogue and manages it.
- LlmChatCompletionDialogues: The dialogues class keeps track of all dialogues.
"""

from abc import ABC
from typing import cast
from collections.abc import Callable

from aea.common import Address
from aea.protocols.base import Message
from aea.protocols.dialogue.base import Dialogue, Dialogues, DialogueLabel

from packages.zarathustra.protocols.llm_chat_completion.message import (
    LlmChatCompletionMessage,
)


class LlmChatCompletionDialogue(Dialogue):
    """The llm_chat_completion dialogue class maintains state of a dialogue and manages it."""

    INITIAL_PERFORMATIVES: frozenset[Message.Performative] = frozenset(
        {
            LlmChatCompletionMessage.Performative.CREATE,
            LlmChatCompletionMessage.Performative.RETRIEVE,
            LlmChatCompletionMessage.Performative.UPDATE,
            LlmChatCompletionMessage.Performative.LIST,
            LlmChatCompletionMessage.Performative.DELETE,
        }
    )
    TERMINAL_PERFORMATIVES: frozenset[Message.Performative] = frozenset(
        {LlmChatCompletionMessage.Performative.RESPONSE, LlmChatCompletionMessage.Performative.ERROR}
    )
    VALID_REPLIES: dict[Message.Performative, frozenset[Message.Performative]] = {
        LlmChatCompletionMessage.Performative.CREATE: frozenset(
            {LlmChatCompletionMessage.Performative.RESPONSE, LlmChatCompletionMessage.Performative.ERROR}
        ),
        LlmChatCompletionMessage.Performative.DELETE: frozenset(
            {LlmChatCompletionMessage.Performative.RESPONSE, LlmChatCompletionMessage.Performative.ERROR}
        ),
        LlmChatCompletionMessage.Performative.ERROR: frozenset(),
        LlmChatCompletionMessage.Performative.LIST: frozenset(
            {LlmChatCompletionMessage.Performative.RESPONSE, LlmChatCompletionMessage.Performative.ERROR}
        ),
        LlmChatCompletionMessage.Performative.RESPONSE: frozenset(),
        LlmChatCompletionMessage.Performative.RETRIEVE: frozenset(
            {LlmChatCompletionMessage.Performative.RESPONSE, LlmChatCompletionMessage.Performative.ERROR}
        ),
        LlmChatCompletionMessage.Performative.UPDATE: frozenset(
            {LlmChatCompletionMessage.Performative.RESPONSE, LlmChatCompletionMessage.Performative.ERROR}
        ),
    }

    class Role(Dialogue.Role):
        """This class defines the agent's role in a llm_chat_completion dialogue."""

        CONNECTION = "connection"
        SKILL = "skill"

    class EndState(Dialogue.EndState):
        """This class defines the end states of a llm_chat_completion dialogue."""

        RESPONSE = 0
        ERROR = 1

    def __init__(
        self,
        dialogue_label: DialogueLabel,
        self_address: Address,
        role: Dialogue.Role,
        message_class: type[LlmChatCompletionMessage] = LlmChatCompletionMessage,
    ) -> None:
        """Initialize a dialogue."""
        Dialogue.__init__(
            self,
            dialogue_label=dialogue_label,
            message_class=message_class,
            self_address=self_address,
            role=role,
        )


class LlmChatCompletionDialogues(Dialogues, ABC):
    """This class keeps track of all llm_chat_completion dialogues."""

    END_STATES = frozenset({LlmChatCompletionDialogue.EndState.RESPONSE, LlmChatCompletionDialogue.EndState.ERROR})

    _keep_terminal_state_dialogues = True

    def __init__(
        self,
        self_address: Address,
        role_from_first_message: Callable[[Message, Address], Dialogue.Role],
        dialogue_class: type[LlmChatCompletionDialogue] = LlmChatCompletionDialogue,
    ) -> None:
        """Initialize dialogues."""
        Dialogues.__init__(
            self,
            self_address=self_address,
            end_states=cast(frozenset[Dialogue.EndState], self.END_STATES),
            message_class=LlmChatCompletionMessage,
            dialogue_class=dialogue_class,
            role_from_first_message=role_from_first_message,
        )
