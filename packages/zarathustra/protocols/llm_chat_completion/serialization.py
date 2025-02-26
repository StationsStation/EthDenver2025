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

"""Serialization module for llm_chat_completion protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import Any, Dict, cast

from aea.mail.base_pb2 import DialogueMessage  # type: ignore
from aea.mail.base_pb2 import Message as ProtobufMessage  # type: ignore
from aea.protocols.base import Message  # type: ignore
from aea.protocols.base import Serializer  # type: ignore

from packages.zarathustra.protocols.llm_chat_completion import (  # type: ignore
    llm_chat_completion_pb2,
)
from packages.zarathustra.protocols.llm_chat_completion.custom_types import (  # type: ignore
    ErrorCode,
    Kwargs,
    Messages,
)
from packages.zarathustra.protocols.llm_chat_completion.message import (  # type: ignore
    LlmChatCompletionMessage,
)


class LlmChatCompletionSerializer(Serializer):
    """Serialization for the 'llm_chat_completion' protocol."""

    @staticmethod
    def encode(msg: Message) -> bytes:
        """
        Encode a 'LlmChatCompletion' message into bytes.

        :param msg: the message object.
        :return: the bytes.
        """
        msg = cast(LlmChatCompletionMessage, msg)
        message_pb = ProtobufMessage()
        dialogue_message_pb = DialogueMessage()
        llm_chat_completion_msg = llm_chat_completion_pb2.LlmChatCompletionMessage()  # type: ignore

        dialogue_message_pb.message_id = msg.message_id
        dialogue_reference = msg.dialogue_reference
        dialogue_message_pb.dialogue_starter_reference = dialogue_reference[0]
        dialogue_message_pb.dialogue_responder_reference = dialogue_reference[1]
        dialogue_message_pb.target = msg.target

        performative_id = msg.performative
        if performative_id == LlmChatCompletionMessage.Performative.CREATE:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.Create_Performative()  # type: ignore
            model = msg.model
            performative.model = model
            messages = msg.messages
            Messages.encode(performative.messages, messages)
            kwargs = msg.kwargs
            Kwargs.encode(performative.kwargs, kwargs)
            llm_chat_completion_msg.create.CopyFrom(performative)
        elif performative_id == LlmChatCompletionMessage.Performative.RETRIEVE:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.Retrieve_Performative()  # type: ignore
            completion_id = msg.completion_id
            performative.completion_id = completion_id
            kwargs = msg.kwargs
            Kwargs.encode(performative.kwargs, kwargs)
            llm_chat_completion_msg.retrieve.CopyFrom(performative)
        elif performative_id == LlmChatCompletionMessage.Performative.UPDATE:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.Update_Performative()  # type: ignore
            completion_id = msg.completion_id
            performative.completion_id = completion_id
            kwargs = msg.kwargs
            Kwargs.encode(performative.kwargs, kwargs)
            llm_chat_completion_msg.update.CopyFrom(performative)
        elif performative_id == LlmChatCompletionMessage.Performative.LIST:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.List_Performative()  # type: ignore
            kwargs = msg.kwargs
            Kwargs.encode(performative.kwargs, kwargs)
            llm_chat_completion_msg.list.CopyFrom(performative)
        elif performative_id == LlmChatCompletionMessage.Performative.DELETE:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.Delete_Performative()  # type: ignore
            completion_id = msg.completion_id
            performative.completion_id = completion_id
            kwargs = msg.kwargs
            Kwargs.encode(performative.kwargs, kwargs)
            llm_chat_completion_msg.delete.CopyFrom(performative)
        elif performative_id == LlmChatCompletionMessage.Performative.RESPONSE:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.Response_Performative()  # type: ignore
            data = msg.data
            performative.data = data
            model_class = msg.model_class
            performative.model_class = model_class
            model_module = msg.model_module
            performative.model_module = model_module
            llm_chat_completion_msg.response.CopyFrom(performative)
        elif performative_id == LlmChatCompletionMessage.Performative.ERROR:
            performative = llm_chat_completion_pb2.LlmChatCompletionMessage.Error_Performative()  # type: ignore
            error_code = msg.error_code
            ErrorCode.encode(performative.error_code, error_code)
            error_msg = msg.error_msg
            performative.error_msg = error_msg
            llm_chat_completion_msg.error.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        dialogue_message_pb.content = llm_chat_completion_msg.SerializeToString()

        message_pb.dialogue_message.CopyFrom(dialogue_message_pb)
        message_bytes = message_pb.SerializeToString()
        return message_bytes
    @staticmethod
    def decode(obj: bytes) -> Message:
        """
        Decode bytes into a 'LlmChatCompletion' message.

        :param obj: the bytes object.
        :return: the 'LlmChatCompletion' message.
        """
        message_pb = ProtobufMessage()
        llm_chat_completion_pb = llm_chat_completion_pb2.LlmChatCompletionMessage()  # type: ignore
        message_pb.ParseFromString(obj)
        message_id = message_pb.dialogue_message.message_id
        dialogue_reference = (message_pb.dialogue_message.dialogue_starter_reference, message_pb.dialogue_message.dialogue_responder_reference)
        target = message_pb.dialogue_message.target

        llm_chat_completion_pb.ParseFromString(message_pb.dialogue_message.content)
        performative = llm_chat_completion_pb.WhichOneof("performative")
        performative_id = LlmChatCompletionMessage.Performative(str(performative))
        performative_content = dict()  # type: Dict[str, Any]
        if performative_id == LlmChatCompletionMessage.Performative.CREATE:
            model = llm_chat_completion_pb.create.model
            performative_content["model"] = model
            pb2_messages = llm_chat_completion_pb.create.messages
            messages = Messages.decode(pb2_messages)
            performative_content["messages"] = messages
            pb2_kwargs = llm_chat_completion_pb.create.kwargs
            kwargs = Kwargs.decode(pb2_kwargs)
            performative_content["kwargs"] = kwargs
        elif performative_id == LlmChatCompletionMessage.Performative.RETRIEVE:
            completion_id = llm_chat_completion_pb.retrieve.completion_id
            performative_content["completion_id"] = completion_id
            pb2_kwargs = llm_chat_completion_pb.retrieve.kwargs
            kwargs = Kwargs.decode(pb2_kwargs)
            performative_content["kwargs"] = kwargs
        elif performative_id == LlmChatCompletionMessage.Performative.UPDATE:
            completion_id = llm_chat_completion_pb.update.completion_id
            performative_content["completion_id"] = completion_id
            pb2_kwargs = llm_chat_completion_pb.update.kwargs
            kwargs = Kwargs.decode(pb2_kwargs)
            performative_content["kwargs"] = kwargs
        elif performative_id == LlmChatCompletionMessage.Performative.LIST:
            pb2_kwargs = llm_chat_completion_pb.list.kwargs
            kwargs = Kwargs.decode(pb2_kwargs)
            performative_content["kwargs"] = kwargs
        elif performative_id == LlmChatCompletionMessage.Performative.DELETE:
            completion_id = llm_chat_completion_pb.delete.completion_id
            performative_content["completion_id"] = completion_id
            pb2_kwargs = llm_chat_completion_pb.delete.kwargs
            kwargs = Kwargs.decode(pb2_kwargs)
            performative_content["kwargs"] = kwargs
        elif performative_id == LlmChatCompletionMessage.Performative.RESPONSE:
            data = llm_chat_completion_pb.response.data
            performative_content["data"] = data
            model_class = llm_chat_completion_pb.response.model_class
            performative_content["model_class"] = model_class
            model_module = llm_chat_completion_pb.response.model_module
            performative_content["model_module"] = model_module
        elif performative_id == LlmChatCompletionMessage.Performative.ERROR:
            pb2_error_code = llm_chat_completion_pb.error.error_code
            error_code = ErrorCode.decode(pb2_error_code)
            performative_content["error_code"] = error_code
            error_msg = llm_chat_completion_pb.error.error_msg
            performative_content["error_msg"] = error_msg
        else:
            raise ValueError("Performative not valid: {}.".format(performative_id))

        return LlmChatCompletionMessage(
            message_id=message_id,
            dialogue_reference=dialogue_reference,
            target=target,
            performative=performative,
            **performative_content
        )
