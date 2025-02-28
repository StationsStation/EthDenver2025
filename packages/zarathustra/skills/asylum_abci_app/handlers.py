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
from packages.eightballer.protocols.chatroom.message import ChatroomMessage as TelegramMessage
from packages.eightballer.protocols.chatroom.dialogues import (
    ChatroomDialogue as TelegramDialogue,
    ChatroomDialogues as TelegramDialogues,
)
from packages.zarathustra.skills.asylum_abci_app.strategy import LLMActions, AsylumStrategy
from packages.zarathustra.skills.asylum_abci_app.dialogues import (
    HttpDialogue,
    HttpDialogues,
    DefaultDialogues,
)
from packages.zarathustra.connections.openai_api.connection import reconstitute
from packages.zarathustra.protocols.llm_chat_completion.message import LlmChatCompletionMessage
from packages.zarathustra.protocols.llm_chat_completion.dialogues import (
    LlmChatCompletionDialogue,
    LlmChatCompletionDialogues,
)


class TelegramHandler(Handler):
    """This implements the Telegram handler."""

    SUPPORTED_PROTOCOL = TelegramMessage.protocol_id

    def handle(self, message: Message) -> None:
        """Implement the reaction to an envelope."""

        telegram_msg = cast(TelegramMessage, message)
        if telegram_msg.performative == TelegramMessage.Performative.ERROR:
            self.context.logger.error(f"Received error message={telegram_msg}")
            return

        if telegram_msg.performative == TelegramMessage.Performative.MESSAGE_SENT:
            self.context.logger.debug(f"received telegram message={telegram_msg}")
            return

        telegram_dialogues = cast(TelegramDialogues, self.context.telegram_dialogues)
        telegram_dialogue = cast(TelegramDialogue, telegram_dialogues.update(telegram_msg))

        if not telegram_dialogue:
            self.context.logger.debug(f"received invalid telegram message={telegram_msg}, unidentified dialogue.")

        self.context.logger.info(f"received telegram message={telegram_msg.from_user}, content={telegram_msg.text}")
        self.strategy.pending_telegram_messages.append(telegram_msg)
        self.strategy.current_telegram_thread.append(telegram_msg)

    @property
    def strategy(self):
        """Get the strategy."""
        return cast(AsylumStrategy, self.context.asylum_strategy)

    def setup(self):
        """Implement the setup."""

    def teardown(self):
        """Implement the handler teardown."""


class LlmChatCompletionHandler(Handler):
    """This implements the LlmChatCompletion handler."""

    SUPPORTED_PROTOCOL = LlmChatCompletionMessage.protocol_id

    def handle(self, message: Message) -> None:
        """Implement the reaction to an envelope."""

        llm_chat_completion_msg = cast(LlmChatCompletionMessage, message)
        if llm_chat_completion_msg.performative == LlmChatCompletionMessage.Performative.ERROR:
            self.context.logger.error(f"Received error={llm_chat_completion_msg}")
            return

        if llm_chat_completion_msg.performative == LlmChatCompletionMessage.Performative.RESPONSE:
            self.context.logger.debug(f"received LLM chat completion message={llm_chat_completion_msg}")

        llm_chat_completion_dialogues = cast(LlmChatCompletionDialogues, self.context.llm_chat_completion_dialogues)
        llm_chat_completion_dialogue = cast(
            LlmChatCompletionDialogue, llm_chat_completion_dialogues.update(llm_chat_completion_msg)
        )

        if not llm_chat_completion_dialogue:
            self.context.logger.debug(
                f"received invalid llm chat completion message={llm_chat_completion_msg}, unidentified dialogue."
            )

        llm_chat_completion = reconstitute(message)
        self.context.logger.debug(f"Reconstituted: {llm_chat_completion}")
        text = llm_chat_completion.choices[0].message.content
        if not self.context.asylum_strategy.user_persona:
            self.context.asylum_strategy.user_persona = text
        self.strategy.llm_responses.append((LLMActions.REPLY, text))

    @property
    def strategy(self):
        """Get the strategy."""
        return cast(AsylumStrategy, self.context.asylum_strategy)

    def setup(self):
        """Implement the setup."""

    def teardown(self):
        """Implement the handler teardown."""


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
