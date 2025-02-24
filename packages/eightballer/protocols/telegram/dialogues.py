"""
This module contains the classes required for telegram dialogue management.

- TelegramDialogue: The dialogue class maintains state of a dialogue and manages it.
- TelegramDialogues: The dialogues class keeps track of all dialogues.
"""

from abc import ABC
from typing import Dict, Type, Callable, FrozenSet, cast

from aea.common import Address
from aea.skills.base import Model
from aea.protocols.base import Message
from aea.protocols.dialogue.base import Dialogue, Dialogues, DialogueLabel
from packages.eightballer.protocols.telegram.message import TelegramMessage


def _role_from_first_message(message: Message, sender: Address) -> Dialogue.Role:
    """Infer the role of the agent from an incoming/outgoing first message"""
    del sender, message
    return TelegramDialogue.Role.AGENT


class TelegramDialogue(Dialogue):
    """The telegram dialogue class maintains state of a dialogue and manages it."""

    INITIAL_PERFORMATIVES: FrozenSet[Message.Performative] = frozenset(
        {TelegramMessage.Performative.SEND_MESSAGE, TelegramMessage.Performative.RECEIVE_MESSAGE}
    )
    TERMINAL_PERFORMATIVES: FrozenSet[Message.Performative] = frozenset(
        {
            TelegramMessage.Performative.MESSAGE_SENT,
            TelegramMessage.Performative.NEW_MESSAGE,
            TelegramMessage.Performative.ERROR,
        }
    )
    VALID_REPLIES: Dict[Message.Performative, FrozenSet[Message.Performative]] = {
        TelegramMessage.Performative.ERROR: frozenset(),
        TelegramMessage.Performative.MESSAGE_SENT: frozenset(),
        TelegramMessage.Performative.NEW_MESSAGE: frozenset(),
        TelegramMessage.Performative.RECEIVE_MESSAGE: frozenset(
            {TelegramMessage.Performative.NEW_MESSAGE, TelegramMessage.Performative.ERROR}
        ),
        TelegramMessage.Performative.SEND_MESSAGE: frozenset(
            {TelegramMessage.Performative.MESSAGE_SENT, TelegramMessage.Performative.ERROR}
        ),
    }

    class Role(Dialogue.Role):
        """This class defines the agent's role in a telegram dialogue."""

        AGENT = "agent"

    class EndState(Dialogue.EndState):
        """This class defines the end states of a telegram dialogue."""

        MESSAGE_SENT = 0
        NEW_MESSAGE = 1
        ERROR = 2

    def __init__(
        self,
        dialogue_label: DialogueLabel,
        self_address: Address,
        role: Dialogue.Role,
        message_class: Type[TelegramMessage] = TelegramMessage,
    ) -> None:
        """
        Initialize a dialogue.



        Args:
               dialogue_label:  the identifier of the dialogue
               self_address:  the address of the entity for whom this dialogue is maintained
               role:  the role of the agent this dialogue is maintained for
               message_class:  the message class used

        """
        Dialogue.__init__(
            self, dialogue_label=dialogue_label, message_class=message_class, self_address=self_address, role=role
        )


class BaseTelegramDialogues(Dialogues, ABC):
    """This class keeps track of all telegram dialogues."""

    END_STATES = frozenset(
        {TelegramDialogue.EndState.MESSAGE_SENT, TelegramDialogue.EndState.NEW_MESSAGE, TelegramDialogue.EndState.ERROR}
    )
    _keep_terminal_state_dialogues = False

    def __init__(
        self,
        self_address: Address,
        role_from_first_message: Callable[[Message, Address], Dialogue.Role] = _role_from_first_message,
        dialogue_class: Type[TelegramDialogue] = TelegramDialogue,
    ) -> None:
        """
        Initialize dialogues.



        Args:
               self_address:  the address of the entity for whom dialogues are maintained
               dialogue_class:  the dialogue class used
               role_from_first_message:  the callable determining role from first message

        """
        Dialogues.__init__(
            self,
            self_address=self_address,
            end_states=cast(FrozenSet[Dialogue.EndState], self.END_STATES),
            message_class=TelegramMessage,
            dialogue_class=dialogue_class,
            role_from_first_message=role_from_first_message,
        )


class TelegramDialogues(BaseTelegramDialogues, Model):
    """This class defines the dialogues used in Telegram."""

    def __init__(self, **kwargs):
        """Initialize dialogues."""
        Model.__init__(self, keep_terminal_state_dialogues=False, **kwargs)
        BaseTelegramDialogues.__init__(
            self, self_address=str(self.context.skill_id), role_from_first_message=_role_from_first_message
        )
