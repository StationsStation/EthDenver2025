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


"""This module contains the tests of the Openai Api connection module."""
# pylint: skip-file

import re
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aea.common import Address
from aea.mail.base import Message, Envelope
from aea.identity.base import Identity
from aea.configurations.base import ComponentType, ConnectionConfig
from aea.configurations.loader import load_component_configuration
from aea.protocols.dialogue.base import Dialogue as BaseDialogue

from packages.zarathustra.connections.openai_api.connection import (
    CONNECTION_ID as CONNECTION_PUBLIC_ID,
    Model,
    OpenaiApiConnection,
    reconstitute,
)
from packages.zarathustra.protocols.llm_chat_completion.message import LlmChatCompletionMessage
from packages.zarathustra.protocols.llm_chat_completion.dialogues import (
    LlmChatCompletionDialogue,
    BaseLlmChatCompletionDialogues,
)
from packages.zarathustra.protocols.llm_chat_completion.tests.data import MESSAGES
from packages.zarathustra.protocols.llm_chat_completion.custom_types import Kwargs


def envelope_it(message: LlmChatCompletionMessage):
    """Envelope the message."""

    return Envelope(
        to=message.to,
        sender=message.sender,
        message=message,
    )


class LlmChatCompletionDialogues(BaseLlmChatCompletionDialogues):
    """The dialogues class keeps track of all openai_api dialogues."""

    def __init__(self, self_address: Address, **kwargs) -> None:  # noqa: ARG002
        """Initialize dialogues."""

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message,  # noqa: ARG001
            receiver_address: Address,  # noqa: ARG001
        ) -> BaseDialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message."""
            return LlmChatCompletionDialogue.Role.CONNECTION

        BaseLlmChatCompletionDialogues.__init__(
            self,
            self_address=self_address,
            role_from_first_message=role_from_first_message,
        )


class TestOpenaiApiConnection:
    """TestOpenaiApiConnection."""

    def setup(self):
        """Initialise the test case."""

        self.identity = Identity("dummy_name", address="dummy_address", public_key="dummy_public_key")
        self.agent_address = self.identity.address

        self.connection_id = OpenaiApiConnection.connection_id
        self.protocol_id = LlmChatCompletionMessage.protocol_id
        self.target_skill_id = "dummy_author/dummy_skill:0.1.0"
        directory = Path(__file__).parent.parent
        config = load_component_configuration(ComponentType.CONNECTION, directory)
        pattern = r"\$\{[^:]+:([^}]+)\}"
        extracted_values = {key: re.search(pattern, value).group(1) for key, value in config.config.items()}

        self.configuration = ConnectionConfig(
            target_skill_id=self.target_skill_id,
            connection_id=OpenaiApiConnection.connection_id,
            restricted_to_protocols={LlmChatCompletionMessage.protocol_id},
            **extracted_values,
        )

        self.openai_api_connection = OpenaiApiConnection(
            configuration=self.configuration,
            data_dir=MagicMock(),
            identity=self.identity,
        )

        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.openai_api_connection.connect())
        self.connection_address = str(OpenaiApiConnection.connection_id)
        self._dialogues = LlmChatCompletionDialogues(self.target_skill_id)

    @pytest.mark.asyncio
    async def test_openai_api_connection_connect(self):
        """Test the connect."""
        await self.openai_api_connection.connect()
        assert not self.openai_api_connection.channel.is_stopped

    @pytest.mark.asyncio
    async def test_openai_api_connection_disconnect(self):
        """Test the disconnect."""
        await self.openai_api_connection.disconnect()
        assert self.openai_api_connection.channel.is_stopped

    @pytest.mark.asyncio
    async def test_handles_inbound_performative(self):
        """Test the handleling of an inbound create performative."""
        await self.openai_api_connection.connect()

        model = Model.META_LLAMA_3_1_405B_INSTRUCT_FP8
        messages = MESSAGES
        number_of_responses = 2

        msg, _dialogue = self._dialogues.create(
            counterparty=str(CONNECTION_PUBLIC_ID),
            performative=LlmChatCompletionMessage.Performative.CREATE,
            model=model,
            messages=messages,
            kwargs=Kwargs({"n": number_of_responses}),
        )

        await self.openai_api_connection.send(envelope_it(msg))
        response_envelope = await self.openai_api_connection.receive()
        if response_envelope.message.performative == LlmChatCompletionMessage.Performative.ERROR:
            self.openai_api_connection.logger.exception(f"{response_envelope.message}")
            assert response_envelope.message.error_code == LlmChatCompletionMessage.ErrorCode.OPENAI_ERROR
            return
        model_chat_completion = reconstitute(response_envelope.message)
        assert len(model_chat_completion.choices) == number_of_responses
        for response in model_chat_completion.choices:
            assert response.message.content
