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

"""Serialization module for telegram protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import Any, Dict, cast

from aea.mail.base_pb2 import DialogueMessage  # type: ignore
from aea.mail.base_pb2 import Message as ProtobufMessage  # type: ignore
from aea.protocols.base import Message  # type: ignore
from aea.protocols.base import Serializer  # type: ignore

from packages.eightballer.protocols.telegram import telegram_pb2  # type: ignore
from packages.eightballer.protocols.telegram.custom_types import (  # type: ignore
    ErrorCode,
)
from packages.eightballer.protocols.telegram.message import (  # type: ignore
    TelegramMessage,
)


class TelegramSerializer(Serializer):
    """Serialization for the 'telegram' protocol."""

    @staticmethod
    def encode(msg: Message) -> bytes:
        """
        Encode a 'Telegram' message into bytes.

        :param msg: the message object.
        :return: the bytes.
        """
        msg = cast(TelegramMessage, msg)
        message_pb = ProtobufMessage()
        dialogue_message_pb = DialogueMessage()
        telegram_msg = telegram_pb2.TelegramMessage()  # type: ignore

        dialogue_message_pb.message_id = msg.message_id
        dialogue_reference = msg.dialogue_reference
        dialogue_message_pb.dialogue_starter_reference = dialogue_reference[0]
        dialogue_message_pb.dialogue_responder_reference = dialogue_reference[1]
        dialogue_message_pb.target = msg.target

        performative_id = msg.performative
        if performative_id == TelegramMessage.Performative.SEND_MESSAGE:
            performative = telegram_pb2.TelegramMessage.Send_Message_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            text = msg.text
            performative.text = text
            if msg.is_set("parse_mode"):
                performative.parse_mode_is_set = True
                parse_mode = msg.parse_mode
                performative.parse_mode = parse_mode
            if msg.is_set("reply_markup"):
                performative.reply_markup_is_set = True
                reply_markup = msg.reply_markup
                performative.reply_markup = reply_markup
            telegram_msg.send_message.CopyFrom(performative)
        elif performative_id == TelegramMessage.Performative.RECEIVE_MESSAGE:
            performative = telegram_pb2.TelegramMessage.Receive_Message_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            id = msg.id
            performative.id = id
            telegram_msg.receive_message.CopyFrom(performative)
        elif performative_id == TelegramMessage.Performative.MESSAGE_SENT:
            performative = telegram_pb2.TelegramMessage.Message_Sent_Performative()  # type: ignore
            id = msg.id
            performative.id = id
            status = msg.status
            performative.status = status
            telegram_msg.message_sent.CopyFrom(performative)
        elif performative_id == TelegramMessage.Performative.NEW_MESSAGE:
            performative = telegram_pb2.TelegramMessage.New_Message_Performative()  # type: ignore
            chat_id = msg.chat_id
            performative.chat_id = chat_id
            id = msg.id
            performative.id = id
            text = msg.text
            performative.text = text
            from_user = msg.from_user
            performative.from_user = from_user
            timestamp = msg.timestamp
            performative.timestamp = timestamp
            telegram_msg.new_message.CopyFrom(performative)
        elif performative_id == TelegramMessage.Performative.ERROR:
            performative = telegram_pb2.TelegramMessage.Error_Performative()  # type: ignore
            error_code = msg.error_code
            ErrorCode.encode(performative.error_code, error_code)
            error_msg = msg.error_msg
            performative.error_msg = error_msg
            error_data = msg.error_data
            performative.error_data.update(error_data)
            telegram_msg.error.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        dialogue_message_pb.content = telegram_msg.SerializeToString()

        message_pb.dialogue_message.CopyFrom(dialogue_message_pb)
        message_bytes = message_pb.SerializeToString()
        return message_bytes

    @staticmethod
    def decode(obj: bytes) -> Message:
        """
        Decode bytes into a 'Telegram' message.

        :param obj: the bytes object.
        :return: the 'Telegram' message.
        """
        message_pb = ProtobufMessage()
        telegram_pb = telegram_pb2.TelegramMessage()  # type: ignore
        message_pb.ParseFromString(obj)
        message_id = message_pb.dialogue_message.message_id
        dialogue_reference = (
            message_pb.dialogue_message.dialogue_starter_reference,
            message_pb.dialogue_message.dialogue_responder_reference,
        )
        target = message_pb.dialogue_message.target

        telegram_pb.ParseFromString(message_pb.dialogue_message.content)
        performative = telegram_pb.WhichOneof("performative")
        performative_id = TelegramMessage.Performative(str(performative))
        performative_content = dict()  # type: Dict[str, Any]
        if performative_id == TelegramMessage.Performative.SEND_MESSAGE:
            chat_id = telegram_pb.send_message.chat_id
            performative_content["chat_id"] = chat_id
            text = telegram_pb.send_message.text
            performative_content["text"] = text
            if telegram_pb.send_message.parse_mode_is_set:
                parse_mode = telegram_pb.send_message.parse_mode
                performative_content["parse_mode"] = parse_mode
            if telegram_pb.send_message.reply_markup_is_set:
                reply_markup = telegram_pb.send_message.reply_markup
                performative_content["reply_markup"] = reply_markup
        elif performative_id == TelegramMessage.Performative.RECEIVE_MESSAGE:
            chat_id = telegram_pb.receive_message.chat_id
            performative_content["chat_id"] = chat_id
            id = telegram_pb.receive_message.id
            performative_content["id"] = id
        elif performative_id == TelegramMessage.Performative.MESSAGE_SENT:
            id = telegram_pb.message_sent.id
            performative_content["id"] = id
            status = telegram_pb.message_sent.status
            performative_content["status"] = status
        elif performative_id == TelegramMessage.Performative.NEW_MESSAGE:
            chat_id = telegram_pb.new_message.chat_id
            performative_content["chat_id"] = chat_id
            id = telegram_pb.new_message.id
            performative_content["id"] = id
            text = telegram_pb.new_message.text
            performative_content["text"] = text
            from_user = telegram_pb.new_message.from_user
            performative_content["from_user"] = from_user
            timestamp = telegram_pb.new_message.timestamp
            performative_content["timestamp"] = timestamp
        elif performative_id == TelegramMessage.Performative.ERROR:
            pb2_error_code = telegram_pb.error.error_code
            error_code = ErrorCode.decode(pb2_error_code)
            performative_content["error_code"] = error_code
            error_msg = telegram_pb.error.error_msg
            performative_content["error_msg"] = error_msg
            error_data = telegram_pb.error.error_data
            error_data_dict = dict(error_data)
            performative_content["error_data"] = error_data_dict
        else:
            raise ValueError("Performative not valid: {}.".format(performative_id))

        return TelegramMessage(
            message_id=message_id,
            dialogue_reference=dialogue_reference,
            target=target,
            performative=performative,
            **performative_content
        )
