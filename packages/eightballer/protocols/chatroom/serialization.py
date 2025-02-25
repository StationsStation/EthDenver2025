# -*- coding: utf-8 -*-
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

"""Serialization module for chatroom protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import Any, Dict, cast

from aea.mail.base_pb2 import DialogueMessage  # type: ignore
from aea.mail.base_pb2 import Message as ProtobufMessage  # type: ignore
from aea.protocols.base import Message  # type: ignore
from aea.protocols.base import Serializer  # type: ignore

from packages.eightballer.protocols.chatroom import chatroom_pb2  # type: ignore
from packages.eightballer.protocols.chatroom.custom_types import (  # type: ignore
    ErrorCode,
)
from packages.eightballer.protocols.chatroom.message import (  # type: ignore
    ChatroomMessage,
)


class ChatroomSerializer(Serializer):
    """Serialization for the 'chatroom' protocol."""

    @staticmethod
    def encode(msg: Message) -> bytes:
        """
        Encode a 'Chatroom' message into bytes.

        :param msg: the message object.
        :return: the bytes.
        """
        msg = cast(ChatroomMessage, msg)
        message_pb = ProtobufMessage()
        dialogue_message_pb = DialogueMessage()
        chatroom_msg = chatroom_pb2.ChatroomMessage()  # type: ignore

        dialogue_message_pb.message_id = msg.message_id
        dialogue_reference = msg.dialogue_reference
        dialogue_message_pb.dialogue_starter_reference = dialogue_reference[0]
        dialogue_message_pb.dialogue_responder_reference = dialogue_reference[1]
        dialogue_message_pb.target = msg.target

        performative_id = msg.performative
        if performative_id == ChatroomMessage.Performative.MESSAGE:
            performative = chatroom_pb2.ChatroomMessage.Message_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            text = msg.text
            performative.text = text
            if msg.is_set("id"):
                performative.id_is_set = True
                id = msg.id
                performative.id = id
            if msg.is_set("parse_mode"):
                performative.parse_mode_is_set = True
                parse_mode = msg.parse_mode
                performative.parse_mode = parse_mode
            if msg.is_set("reply_markup"):
                performative.reply_markup_is_set = True
                reply_markup = msg.reply_markup
                performative.reply_markup = reply_markup
            if msg.is_set("from_user"):
                performative.from_user_is_set = True
                from_user = msg.from_user
                performative.from_user = from_user
            if msg.is_set("timestamp"):
                performative.timestamp_is_set = True
                timestamp = msg.timestamp
                performative.timestamp = timestamp
            chatroom_msg.message.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.MESSAGE_SENT:
            performative = chatroom_pb2.ChatroomMessage.Message_Sent_Performative()  # type: ignore
            if msg.is_set("id"):
                performative.id_is_set = True
                id = msg.id
                performative.id = id
            chatroom_msg.message_sent.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.ERROR:
            performative = chatroom_pb2.ChatroomMessage.Error_Performative()  # type: ignore
            error_code = msg.error_code
            ErrorCode.encode(performative.error_code, error_code)
            error_msg = msg.error_msg
            performative.error_msg = error_msg
            error_data = msg.error_data
            performative.error_data.update(error_data)
            chatroom_msg.error.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.SUBSCRIBE:
            performative = chatroom_pb2.ChatroomMessage.Subscribe_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            chatroom_msg.subscribe.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.UNSUBSCRIBE:
            performative = chatroom_pb2.ChatroomMessage.Unsubscribe_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            chatroom_msg.unsubscribe.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.GET_CHANNELS:
            performative = chatroom_pb2.ChatroomMessage.Get_Channels_Performative()  # type: ignore
            agent_id = msg.agent_id
            performative.agent_id = agent_id
            chatroom_msg.get_channels.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.UNSUBSCRIPTION_RESULT:
            performative = chatroom_pb2.ChatroomMessage.Unsubscription_Result_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            status = msg.status
            performative.status = status
            chatroom_msg.unsubscription_result.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.SUBSCRIPTION_RESULT:
            performative = chatroom_pb2.ChatroomMessage.Subscription_Result_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            status = msg.status
            performative.status = status
            chatroom_msg.subscription_result.CopyFrom(performative)
        elif performative_id == ChatroomMessage.Performative.CHANNELS:
            performative = chatroom_pb2.ChatroomMessage.Channels_Performative()  # type: ignore
            channels = msg.channels
            performative.channels.extend(channels)
            chatroom_msg.channels.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        dialogue_message_pb.content = chatroom_msg.SerializeToString()

        message_pb.dialogue_message.CopyFrom(dialogue_message_pb)
        message_bytes = message_pb.SerializeToString()
        return message_bytes

    @staticmethod
    def decode(obj: bytes) -> Message:
        """
        Decode bytes into a 'Chatroom' message.

        :param obj: the bytes object.
        :return: the 'Chatroom' message.
        """
        message_pb = ProtobufMessage()
        chatroom_pb = chatroom_pb2.ChatroomMessage()  # type: ignore
        message_pb.ParseFromString(obj)
        message_id = message_pb.dialogue_message.message_id
        dialogue_reference = (
            message_pb.dialogue_message.dialogue_starter_reference,
            message_pb.dialogue_message.dialogue_responder_reference,
        )
        target = message_pb.dialogue_message.target

        chatroom_pb.ParseFromString(message_pb.dialogue_message.content)
        performative = chatroom_pb.WhichOneof("performative")
        performative_id = ChatroomMessage.Performative(str(performative))
        performative_content = dict()  # type: Dict[str, Any]
        if performative_id == ChatroomMessage.Performative.MESSAGE:
            chat_id = chatroom_pb.message.chat_id
            performative_content["chat_id"] = chat_id
            text = chatroom_pb.message.text
            performative_content["text"] = text
            if chatroom_pb.message.id_is_set:
                id = chatroom_pb.message.id
                performative_content["id"] = id
            if chatroom_pb.message.parse_mode_is_set:
                parse_mode = chatroom_pb.message.parse_mode
                performative_content["parse_mode"] = parse_mode
            if chatroom_pb.message.reply_markup_is_set:
                reply_markup = chatroom_pb.message.reply_markup
                performative_content["reply_markup"] = reply_markup
            if chatroom_pb.message.from_user_is_set:
                from_user = chatroom_pb.message.from_user
                performative_content["from_user"] = from_user
            if chatroom_pb.message.timestamp_is_set:
                timestamp = chatroom_pb.message.timestamp
                performative_content["timestamp"] = timestamp
        elif performative_id == ChatroomMessage.Performative.MESSAGE_SENT:
            if chatroom_pb.message_sent.id_is_set:
                id = chatroom_pb.message_sent.id
                performative_content["id"] = id
        elif performative_id == ChatroomMessage.Performative.ERROR:
            pb2_error_code = chatroom_pb.error.error_code
            error_code = ErrorCode.decode(pb2_error_code)
            performative_content["error_code"] = error_code
            error_msg = chatroom_pb.error.error_msg
            performative_content["error_msg"] = error_msg
            error_data = chatroom_pb.error.error_data
            error_data_dict = dict(error_data)
            performative_content["error_data"] = error_data_dict
        elif performative_id == ChatroomMessage.Performative.SUBSCRIBE:
            chat_id = chatroom_pb.subscribe.chat_id
            performative_content["chat_id"] = chat_id
        elif performative_id == ChatroomMessage.Performative.UNSUBSCRIBE:
            chat_id = chatroom_pb.unsubscribe.chat_id
            performative_content["chat_id"] = chat_id
        elif performative_id == ChatroomMessage.Performative.GET_CHANNELS:
            agent_id = chatroom_pb.get_channels.agent_id
            performative_content["agent_id"] = agent_id
        elif performative_id == ChatroomMessage.Performative.UNSUBSCRIPTION_RESULT:
            chat_id = chatroom_pb.unsubscription_result.chat_id
            performative_content["chat_id"] = chat_id
            status = chatroom_pb.unsubscription_result.status
            performative_content["status"] = status
        elif performative_id == ChatroomMessage.Performative.SUBSCRIPTION_RESULT:
            chat_id = chatroom_pb.subscription_result.chat_id
            performative_content["chat_id"] = chat_id
            status = chatroom_pb.subscription_result.status
            performative_content["status"] = status
        elif performative_id == ChatroomMessage.Performative.CHANNELS:
            channels = chatroom_pb.channels.channels
            channels_tuple = tuple(channels)
            performative_content["channels"] = channels_tuple
        else:
            raise ValueError("Performative not valid: {}.".format(performative_id))

        return ChatroomMessage(
            message_id=message_id,
            dialogue_reference=dialogue_reference,
            target=target,
            performative=performative,
            **performative_content
        )
