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


"""This module contains class representations corresponding to every custom type in the protocol specification."""

from enum import Enum, StrEnum
from collections.abc import Sequence

from pydantic import Field, BaseModel


Primitive = bool | int | float | str | bytes
PrimitiveMapping = dict[str, Primitive]
SequenceMapping = dict[str, Sequence[Primitive]]
HybridMapping = dict[str, Primitive | Sequence[Primitive] | PrimitiveMapping | SequenceMapping]


def _value_decode(entry_proto) -> Primitive:
    """Decode value."""

    if entry_proto.HasField("bool_value"):
        return entry_proto.bool_value
    if entry_proto.HasField("int_value"):
        return entry_proto.int_value
    if entry_proto.HasField("float_value"):
        return float(entry_proto.float_value)
    if entry_proto.HasField("str_value"):
        return entry_proto.str_value
    if entry_proto.HasField("bytes_value"):
        return entry_proto.bytes_value
    msg = f"Invalid value entry: {entry_proto}"
    raise ValueError(msg)


def _value_encode(entry_proto, value: Primitive) -> None:
    """Encode value."""

    if isinstance(value, bool):
        entry_proto.bool_value = value
    elif isinstance(value, int):
        entry_proto.int_value = value
    elif isinstance(value, float):
        entry_proto.float_value = str(value)
    elif isinstance(value, str):
        entry_proto.str_value = value
    elif isinstance(value, bytes):
        entry_proto.bytes_value = value
    else:
        msg = f"Unsupported value type: {value}"
        raise TypeError(msg)


class ErrorCode(Enum):
    """This class represents an instance of ErrorCode."""

    UNSUPPORTED_PROTOCOL = 0
    OPENAI_ERROR = 1
    OTHER_EXCEPTION = 2

    @staticmethod
    def encode(error_code_protobuf_object, error_code_object: "ErrorCode") -> None:
        """Encode an instance of this class into the protocol buffer object."""
        error_code_protobuf_object.error_code = error_code_object.value

    @classmethod
    def decode(cls, error_code_protobuf_object) -> "ErrorCode":
        """Decode a protocol buffer object that corresponds with this class into an instance of this class."""
        return ErrorCode(error_code_protobuf_object.error_code)


class Kwargs(dict):
    """This class represents an instance of Kwargs."""

    @staticmethod
    def encode(kwargs_protobuf_object, kwargs_object: "Kwargs") -> None:
        """Encode an instance of this class into the protocol buffer object."""

        for key, value in kwargs_object.items():
            item = kwargs_protobuf_object.items.add()
            item.key = key
            if isinstance(value, Primitive):
                _value_encode(item.primitive, value)
            elif isinstance(value, Sequence):
                for v in value:
                    _value_encode(item.sequence.values.add(), v)  # noqa: PD011
            elif isinstance(value, dict):
                Kwargs.encode(item.mapping, value)
            else:
                msg = f"Unsupported value type: {value}"
                raise TypeError(msg)

    @classmethod
    def decode(cls, kwargs_protobuf_object) -> "Kwargs":
        """Decode a protocol buffer object that corresponds with this class into an instance of this class."""

        mapping = {}
        for item in kwargs_protobuf_object.items:
            if item.HasField("primitive"):
                mapping[item.key] = _value_decode(item.primitive)
            elif item.HasField("sequence"):
                mapping[item.key] = list(map(_value_decode, item.sequence.values))
            elif item.HasField("mapping"):
                mapping[item.key] = cls.decode(item.mapping)
            else:
                msg = f"Unsupported value type: {item}"
                raise TypeError(msg)

        return cls(mapping)


class Role(StrEnum):
    """Role."""

    DEVELOPER = "developer"
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class Message(BaseModel):
    """Message."""

    content: str
    role: Role
    name: str | None = Field(default=None)


class Messages(list):
    """This class represents an instance of Messages."""

    @staticmethod
    def encode(messages_protobuf_object, messages_object: "Messages") -> None:
        """Encode an instance of this class into the protocol buffer object."""
        for value in messages_object:
            data = value.model_dump(exclude_none=True)
            proto_message = messages_protobuf_object.messages.add()
            for key, val in data.items():
                kv_pair = proto_message.items.add()
                kv_pair.key = key
                kv_pair.value = val

    @classmethod
    def decode(cls, messages_protobuf_object) -> "Messages":
        """Decode a protocol buffer object that corresponds with this class into an instance of this class."""
        messages = []
        for message in messages_protobuf_object.messages:
            data = {kv_pair.key: kv_pair.value for kv_pair in message.items}
            messages.append(Message(**data))
        return Messages(messages)
