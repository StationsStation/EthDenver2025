# -*- coding: utf-8 -*-
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

"""This module contains llm_chat_completion's message definition."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,too-many-branches,not-an-iterable,unidiomatic-typecheck,unsubscriptable-object
import logging
from typing import Any, Set, Tuple, cast

from aea.configurations.base import PublicId
from aea.exceptions import AEAEnforceError, enforce
from aea.protocols.base import Message  # type: ignore

from packages.zarathustra.protocols.llm_chat_completion.custom_types import (
    ErrorCode as CustomErrorCode,
)
from packages.zarathustra.protocols.llm_chat_completion.custom_types import (
    Kwargs as CustomKwargs,
)
from packages.zarathustra.protocols.llm_chat_completion.custom_types import (
    Messages as CustomMessages,
)


_default_logger = logging.getLogger("aea.packages.zarathustra.protocols.llm_chat_completion.message")

DEFAULT_BODY_SIZE = 4


class LlmChatCompletionMessage(Message):
    """A protocol for openAI LLM chat completion."""

    protocol_id = PublicId.from_str("zarathustra/llm_chat_completion:1.0.0")
    protocol_specification_id = PublicId.from_str("zarathustra/llm_chat_completion:1.0.0")

    ErrorCode = CustomErrorCode

    Kwargs = CustomKwargs

    Messages = CustomMessages

    class Performative(Message.Performative):
        """Performatives for the llm_chat_completion protocol."""

        CREATE = "create"
        DELETE = "delete"
        ERROR = "error"
        LIST = "list"
        RESPONSE = "response"
        RETRIEVE = "retrieve"
        UPDATE = "update"

        def __str__(self) -> str:
            """Get the string representation."""
            return str(self.value)

    _performatives = {"create", "delete", "error", "list", "response", "retrieve", "update"}
    __slots__: Tuple[str, ...] = tuple()
    class _SlotsCls():
        __slots__ = (
            "completion_id",            "data",            "dialogue_reference",            "error_code",            "error_msg",            "kwargs",            "message_id",            "messages",            "model",            "model_class",            "model_module",            "performative",            "target",        )
    def __init__(
        self,
        performative: Performative,
        dialogue_reference: Tuple[str, str] = ("", ""),
        message_id: int = 1,
        target: int = 0,
        **kwargs: Any,
    ):
        """
        Initialise an instance of LlmChatCompletionMessage.

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
            performative=LlmChatCompletionMessage.Performative(performative),
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
        return cast(LlmChatCompletionMessage.Performative, self.get("performative"))

    @property
    def target(self) -> int:
        """Get the target of the message."""
        enforce(self.is_set("target"), "target is not set.")
        return cast(int, self.get("target"))

    @property
    def completion_id(self) -> str:
        """Get the 'completion_id' content from the message."""
        enforce(self.is_set("completion_id"), "'completion_id' content is not set.")
        return cast(str, self.get("completion_id"))

    @property
    def data(self) -> str:
        """Get the 'data' content from the message."""
        enforce(self.is_set("data"), "'data' content is not set.")
        return cast(str, self.get("data"))

    @property
    def error_code(self) -> CustomErrorCode:
        """Get the 'error_code' content from the message."""
        enforce(self.is_set("error_code"), "'error_code' content is not set.")
        return cast(CustomErrorCode, self.get("error_code"))

    @property
    def error_msg(self) -> str:
        """Get the 'error_msg' content from the message."""
        enforce(self.is_set("error_msg"), "'error_msg' content is not set.")
        return cast(str, self.get("error_msg"))

    @property
    def kwargs(self) -> CustomKwargs:
        """Get the 'kwargs' content from the message."""
        enforce(self.is_set("kwargs"), "'kwargs' content is not set.")
        return cast(CustomKwargs, self.get("kwargs"))

    @property
    def messages(self) -> CustomMessages:
        """Get the 'messages' content from the message."""
        enforce(self.is_set("messages"), "'messages' content is not set.")
        return cast(CustomMessages, self.get("messages"))

    @property
    def model(self) -> str:
        """Get the 'model' content from the message."""
        enforce(self.is_set("model"), "'model' content is not set.")
        return cast(str, self.get("model"))

    @property
    def model_class(self) -> str:
        """Get the 'model_class' content from the message."""
        enforce(self.is_set("model_class"), "'model_class' content is not set.")
        return cast(str, self.get("model_class"))

    @property
    def model_module(self) -> str:
        """Get the 'model_module' content from the message."""
        enforce(self.is_set("model_module"), "'model_module' content is not set.")
        return cast(str, self.get("model_module"))

    def _is_consistent(self) -> bool:
        """Check that the message follows the llm_chat_completion protocol."""
        try:
            enforce(isinstance(self.dialogue_reference, tuple), "Invalid type for 'dialogue_reference'. Expected 'tuple'. Found '{}'.".format(type(self.dialogue_reference)))
            enforce(isinstance(self.dialogue_reference[0], str), "Invalid type for 'dialogue_reference[0]'. Expected 'str'. Found '{}'.".format(type(self.dialogue_reference[0])))
            enforce(isinstance(self.dialogue_reference[1], str), "Invalid type for 'dialogue_reference[1]'. Expected 'str'. Found '{}'.".format(type(self.dialogue_reference[1])))
            enforce(type(self.message_id) is int, "Invalid type for 'message_id'. Expected 'int'. Found '{}'.".format(type(self.message_id)))
            enforce(type(self.target) is int, "Invalid type for 'target'. Expected 'int'. Found '{}'.".format(type(self.target)))

            # Light Protocol Rule 2
            # Check correct performative
            enforce(isinstance(self.performative, LlmChatCompletionMessage.Performative), "Invalid 'performative'. Expected either of '{}'. Found '{}'.".format(self.valid_performatives, self.performative))

            # Check correct contents
            actual_nb_of_contents = len(self._body) - DEFAULT_BODY_SIZE
            expected_nb_of_contents = 0
            if self.performative == LlmChatCompletionMessage.Performative.CREATE:
                expected_nb_of_contents = 3
                enforce(isinstance(self.model, str), "Invalid type for content 'model'. Expected 'str'. Found '{}'.".format(type(self.model)))
                enforce(isinstance(self.messages, CustomMessages), "Invalid type for content 'messages'. Expected 'Messages'. Found '{}'.".format(type(self.messages)))
                enforce(isinstance(self.kwargs, CustomKwargs), "Invalid type for content 'kwargs'. Expected 'Kwargs'. Found '{}'.".format(type(self.kwargs)))
            elif self.performative == LlmChatCompletionMessage.Performative.RETRIEVE:
                expected_nb_of_contents = 2
                enforce(isinstance(self.completion_id, str), "Invalid type for content 'completion_id'. Expected 'str'. Found '{}'.".format(type(self.completion_id)))
                enforce(isinstance(self.kwargs, CustomKwargs), "Invalid type for content 'kwargs'. Expected 'Kwargs'. Found '{}'.".format(type(self.kwargs)))
            elif self.performative == LlmChatCompletionMessage.Performative.UPDATE:
                expected_nb_of_contents = 2
                enforce(isinstance(self.completion_id, str), "Invalid type for content 'completion_id'. Expected 'str'. Found '{}'.".format(type(self.completion_id)))
                enforce(isinstance(self.kwargs, CustomKwargs), "Invalid type for content 'kwargs'. Expected 'Kwargs'. Found '{}'.".format(type(self.kwargs)))
            elif self.performative == LlmChatCompletionMessage.Performative.LIST:
                expected_nb_of_contents = 1
                enforce(isinstance(self.kwargs, CustomKwargs), "Invalid type for content 'kwargs'. Expected 'Kwargs'. Found '{}'.".format(type(self.kwargs)))
            elif self.performative == LlmChatCompletionMessage.Performative.DELETE:
                expected_nb_of_contents = 2
                enforce(isinstance(self.completion_id, str), "Invalid type for content 'completion_id'. Expected 'str'. Found '{}'.".format(type(self.completion_id)))
                enforce(isinstance(self.kwargs, CustomKwargs), "Invalid type for content 'kwargs'. Expected 'Kwargs'. Found '{}'.".format(type(self.kwargs)))
            elif self.performative == LlmChatCompletionMessage.Performative.RESPONSE:
                expected_nb_of_contents = 3
                enforce(isinstance(self.data, str), "Invalid type for content 'data'. Expected 'str'. Found '{}'.".format(type(self.data)))
                enforce(isinstance(self.model_class, str), "Invalid type for content 'model_class'. Expected 'str'. Found '{}'.".format(type(self.model_class)))
                enforce(isinstance(self.model_module, str), "Invalid type for content 'model_module'. Expected 'str'. Found '{}'.".format(type(self.model_module)))
            elif self.performative == LlmChatCompletionMessage.Performative.ERROR:
                expected_nb_of_contents = 2
                enforce(isinstance(self.error_code, CustomErrorCode), "Invalid type for content 'error_code'. Expected 'ErrorCode'. Found '{}'.".format(type(self.error_code)))
                enforce(isinstance(self.error_msg, str), "Invalid type for content 'error_msg'. Expected 'str'. Found '{}'.".format(type(self.error_msg)))

            # Check correct content count
            enforce(expected_nb_of_contents == actual_nb_of_contents, "Incorrect number of contents. Expected {}. Found {}".format(expected_nb_of_contents, actual_nb_of_contents))

            # Light Protocol Rule 3
            if self.message_id == 1:
                enforce(self.target == 0, "Invalid 'target'. Expected 0 (because 'message_id' is 1). Found {}.".format(self.target))
        except (AEAEnforceError, ValueError, KeyError) as e:
            _default_logger.error(str(e))
            return False

        return True
