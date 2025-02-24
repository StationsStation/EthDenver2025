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

"""Test messages module for llm_chat_completion protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import List

from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase

from packages.zarathustra.protocols.llm_chat_completion.custom_types import (
    ErrorCode,
    Kwargs,
    Messages,
)
from packages.zarathustra.protocols.llm_chat_completion.message import (
    LlmChatCompletionMessage,
)
from packages.zarathustra.protocols.llm_chat_completion.tests.data import KWARGS, MESSAGES


class TestMessageLlmChatCompletion(BaseProtocolMessagesTestCase):
    """Test for the 'llm_chat_completion' protocol message."""

    MESSAGE_CLASS = LlmChatCompletionMessage

    def build_messages(self) -> List[LlmChatCompletionMessage]: # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.CREATE,
                model = "some model",
                messages = MESSAGES,
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.RETRIEVE,
                completion_id = "some str",
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.UPDATE,
                completion_id = "some str",
                kwargs = KWARGS,
        ),
        
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.LIST,
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.DELETE,
                completion_id = "some str",
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.RESPONSE,
                data = "some str",
                model_class = "some str",
                model_module = "some str",
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.ERROR,
                error_code = ErrorCode(0),
                error_msg = "some str",
        ),
        ]
    def build_inconsistent(self) -> List[LlmChatCompletionMessage]: # type: ignore[override]
        """Build inconsistent messages to be used for testing."""
        return [
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.CREATE,
                # skip content: model
                messages = MESSAGES,
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.RETRIEVE,
                # skip content: completion_id
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.UPDATE,
                # skip content: completion_id
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.LIST,
                # skip content: kwargs
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.DELETE,
                # skip content: completion_id
                kwargs = KWARGS,
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.RESPONSE,
                # skip content: data
                model_class = "some str",
                model_module = "some str",
        ),
            LlmChatCompletionMessage(
                performative=LlmChatCompletionMessage.Performative.ERROR,
                # skip content: error_code
                error_msg = "some str",
        ),
        ]
