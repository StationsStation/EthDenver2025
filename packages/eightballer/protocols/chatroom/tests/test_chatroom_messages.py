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

"""Test messages module for chatroom protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
import os

import yaml
from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase

from packages.eightballer.protocols.chatroom.message import ChatroomMessage
from packages.eightballer.protocols.chatroom.custom_types import ErrorCode


def load_data(custom_type):
    """Load test data."""
    with open(f"{os.path.dirname(__file__)}/dummy_data.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)[custom_type]


class TestMessageChatroom(BaseProtocolMessagesTestCase):
    """Test for the 'chatroom' protocol message."""

    MESSAGE_CLASS = ChatroomMessage

    def build_messages(self) -> list[ChatroomMessage]:  # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            ChatroomMessage(
                performative=ChatroomMessage.Performative.MESSAGE,
                chat_id="some str",
                text="some str",
                id=12,
                parse_mode="some str",
                reply_markup="some str",
                from_user="some str",
                timestamp=12,
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.MESSAGE_SENT,
                id=12,
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.ERROR,
                error_code=ErrorCode(0),  # check it please!
                error_msg="some str",
                error_data={"some str": b"some_bytes"},
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.SUBSCRIBE,
                chat_id="some str",
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.UNSUBSCRIBE,
                chat_id="some str",
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.GET_CHANNELS,
                agent_id="some str",
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.UNSUBSCRIPTION_RESULT,
                chat_id="some str",
                status="some str",
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.SUBSCRIPTION_RESULT,
                chat_id="some str",
                status="some str",
            ),
            ChatroomMessage(
                performative=ChatroomMessage.Performative.CHANNELS,
                channels=("some str",),
            ),
        ]

    def build_inconsistent(self):
        """Build inconsistent message."""
        return []
