#                                                                             --
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
#                                                                             --

"""Test messages module for telegram protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
import os

import yaml
from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase

from packages.eightballer.protocols.telegram.message import TelegramMessage
from packages.eightballer.protocols.telegram.custom_types import (
    ErrorCode,
    MessageStatus,
)


def load_data(custom_type):
    """Load test data."""
    with open(f"{os.path.dirname(__file__)}/dummy_data.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)[custom_type]


class TestMessageTelegram(BaseProtocolMessagesTestCase):
    """Test for the 'telegram' protocol message."""

    MESSAGE_CLASS = TelegramMessage

    def build_messages(self) -> list[TelegramMessage]:  # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            TelegramMessage(
                performative=TelegramMessage.Performative.MESSAGE,
                chat_id="some str",
                text="some str",
                id=12,
                parse_mode="some str",
                reply_markup="some str",
                from_user="some str",
                timestamp=12,
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.MESSAGE_SENT,
                id=12,
                msg_status=MessageStatus(0),  # check it please!
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.ERROR,
                error_code=ErrorCode(0),  # check it please!
                error_msg="some str",
                error_data={"some str": b"some_bytes"},
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.SUBSCRIBE,
                chat_id="some str",
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.UNSUBSCRIBE,
                chat_id="some str",
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.GET_CHANNELS,
                agent_id="some str",
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.UNSUBSCRIPTION_RESULT,
                chat_id="some str",
                status="some str",
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.SUBSCRIPTION_RESULT,
                chat_id="some str",
                status="some str",
            ),
            TelegramMessage(
                performative=TelegramMessage.Performative.CHANNELS,
                channels=("some str",),
            ),
        ]

    def build_inconsistent(self):
        """Build inconsistent message."""
        return []
