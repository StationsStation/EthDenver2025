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

"""Test dialogues module for llm_chat_completion protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from aea.test_tools.test_protocol import BaseProtocolDialoguesTestCase

from packages.zarathustra.protocols.llm_chat_completion.message import (
    LlmChatCompletionMessage,
)
from packages.zarathustra.protocols.llm_chat_completion.dialogues import (
    LlmChatCompletionDialogue,
    BaseLlmChatCompletionDialogues,
)
from packages.zarathustra.protocols.llm_chat_completion.tests.data import KWARGS, MESSAGES


class TestDialoguesLlmChatCompletion(BaseProtocolDialoguesTestCase):
    """Test for the 'llm_chat_completion' protocol dialogues."""

    MESSAGE_CLASS = LlmChatCompletionMessage

    DIALOGUE_CLASS = LlmChatCompletionDialogue

    DIALOGUES_CLASS = BaseLlmChatCompletionDialogues

    ROLE_FOR_THE_FIRST_MESSAGE = LlmChatCompletionDialogue.Role.CONNECTION

    def make_message_content(self) -> dict:
        """Make a dict with message contruction content for dialogues.create."""
        return {
            "performative": LlmChatCompletionMessage.Performative.CREATE,
            "model": "some model",
            "messages": MESSAGES,
            "kwargs": KWARGS,
        }
