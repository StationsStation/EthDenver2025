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


"""This module contains the tests of the Telegram Wrapper connection module."""
# pylint: skip-file

import asyncio
from unittest.mock import MagicMock

import pytest
from aea.common import Address
from aea.mail.base import Message, Envelope
from aea.identity.base import Identity
from aea.configurations.base import ConnectionConfig
from aea.protocols.dialogue.base import Dialogue as BaseDialogue

from packages.eightballer.protocols.telegram.message import TelegramMessage
from packages.eightballer.protocols.telegram.dialogues import TelegramDialogue, BaseTelegramDialogues
from packages.eightballer.connections.telegram_wrapper.connection import (
    CONNECTION_ID as CONNECTION_PUBLIC_ID,
    TelegramWrapperConnection,
)


def envelope_it(message: TelegramMessage):
    """Envelope the message."""

    return Envelope(
        to=message.to,
        sender=message.sender,
        message=message,
    )


class TelegramDialogues(BaseTelegramDialogues):
    """The dialogues class keeps track of all telegram_wrapper dialogues."""

    def __init__(self, self_address: Address, **kwargs) -> None:
        """Initialize dialogues."""
        del kwargs

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> BaseDialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message."""
            del receiver_address, message
            return TelegramDialogue.Role.AGENT

        BaseTelegramDialogues.__init__(
            self,
            self_address=self_address,
            role_from_first_message=role_from_first_message,
        )


class TestTelegramWrapperConnection:
    """Simple test of the telegram_wrapper connection."""

    def setup(self):
        """Initialise the test case."""

        self.identity = Identity("dummy_name", address="dummy_address", public_key="dummy_public_key")
        self.agent_address = self.identity.address

        self.connection_id = TelegramWrapperConnection.connection_id
        self.protocol_id = TelegramMessage.protocol_id
        self.target_skill_id = "dummy_author/dummy_skill:0.1.0"

        kwargs = {}

        self.configuration = ConnectionConfig(
            target_skill_id=self.target_skill_id,
            connection_id=TelegramWrapperConnection.connection_id,
            restricted_to_protocols={TelegramMessage.protocol_id},
            **kwargs,
        )

        self.telegram_wrapper_connection = TelegramWrapperConnection(
            configuration=self.configuration,
            data_dir=MagicMock(),
            identity=self.identity,
        )

        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.telegram_wrapper_connection.connect())
        self.connection_address = str(TelegramWrapperConnection.connection_id)
        self._dialogues = TelegramDialogues(self.target_skill_id)

    @pytest.mark.asyncio
    async def test_telegram_wrapper_connection_connect(self):
        """Test the connect."""
        await self.telegram_wrapper_connection.connect()
        assert not self.telegram_wrapper_connection.channel.is_stopped

    @pytest.mark.asyncio
    async def test_telegram_wrapper_connection_disconnect(self):
        """Test the disconnect."""
        await self.telegram_wrapper_connection.disconnect()
        assert self.telegram_wrapper_connection.channel.is_stopped

    @pytest.mark.asyncio
    async def test_handles_inbound_query(self):
        """Test the connect."""
        await self.telegram_wrapper_connection.connect()

        msg, _dialogue = self._dialogues.create(
            counterparty=str(CONNECTION_PUBLIC_ID),
            performative=TelegramMessage.Performative.SEND_MESSAGE,
            chat_id="123",
            text="Hello World",
        )

        await self.telegram_wrapper_connection.send(envelope_it(msg))
