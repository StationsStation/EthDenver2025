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

"""Test data for custom types of the sql_alchemy protocol."""

from packages.zarathustra.protocols.llm_chat_completion.custom_types import Kwargs, Messages, Message, Role


KWARGS = Kwargs(
    {
        "int": 1,
        "float": 1.1,
        "bool": True,
        "str": "apple",
        "bytes": b"byte",
        "int_sequence": [1, 2, 3],
        "float_sequence": [1.1, 2.2, 3.3],
        "bool_sequence": [True, False, True],
        "str_sequence": ["apple", "banana", "cherry"],
        "bytes_sequence": [b"byte1", b"byte2", b"byte3"],
        "mapping": {
            "int": 1,
            "float": 1.1,
            "bool": True,
            "str": "apple",
            "bytes": b"byte",
            "int_sequence": [1, 2, 3],
            "float_sequence": [1.1, 2.2, 3.3],
            "bool_sequence": [True, False, True],
            "str_sequence": ["apple", "banana", "cherry"],
            "bytes_sequence": [b"byte1", b"byte2", b"byte3"],
        },
    }
)

MESSAGES = Messages(
    [
        Message(role=Role.DEVELOPER, content="You are a developer"),
        Message(role=Role.SYSTEM, content="You are the system"),
        Message(role=Role.USER, content="You are a user"),
        Message(role=Role.ASSISTANT, content="You are an assistant"),
        Message(role=Role.TOOL, content="You are a tool"),
        Message(role=Role.FUNCTION, content="You are a function"),
    ]
)
