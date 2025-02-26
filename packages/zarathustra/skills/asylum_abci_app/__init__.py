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

"""This module contains the implementation of the asylum ABCI app skill."""

from pydantic import BaseModel, AliasGenerator, ConfigDict

from aea.configurations.base import PublicId


PUBLIC_ID = PublicId.from_str("zarathustra/asylum_abci_app:0.1.0")


def snake_to_kebab(text: str) -> str:
    return text.replace("_", "-")


class PydanticModel(BaseModel):
    """PydanticModel"""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        alias_generator=AliasGenerator(
            validation_alias=snake_to_kebab,
            serialization_alias=snake_to_kebab,
        ),
    )
