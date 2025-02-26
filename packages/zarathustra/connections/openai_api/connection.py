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

"""Openai API connection and channel."""

# ruff: noqa: TD002, TD003, FIX002, ARG002

import asyncio
import logging
import importlib
import subprocess
from abc import abstractmethod
from enum import StrEnum
from typing import Any, cast
from pathlib import Path
from asyncio.events import AbstractEventLoop
from collections.abc import Callable

import openai
from pydantic import BaseModel
from aea.common import Address
from aea.mail.base import Message, Envelope
from aea.connections.base import Connection, ConnectionStates
from aea.configurations.base import PublicId
from aea.protocols.dialogue.base import Dialogue

from packages.zarathustra.protocols.llm_chat_completion.message import LlmChatCompletionMessage
from packages.zarathustra.protocols.llm_chat_completion.dialogues import (
    LlmChatCompletionDialogue,
    BaseLlmChatCompletionDialogues,
)


CONNECTION_ID = PublicId.from_str("zarathustra/openai_api:0.1.0")
_default_logger = logging.getLogger("aea.packages.zarathustra.connections.openai_api")

LLM_RESPONSE_TIMEOUT = 10


def get_repo_root() -> Path:
    """Get repo root."""
    command = ["git", "rev-parse", "--show-toplevel"]
    repo_root = subprocess.check_output(command, stderr=subprocess.STDOUT).strip()
    return Path(repo_root.decode("utf-8"))


class Model(StrEnum):
    """Model. See https://chatapi.akash.network/."""

    DEEPSEEK_R1 = "DeepSeek-R1"
    DEEPSEEK_R1_DISTILL_LLAMA_70B = "DeepSeek-R1-Distill-Llama-70B"
    DEEPSEEK_R1_DISTILL_LLAMA_8B = "DeepSeek-R1-Distill-Llama-8B"
    DEEPSEEK_R1_DISTILL_QWEN_1_5B = "DeepSeek-R1-Distill-Qwen-1.5B"
    DEEPSEEK_R1_DISTILL_QWEN_14B = "DeepSeek-R1-Distill-Qwen-14B"
    DEEPSEEK_R1_DISTILL_QWEN_32B = "DeepSeek-R1-Distill-Qwen-32B"
    DEEPSEEK_R1_DISTILL_QWEN_7B = "DeepSeek-R1-Distill-Qwen-7B"
    META_LLAMA_3_1_8B_INSTRUCT_FP8 = "Meta-Llama-3-1-8B-Instruct-FP8"
    META_LLAMA_3_1_405B_INSTRUCT_FP8 = "Meta-Llama-3-1-405B-Instruct-FP8"
    META_LLAMA_3_2_3B_INSTRUCT = "Meta-Llama-3-2-3B-Instruct"
    NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_HF = "nvidia-Llama-3-1-Nemotron-70B-Instruct-HF"
    META_LLAMA_3_3_70B_INSTRUCT = "Meta-Llama-3-3-70B-Instruct"


def reconstitute(message: LlmChatCompletionMessage) -> BaseModel:
    """Reconstitute pydantic model."""
    module = importlib.import_module(message.model_module)
    cls = getattr(module, message.model_class)
    return cls.model_validate_json(message.data)


class LlmChatCompletionDialogues(BaseLlmChatCompletionDialogues):
    """The dialogues class keeps track of all openai_api dialogues."""

    def __init__(self, self_address: Address, **kwargs) -> None:
        """Initialize dialogues."""

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> Dialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message."""
            assert message, receiver_address
            return LlmChatCompletionDialogue.Role.SKILL

        BaseLlmChatCompletionDialogues.__init__(
            self,
            self_address=self_address,
            role_from_first_message=role_from_first_message,
        )


class BaseAsyncChannel:
    """BaseAsyncChannel."""

    def __init__(
        self,
        agent_address: Address,
        connection_id: PublicId,
        message_type: Message,
    ):
        """Initialize the BaseAsyncChannel channel."""

        self.agent_address = agent_address
        self.connection_id = connection_id
        self.message_type = message_type

        self.is_stopped = True
        self._connection = None
        self._tasks: set[asyncio.Task] = set()
        self._in_queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.logger = _default_logger

    @property
    @abstractmethod
    def performative_handlers(self) -> dict[Message.Performative, Callable[[Message, Dialogue], Message]]:
        """Performative to message handler mapping."""

    @abstractmethod
    async def connect(self, loop: AbstractEventLoop) -> None:
        """Connect channel using loop."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect channel."""

    async def send(self, envelope: Envelope) -> None:
        """Send an envelope with a protocol message."""

        if not (self._loop and self._connection):
            msg = "{self.__class__.__name__} not connected, call connect first!"
            raise ConnectionError(msg)

        if not isinstance(envelope.message, self.message_type):
            msg = f"Message not of type {self.message_type}"
            raise TypeError(msg)

        message = envelope.message

        if message.performative not in self.performative_handlers:
            log_msg = "Message with unexpected performative `{message.performative}` received."
            self.logger.error(log_msg)
            return

        handler = self.performative_handlers[message.performative]

        dialogue = cast(Dialogue, self._dialogues.update(message))
        if dialogue is None:
            self.logger.warning(f"Could not create dialogue for message={message}")
            return

        response_message = await handler(message, dialogue)
        self.logger.info(f"returning message: {response_message}")

        response_envelope = Envelope(
            to=str(envelope.sender),
            sender=str(self.connection_id),
            message=response_message,
            protocol_specification_id=self.message_type.protocol_specification_id,
        )

        await self._in_queue.put(response_envelope)

    async def get_message(self) -> Envelope | None:
        """Check the in-queue for envelopes."""

        if self.is_stopped:
            return None
        try:
            return self._in_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def _cancel_tasks(self) -> None:
        """Cancel all requests tasks pending."""

        for task in list(self._tasks):
            if task.done():  # pragma: nocover
                continue
            task.cancel()

        for task in list(self._tasks):
            try:
                await task
            except KeyboardInterrupt:
                raise
            except BaseException:  # noqa
                pass  # nosec


class OpenaiApiAsyncChannel(BaseAsyncChannel):  # pylint: disable=too-many-instance-attributes
    """A channel handling incomming communication from the Openai Api connection."""

    def __init__(
        self,
        agent_address: Address,
        connection_id: PublicId,
        api_key: str,
        base_url: str,
    ):
        """Initialize the Openai Api channel."""

        super().__init__(agent_address, connection_id, message_type=LlmChatCompletionMessage)

        # TODO: assign attributes from custom connection configuration explicitly
        self.api_key = api_key
        self.base_url = base_url

        self._dialogues = LlmChatCompletionDialogues(str(OpenaiApiConnection.connection_id))
        self.logger.debug("Initialised the Openai Api channel")

    async def connect(self, loop: AbstractEventLoop) -> None:
        """Connect channel using loop."""

        if self.is_stopped:
            self._loop = loop
            self._in_queue = asyncio.Queue()
            self.is_stopped = False
            try:
                self._connection = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                self.logger.info("Openai Api has connected.")
            except Exception as e:
                self.is_stopped = True
                self._in_queue = None
                msg = f"Failed to start Openai Api: {e}"
                raise ConnectionError(msg) from e

    async def disconnect(self) -> None:
        """Disconnect channel."""

        if self.is_stopped:
            return

        await self._cancel_tasks()
        self.is_stopped = True
        self.logger.info("Openai Api has shutdown.")

    @property
    def performative_handlers(
        self,
    ) -> dict[
        LlmChatCompletionMessage.Performative,
        Callable[[LlmChatCompletionMessage, LlmChatCompletionDialogue], LlmChatCompletionMessage],
    ]:
        """Return a mapping for performative to handler."""
        return {
            LlmChatCompletionMessage.Performative.CREATE: self.create,
            LlmChatCompletionMessage.Performative.RETRIEVE: self.retrieve,
            LlmChatCompletionMessage.Performative.UPDATE: self.update,
            LlmChatCompletionMessage.Performative.LIST: self.list,
            LlmChatCompletionMessage.Performative.DELETE: self.delete,
        }

    async def create(
        self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue
    ) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with CREATE Perfomative."""

        model = message.model
        messages = message.messages
        kwargs = message.kwargs

        try:
            chat_completion = await asyncio.wait_for(
                self._connection.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs,
                ),
                timeout=LLM_RESPONSE_TIMEOUT,
            )
        except (TimeoutError, asyncio.exceptions.CancelledError) as e:
            self.logger.exception(f"Model {model} did not respond timely: {e}")
            return dialogue.reply(
                performative=LlmChatCompletionMessage.Performative.ERROR,
                error_code=message.ErrorCode.OPENAI_ERROR,
                error_msg=f"Model {model} did not respond timely: {e}",
            )
        except Exception as e:
            self.logger.exception(f"Caught another exception: {e}")
            return dialogue.reply(
                performative=LlmChatCompletionMessage.Performative.ERROR,
                error_code=message.ErrorCode.OTHER_EXCEPTION,
                error_msg=f"{e}",
            )

        data = chat_completion.to_json()
        model_class = chat_completion.__class__.__name__
        module_name = chat_completion.__module__

        return dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=data,
            model_class=model_class,
            model_module=module_name,
        )

    async def retrieve(
        self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue
    ) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with RETRIEVE Perfomative."""

        # TODO: Implement the necessary logic required for the response message

        dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        return dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

    async def update(
        self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue
    ) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with UPDATE Perfomative."""

        # TODO: Implement the necessary logic required for the response message

        dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        return dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

    async def list(
        self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue
    ) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with LIST Perfomative."""

        # TODO: Implement the necessary logic required for the response message

        dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        return dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

    async def delete(
        self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue
    ) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with DELETE Perfomative."""

        # TODO: Implement the necessary logic required for the response message

        dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        return dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )


class OpenaiApiConnection(Connection):
    """Proxy to the functionality of a Openai Api connection."""

    connection_id = CONNECTION_ID

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a Openai Api connection."""

        keys = ["api_key", "base_url"]
        config = kwargs["configuration"].config
        try:
            custom_kwargs = {key: config.pop(key) for key in keys}
        except KeyError as e:
            msg = f"Provide connection overrides for: {keys}"
            raise ConnectionError(msg) from e
        super().__init__(**kwargs)

        self.channel = OpenaiApiAsyncChannel(
            self.address,
            connection_id=self.connection_id,
            **custom_kwargs,
        )

    async def connect(self) -> None:
        """Connect to a Openai Api."""

        if self.is_connected:  # pragma: nocover
            return

        with self._connect_context():
            self.channel.logger = self.logger
            await self.channel.connect(self.loop)

    async def disconnect(self) -> None:
        """Disconnect from a Openai Api."""

        if self.is_disconnected:
            return  # pragma: nocover
        self.state = ConnectionStates.disconnecting
        await self.channel.disconnect()
        self.state = ConnectionStates.disconnected

    async def send(self, envelope: Envelope) -> None:
        """Send an envelope."""

        self._ensure_connected()
        return await self.channel.send(envelope)

    async def receive(self, *args: Any, **kwargs: Any) -> Envelope | None:
        """Receive an envelope. Blocking."""

        self._ensure_connected()
        try:
            return await self.channel.get_message()
        except Exception as e:  # noqa
            self.logger.info(f"Exception on receive {e}")
            return None
