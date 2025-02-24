
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

"""Openai API connection and channel."""

import os
import importlib
from abc import abstractmethod
from enum import StrEnum
from pathlib import Path
import subprocess
import asyncio
from asyncio.events import AbstractEventLoop
import logging
from typing import Any, Dict, Callable, Optional, Set, cast

from pydantic import BaseModel
from dotenv import load_dotenv

from aea.common import Address
from aea.configurations.base import PublicId
from aea.connections.base import Connection, ConnectionStates
from aea.mail.base import Envelope, Message
from aea.protocols.dialogue.base import Dialogue

from packages.zarathustra.protocols.llm_chat_completion.dialogues import LlmChatCompletionDialogue
from packages.zarathustra.protocols.llm_chat_completion.dialogues import LlmChatCompletionDialogues as BaseLlmChatCompletionDialogues
from packages.zarathustra.protocols.llm_chat_completion.message import LlmChatCompletionMessage

import openai


CONNECTION_ID = PublicId.from_str("zarathustra/openai_api:0.1.0")
_default_logger = logging.getLogger("aea.packages.zarathustra.connections.openai_api")

LLM_RESPONSE_TIMEOUT = 10


def get_repo_root() -> Path:
    command = ["git", "rev-parse", "--show-toplevel"]
    repo_root = subprocess.check_output(command, stderr=subprocess.STDOUT).strip()  # noqa: S603
    return Path(repo_root.decode("utf-8"))


class Model(StrEnum):
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


def setup_llm_client() -> openai.AsyncOpenAI:
    """Load environment variables and instantiate the LLM client."""
    load_dotenv(get_repo_root() / ".env")

    if (api_key := os.environ.get("AKASH_API_KEY")) is None:
        raise OSError(
            "Ensure 'AKASH_API_KEY' is set in the repository's root .env file. "
            "Visit https://chatapi.akash.network/ to obtain an API key.",
        )

    return openai.AsyncOpenAI(
        api_key=api_key,
        base_url="https://chatapi.akash.network/api/v1",
    )


def reconstitute(message: LlmChatCompletionMessage) -> BaseModel:
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
            """Infer the role of the agent from an incoming/outgoing first message"""
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
        """
        Initialize the BaseAsyncChannel channel."""

        self.agent_address = agent_address
        self.connection_id = connection_id
        self.message_type = message_type

        self.is_stopped = True
        self._connection = None
        self._tasks: Set[asyncio.Task] = set()
        self._in_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.logger = _default_logger

    @property
    @abstractmethod
    def performative_handlers(self) -> Dict[Message.Performative, Callable[[Message, Dialogue], Message]]:
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
            raise ConnectionError("{self.__class__.__name__} not connected, call connect first!")

        if not isinstance(envelope.message, self.message_type):
            raise TypeError(f"Message not of type {self.message_type}")

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

    async def get_message(self) -> Optional[Envelope]:
        """Check the in-queue for envelopes."""

        if self.is_stopped:
            return None
        try:
            envelope = self._in_queue.get_nowait()
            return envelope
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
            except KeyboardInterrupt:  # noqa
                raise
            except BaseException:  # noqa
                pass  # nosec


class OpenaiApiAsyncChannel(BaseAsyncChannel):  # pylint: disable=too-many-instance-attributes
    """A channel handling incomming communication from the Openai Api connection."""

    def __init__(
        self,
        agent_address: Address,
        connection_id: PublicId,
        **kwargs  # TODO: pass the neccesary arguments for your channel explicitly
    ):
        """
        Initialize the Openai Api channel.

        :param agent_address: the address of the agent.
        :param connection_id: the id of the connection.
        """

        super().__init__(agent_address, connection_id, message_type=LlmChatCompletionMessage)

        # TODO: assign attributes from custom connection configuration explicitly
        for key, value in kwargs.items():
            setattr(self, key, value)

        self._dialogues = LlmChatCompletionDialogues(str(OpenaiApiConnection.connection_id))
        self.logger.debug("Initialised the Openai Api channel")

    async def connect(self, loop: AbstractEventLoop) -> None:
        """Connect channel using loop."""

        if self.is_stopped:
            self._loop = loop
            self._in_queue = asyncio.Queue()
            self.is_stopped = False
            try:
                self._connection = setup_llm_client()
                self.logger.info("Openai Api has connected.")
            except Exception as e:  # noqa
                self.is_stopped = True
                self._in_queue = None
                raise ConnectionError(f"Failed to start Openai Api: {e}")

    async def disconnect(self) -> None:
        """Disconnect channel."""

        if self.is_stopped:
            return

        await self._cancel_tasks()
        ...  # TODO: e.g. self._connection.close()
        self.is_stopped = True
        self.logger.info("Openai Api has shutdown.")

    @property
    def performative_handlers(self) -> Dict[LlmChatCompletionMessage.Performative, Callable[[LlmChatCompletionMessage, LlmChatCompletionDialogue], LlmChatCompletionMessage]]:
        return {
            LlmChatCompletionMessage.Performative.CREATE: self.create,
            LlmChatCompletionMessage.Performative.RETRIEVE: self.retrieve,
            LlmChatCompletionMessage.Performative.UPDATE: self.update,
            LlmChatCompletionMessage.Performative.LIST: self.list,
            LlmChatCompletionMessage.Performative.DELETE: self.delete,
        }

    async def create(self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with CREATE Perfomative """

        model = message.model
        messages = message.messages
        kwargs = message.kwargs

        # TODO: Implement the necessary logic required for the response message
        try:
            chat_completion = await asyncio.wait_for(
                self._connection.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs,
                ),
                timeout=LLM_RESPONSE_TIMEOUT,
            )
        except TimeoutError as e:
            self.logger.exception(f"Model {model} did not respond timely")
            response_message = dialogue.reply(
                performative=LlmChatCompletionMessage.Performative.ERROR,
                error_code=message.ErrorCode.OPENAI_ERROR,
                error_msg=f"Model {model} did not respond timely",
            )
            return response_message
        
        data = chat_completion.to_json()
        model_class = chat_completion.__class__.__name__
        module_name = chat_completion.__module__
    
        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=data,
            model_class=model_class,
            model_module=module_name,
        )

        return response_message

    async def retrieve(self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with RETRIEVE Perfomative """

        completion_id = message.completion_id
        kwargs = message.kwargs

        # TODO: Implement the necessary logic required for the response message
    
        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

        return response_message

    async def update(self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with UPDATE Perfomative """

        completion_id = message.completion_id
        kwargs = message.kwargs

        # TODO: Implement the necessary logic required for the response message
    
        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

        return response_message

    async def list(self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with LIST Perfomative """

        kwargs = message.kwargs

        # TODO: Implement the necessary logic required for the response message
    
        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

        return response_message

    async def delete(self, message: LlmChatCompletionMessage, dialogue: LlmChatCompletionDialogue) -> LlmChatCompletionMessage:
        """Handle LlmChatCompletionMessage with DELETE Perfomative """

        completion_id = message.completion_id
        kwargs = message.kwargs

        # TODO: Implement the necessary logic required for the response message
    
        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.RESPONSE,
            data=...,
            model_class=...,
            model_module=...,
        )

        response_message = dialogue.reply(
            performative=LlmChatCompletionMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
        )

        return response_message


class OpenaiApiConnection(Connection):
    """Proxy to the functionality of a Openai Api connection."""

    connection_id = CONNECTION_ID

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize a Openai Api connection.

        :param kwargs: keyword arguments
        """

        keys = []  # TODO: pop your custom kwargs
        config = kwargs["configuration"].config
        custom_kwargs = {key: config.pop(key) for key in keys}
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
        """
        Send an envelope.

        :param envelope: the envelope to send.
        """

        self._ensure_connected()
        return await self.channel.send(envelope)

    async def receive(self, *args: Any, **kwargs: Any) -> Optional[Envelope]:
        """
        Receive an envelope. Blocking.

        :param args: arguments to receive
        :param kwargs: keyword arguments to receive
        :return: the envelope received, if present.  # noqa: DAR202
        """

        self._ensure_connected()
        try:

            result = await self.channel.get_message()
            return result
        except Exception as e:  # noqa
            self.logger.info(f"Exception on receive {e}")
            return None

