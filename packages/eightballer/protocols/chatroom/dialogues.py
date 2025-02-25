"""This module contains the classes required for chatroom dialogue management.

- ChatroomDialogue: The dialogue class maintains state of a dialogue and manages it.
- ChatroomDialogues: The dialogues class keeps track of all dialogues.
"""

from abc import ABC
from typing import cast
from collections.abc import Callable

from aea.common import Address
from aea.skills.base import Model
from aea.protocols.base import Message
from aea.protocols.dialogue.base import Dialogue, Dialogues, DialogueLabel

from packages.eightballer.protocols.chatroom.message import ChatroomMessage


def _role_from_first_message(message: Message, sender: Address) -> Dialogue.Role:
    """Infer the role of the agent from an incoming/outgoing first message."""
    del sender, message
    return ChatroomDialogue.Role.AGENT


class ChatroomDialogue(Dialogue):
    """The chatroom dialogue class maintains state of a dialogue and manages it."""

    INITIAL_PERFORMATIVES: frozenset[Message.Performative] = frozenset(
        {
            ChatroomMessage.Performative.MESSAGE,
            ChatroomMessage.Performative.SUBSCRIBE,
            ChatroomMessage.Performative.UNSUBSCRIBE,
            ChatroomMessage.Performative.GET_CHANNELS,
        }
    )
    TERMINAL_PERFORMATIVES: frozenset[Message.Performative] = frozenset(
        {
            ChatroomMessage.Performative.UNSUBSCRIPTION_RESULT,
            ChatroomMessage.Performative.SUBSCRIPTION_RESULT,
            ChatroomMessage.Performative.MESSAGE_SENT,
            ChatroomMessage.Performative.ERROR,
            ChatroomMessage.Performative.CHANNELS,
        }
    )
    VALID_REPLIES: dict[Message.Performative, frozenset[Message.Performative]] = {
        ChatroomMessage.Performative.CHANNELS: frozenset(),
        ChatroomMessage.Performative.ERROR: frozenset(),
        ChatroomMessage.Performative.GET_CHANNELS: frozenset(
            {ChatroomMessage.Performative.CHANNELS, ChatroomMessage.Performative.ERROR}
        ),
        ChatroomMessage.Performative.MESSAGE: frozenset(
            {ChatroomMessage.Performative.MESSAGE_SENT, ChatroomMessage.Performative.ERROR}
        ),
        ChatroomMessage.Performative.MESSAGE_SENT: frozenset(),
        ChatroomMessage.Performative.SUBSCRIBE: frozenset(
            {ChatroomMessage.Performative.SUBSCRIPTION_RESULT, ChatroomMessage.Performative.ERROR}
        ),
        ChatroomMessage.Performative.SUBSCRIPTION_RESULT: frozenset(),
        ChatroomMessage.Performative.UNSUBSCRIBE: frozenset(
            {ChatroomMessage.Performative.UNSUBSCRIPTION_RESULT, ChatroomMessage.Performative.ERROR}
        ),
        ChatroomMessage.Performative.UNSUBSCRIPTION_RESULT: frozenset(),
    }

    class Role(Dialogue.Role):
        """This class defines the agent's role in a chatroom dialogue."""

        AGENT = "agent"

    class EndState(Dialogue.EndState):
        """This class defines the end states of a chatroom dialogue."""

        UNSUBSCRIPTION_RESULT = 0
        SUBSCRIPTION_RESULT = 1
        MESSAGE_SENT = 2
        ERROR = 3
        CHANNELS = 4

    def __init__(
        self,
        dialogue_label: DialogueLabel,
        self_address: Address,
        role: Dialogue.Role,
        message_class: type[ChatroomMessage] = ChatroomMessage,
    ) -> None:
        """Initialize a dialogue.



        Args:
        ----
               dialogue_label:  the identifier of the dialogue
               self_address:  the address of the entity for whom this dialogue is maintained
               role:  the role of the agent this dialogue is maintained for
               message_class:  the message class used

        """
        Dialogue.__init__(
            self, dialogue_label=dialogue_label, message_class=message_class, self_address=self_address, role=role
        )


class BaseChatroomDialogues(Dialogues, ABC):
    """This class keeps track of all chatroom dialogues."""

    END_STATES = frozenset(
        {
            ChatroomDialogue.EndState.UNSUBSCRIPTION_RESULT,
            ChatroomDialogue.EndState.SUBSCRIPTION_RESULT,
            ChatroomDialogue.EndState.MESSAGE_SENT,
            ChatroomDialogue.EndState.ERROR,
            ChatroomDialogue.EndState.CHANNELS,
        }
    )
    _keep_terminal_state_dialogues = False

    def __init__(
        self,
        self_address: Address,
        role_from_first_message: Callable[[Message, Address], Dialogue.Role] = _role_from_first_message,
        dialogue_class: type[ChatroomDialogue] = ChatroomDialogue,
    ) -> None:
        """Initialize dialogues.



        Args:
        ----
               self_address:  the address of the entity for whom dialogues are maintained
               dialogue_class:  the dialogue class used
               role_from_first_message:  the callable determining role from first message

        """
        Dialogues.__init__(
            self,
            self_address=self_address,
            end_states=cast(frozenset[Dialogue.EndState], self.END_STATES),
            message_class=ChatroomMessage,
            dialogue_class=dialogue_class,
            role_from_first_message=role_from_first_message,
        )


class ChatroomDialogues(BaseChatroomDialogues, Model):
    """This class defines the dialogues used in Chatroom."""

    def __init__(self, **kwargs):
        """Initialize dialogues."""
        Model.__init__(self, keep_terminal_state_dialogues=False, **kwargs)
        BaseChatroomDialogues.__init__(
            self, self_address=str(self.context.skill_id), role_from_first_message=_role_from_first_message
        )
