# ------------------------------------------------------------------------------
#
#   Copyright 2022 Valory AG
#   Copyright 2018-2021 Fetch.AI Limited
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

"""This module contains the handler for the 'metrics' skill."""

import json
from typing import cast

from aea.skills.base import Handler
from aea.protocols.base import Message

from packages.eightballer.protocols.default import DefaultMessage
from packages.eightballer.protocols.http.message import HttpMessage
from packages.henrikkv.skills.demo_fsm_abci_app.dialogues import (
    HttpDialogue,
    HttpDialogues,
    DefaultDialogues,
)


class HttpHandler(Handler):
    """This implements the echo handler."""

    SUPPORTED_PROTOCOL = HttpMessage.protocol_id

    def setup(self) -> None:
        """Implement the setup."""

    def handle(self, message: Message) -> None:
        """Implement the reaction to an envelope."""
        http_msg = cast(HttpMessage, message)

        # recover dialogue
        http_dialogues = cast(HttpDialogues, self.context.http_dialogues)
        http_dialogue = cast(HttpDialogue, http_dialogues.update(http_msg))
        if http_dialogue is None:
            self._handle_unidentified_dialogue(http_msg)
            return

        # handle message
        if http_msg.performative == HttpMessage.Performative.REQUEST:
            self._handle_request(http_msg, http_dialogue)
        else:
            self._handle_invalid(http_msg, http_dialogue)

    def _handle_unidentified_dialogue(self, http_msg: HttpMessage) -> None:
        """Handle an unidentified dialogue."""
        self.context.logger.info(f"received invalid http message={http_msg}, unidentified dialogue.")
        default_dialogues = cast(DefaultDialogues, self.context.default_dialogues)
        default_msg, _ = default_dialogues.create(
            counterparty=http_msg.sender,
            performative=DefaultMessage.Performative.ERROR,
            error_code=DefaultMessage.ErrorCode.INVALID_DIALOGUE,
            error_msg="Invalid dialogue.",
            error_data={"http_message": http_msg.encode()},
        )
        self.context.outbox.put_message(message=default_msg)

    def _handle_request(self, http_msg: HttpMessage, http_dialogue: HttpDialogue) -> None:
        """Handle a Http request."""
        self.context.logger.info(
            f"received http request with method={http_msg.method}, url={http_msg.url} and body={http_msg.body}"
        )
        if http_msg.method == "get" and http_msg.url.find("/metrics"):
            self._handle_get(http_msg, http_dialogue)
        else:
            self._handle_invalid(http_msg, http_dialogue)

    def _handle_get(self, http_msg: HttpMessage, http_dialogue: HttpDialogue) -> None:
        """Handle a Http request of verb GET."""
        if self.enable_cors:
            cors_headers = "Access-Control-Allow-Origin: *\n"
            cors_headers += "Access-Control-Allow-Methods: POST\n"
            cors_headers += "Access-Control-Allow-Headers: Content-Type,Accept\n"
            headers = cors_headers + http_msg.headers
        else:
            headers = http_msg.headers

        http_response = http_dialogue.reply(
            performative=HttpMessage.Performative.RESPONSE,
            target_message=http_msg,
            version=http_msg.version,
            status_code=200,
            status_text="Success",
            headers=headers,
            body=json.dumps(self.context.shared_state).encode("utf-8"),
        )
        self.context.logger.info(f"responding with: {http_response}")
        self.context.outbox.put_message(message=http_response)

    def _handle_post(self, http_msg: HttpMessage, http_dialogue: HttpDialogue) -> None:
        """Handle a Http request of verb POST."""
        http_response = http_dialogue.reply(
            performative=HttpMessage.Performative.RESPONSE,
            target_message=http_msg,
            version=http_msg.version,
            status_code=200,
            status_text="Success",
            headers=http_msg.headers,
            body=http_msg.body,
        )
        self.context.logger.info(f"responding with: {http_response}")
        self.context.outbox.put_message(message=http_response)

    def _handle_invalid(self, http_msg: HttpMessage, http_dialogue: HttpDialogue) -> None:
        """Handle an invalid http message."""
        self.context.logger.warning(
            f"""
            Cannot handle http message of
            performative={http_msg.performative}
            dialogue={http_dialogue.dialogue_label}.
            """
        )

    def teardown(self) -> None:
        """Implement the handler teardown."""

    def __init__(self, **kwargs):
        """Initialise the handler."""
        self.enable_cors = kwargs.pop("enable_cors", False)
        super().__init__(**kwargs)
