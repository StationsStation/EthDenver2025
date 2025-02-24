# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2025 eightballer
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

"""This module contains telegram's message definition."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,too-many-branches,not-an-iterable,unidiomatic-typecheck,unsubscriptable-object
import logging
from typing import Any, Dict, Optional, Set, Tuple, cast

from aea.configurations.base import PublicId
from aea.exceptions import AEAEnforceError, enforce
from aea.protocols.base import Message  # type: ignore

from packages.eightballer.protocols.telegram.custom_types import (
    ErrorCode as CustomErrorCode,
)


_default_logger = logging.getLogger(
    "aea.packages.eightballer.protocols.telegram.message"
)

DEFAULT_BODY_SIZE = 4


class TelegramMessage(Message):
    """A protocol for sending and receiving messages using the python-tele-rgram library."""

    protocol_id = PublicId.from_str("eightballer/telegram:0.1.0")
    protocol_specification_id = PublicId.from_str("eightballer/telegram:0.1.0")

    ErrorCode = CustomErrorCode

    class Performative(Message.Performative):
        """Performatives for the telegram protocol."""

        ERROR = "error"
        MESSAGE_SENT = "message_sent"
        NEW_MESSAGE = "new_message"
        RECEIVE_MESSAGE = "receive_message"
        SEND_MESSAGE = "send_message"

        def __str__(self) -> str:
            """Get the string representation."""
            return str(self.value)

    _performatives = {
        "error",
        "message_sent",
        "new_message",
        "receive_message",
        "send_message",
    }
    __slots__: Tuple[str, ...] = tuple()

    class _SlotsCls:
        __slots__ = (
            "chat_id",
            "dialogue_reference",
            "error_code",
            "error_data",
            "error_msg",
            "from_user",
            "id",
            "message_id",
            "parse_mode",
            "performative",
            "reply_markup",
            "status",
            "target",
            "text",
            "timestamp",
        )

    def __init__(
        self,
        performative: Performative,
        dialogue_reference: Tuple[str, str] = ("", ""),
        message_id: int = 1,
        target: int = 0,
        **kwargs: Any,
    ):
        """
        Initialise an instance of TelegramMessage.

        :param message_id: the message id.
        :param dialogue_reference: the dialogue reference.
        :param target: the message target.
        :param performative: the message performative.
        :param **kwargs: extra options.
        """
        super().__init__(
            dialogue_reference=dialogue_reference,
            message_id=message_id,
            target=target,
            performative=TelegramMessage.Performative(performative),
            **kwargs,
        )

    @property
    def valid_performatives(self) -> Set[str]:
        """Get valid performatives."""
        return self._performatives

    @property
    def dialogue_reference(self) -> Tuple[str, str]:
        """Get the dialogue_reference of the message."""
        enforce(self.is_set("dialogue_reference"), "dialogue_reference is not set.")
        return cast(Tuple[str, str], self.get("dialogue_reference"))

    @property
    def message_id(self) -> int:
        """Get the message_id of the message."""
        enforce(self.is_set("message_id"), "message_id is not set.")
        return cast(int, self.get("message_id"))

    @property
    def performative(self) -> Performative:  # type: ignore # noqa: F821
        """Get the performative of the message."""
        enforce(self.is_set("performative"), "performative is not set.")
        return cast(TelegramMessage.Performative, self.get("performative"))

    @property
    def target(self) -> int:
        """Get the target of the message."""
        enforce(self.is_set("target"), "target is not set.")
        return cast(int, self.get("target"))

    @property
    def chat_id(self) -> int:
        """Get the 'chat_id' content from the message."""
        enforce(self.is_set("chat_id"), "'chat_id' content is not set.")
        return cast(int, self.get("chat_id"))

    @property
    def error_code(self) -> CustomErrorCode:
        """Get the 'error_code' content from the message."""
        enforce(self.is_set("error_code"), "'error_code' content is not set.")
        return cast(CustomErrorCode, self.get("error_code"))

    @property
    def error_data(self) -> Dict[str, bytes]:
        """Get the 'error_data' content from the message."""
        enforce(self.is_set("error_data"), "'error_data' content is not set.")
        return cast(Dict[str, bytes], self.get("error_data"))

    @property
    def error_msg(self) -> str:
        """Get the 'error_msg' content from the message."""
        enforce(self.is_set("error_msg"), "'error_msg' content is not set.")
        return cast(str, self.get("error_msg"))

    @property
    def from_user(self) -> str:
        """Get the 'from_user' content from the message."""
        enforce(self.is_set("from_user"), "'from_user' content is not set.")
        return cast(str, self.get("from_user"))

    @property
    def id(self) -> int:
        """Get the 'id' content from the message."""
        enforce(self.is_set("id"), "'id' content is not set.")
        return cast(int, self.get("id"))

    @property
    def parse_mode(self) -> Optional[str]:
        """Get the 'parse_mode' content from the message."""
        return cast(Optional[str], self.get("parse_mode"))

    @property
    def reply_markup(self) -> Optional[str]:
        """Get the 'reply_markup' content from the message."""
        return cast(Optional[str], self.get("reply_markup"))

    @property
    def status(self) -> str:
        """Get the 'status' content from the message."""
        enforce(self.is_set("status"), "'status' content is not set.")
        return cast(str, self.get("status"))

    @property
    def text(self) -> str:
        """Get the 'text' content from the message."""
        enforce(self.is_set("text"), "'text' content is not set.")
        return cast(str, self.get("text"))

    @property
    def timestamp(self) -> int:
        """Get the 'timestamp' content from the message."""
        enforce(self.is_set("timestamp"), "'timestamp' content is not set.")
        return cast(int, self.get("timestamp"))

    def _is_consistent(self) -> bool:
        """Check that the message follows the telegram protocol."""
        try:
            enforce(
                isinstance(self.dialogue_reference, tuple),
                "Invalid type for 'dialogue_reference'. Expected 'tuple'. Found '{}'.".format(
                    type(self.dialogue_reference)
                ),
            )
            enforce(
                isinstance(self.dialogue_reference[0], str),
                "Invalid type for 'dialogue_reference[0]'. Expected 'str'. Found '{}'.".format(
                    type(self.dialogue_reference[0])
                ),
            )
            enforce(
                isinstance(self.dialogue_reference[1], str),
                "Invalid type for 'dialogue_reference[1]'. Expected 'str'. Found '{}'.".format(
                    type(self.dialogue_reference[1])
                ),
            )
            enforce(
                type(self.message_id) is int,
                "Invalid type for 'message_id'. Expected 'int'. Found '{}'.".format(
                    type(self.message_id)
                ),
            )
            enforce(
                type(self.target) is int,
                "Invalid type for 'target'. Expected 'int'. Found '{}'.".format(
                    type(self.target)
                ),
            )

            # Light Protocol Rule 2
            # Check correct performative
            enforce(
                isinstance(self.performative, TelegramMessage.Performative),
                "Invalid 'performative'. Expected either of '{}'. Found '{}'.".format(
                    self.valid_performatives, self.performative
                ),
            )

            # Check correct contents
            actual_nb_of_contents = len(self._body) - DEFAULT_BODY_SIZE
            expected_nb_of_contents = 0
            if self.performative == TelegramMessage.Performative.SEND_MESSAGE:
                expected_nb_of_contents = 2
                enforce(
                    type(self.chat_id) is int,
                    "Invalid type for content 'chat_id'. Expected 'int'. Found '{}'.".format(
                        type(self.chat_id)
                    ),
                )
                enforce(
                    isinstance(self.text, str),
                    "Invalid type for content 'text'. Expected 'str'. Found '{}'.".format(
                        type(self.text)
                    ),
                )
                if self.is_set("parse_mode"):
                    expected_nb_of_contents += 1
                    parse_mode = cast(str, self.parse_mode)
                    enforce(
                        isinstance(parse_mode, str),
                        "Invalid type for content 'parse_mode'. Expected 'str'. Found '{}'.".format(
                            type(parse_mode)
                        ),
                    )
                if self.is_set("reply_markup"):
                    expected_nb_of_contents += 1
                    reply_markup = cast(str, self.reply_markup)
                    enforce(
                        isinstance(reply_markup, str),
                        "Invalid type for content 'reply_markup'. Expected 'str'. Found '{}'.".format(
                            type(reply_markup)
                        ),
                    )
            elif self.performative == TelegramMessage.Performative.RECEIVE_MESSAGE:
                expected_nb_of_contents = 2
                enforce(
                    type(self.chat_id) is int,
                    "Invalid type for content 'chat_id'. Expected 'int'. Found '{}'.".format(
                        type(self.chat_id)
                    ),
                )
                enforce(
                    type(self.id) is int,
                    "Invalid type for content 'id'. Expected 'int'. Found '{}'.".format(
                        type(self.id)
                    ),
                )
            elif self.performative == TelegramMessage.Performative.MESSAGE_SENT:
                expected_nb_of_contents = 2
                enforce(
                    type(self.id) is int,
                    "Invalid type for content 'id'. Expected 'int'. Found '{}'.".format(
                        type(self.id)
                    ),
                )
                enforce(
                    isinstance(self.status, str),
                    "Invalid type for content 'status'. Expected 'str'. Found '{}'.".format(
                        type(self.status)
                    ),
                )
            elif self.performative == TelegramMessage.Performative.NEW_MESSAGE:
                expected_nb_of_contents = 5
                enforce(
                    type(self.chat_id) is int,
                    "Invalid type for content 'chat_id'. Expected 'int'. Found '{}'.".format(
                        type(self.chat_id)
                    ),
                )
                enforce(
                    type(self.id) is int,
                    "Invalid type for content 'id'. Expected 'int'. Found '{}'.".format(
                        type(self.id)
                    ),
                )
                enforce(
                    isinstance(self.text, str),
                    "Invalid type for content 'text'. Expected 'str'. Found '{}'.".format(
                        type(self.text)
                    ),
                )
                enforce(
                    isinstance(self.from_user, str),
                    "Invalid type for content 'from_user'. Expected 'str'. Found '{}'.".format(
                        type(self.from_user)
                    ),
                )
                enforce(
                    type(self.timestamp) is int,
                    "Invalid type for content 'timestamp'. Expected 'int'. Found '{}'.".format(
                        type(self.timestamp)
                    ),
                )
            elif self.performative == TelegramMessage.Performative.ERROR:
                expected_nb_of_contents = 3
                enforce(
                    isinstance(self.error_code, CustomErrorCode),
                    "Invalid type for content 'error_code'. Expected 'ErrorCode'. Found '{}'.".format(
                        type(self.error_code)
                    ),
                )
                enforce(
                    isinstance(self.error_msg, str),
                    "Invalid type for content 'error_msg'. Expected 'str'. Found '{}'.".format(
                        type(self.error_msg)
                    ),
                )
                enforce(
                    isinstance(self.error_data, dict),
                    "Invalid type for content 'error_data'. Expected 'dict'. Found '{}'.".format(
                        type(self.error_data)
                    ),
                )
                for key_of_error_data, value_of_error_data in self.error_data.items():
                    enforce(
                        isinstance(key_of_error_data, str),
                        "Invalid type for dictionary keys in content 'error_data'. Expected 'str'. Found '{}'.".format(
                            type(key_of_error_data)
                        ),
                    )
                    enforce(
                        isinstance(value_of_error_data, bytes),
                        "Invalid type for dictionary values in content 'error_data'. Expected 'bytes'. Found '{}'.".format(
                            type(value_of_error_data)
                        ),
                    )

            # Check correct content count
            enforce(
                expected_nb_of_contents == actual_nb_of_contents,
                "Incorrect number of contents. Expected {}. Found {}".format(
                    expected_nb_of_contents, actual_nb_of_contents
                ),
            )

            # Light Protocol Rule 3
            if self.message_id == 1:
                enforce(
                    self.target == 0,
                    "Invalid 'target'. Expected 0 (because 'message_id' is 1). Found {}.".format(
                        self.target
                    ),
                )
        except (AEAEnforceError, ValueError, KeyError) as e:
            _default_logger.error(str(e))
            return False

        return True
