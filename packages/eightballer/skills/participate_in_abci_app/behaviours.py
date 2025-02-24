# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 
#   Copyright 2023 valory-xyz
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

"""This package contains a behaviour that autogenerated from the protocol ``."""

import os
from abc import ABC
from typing import Optional, Any
from aea.skills.behaviours import FSMBehaviour, State
from enum import Enum


class ParticipateinabciappEvents(Enum):
    
    DONE = 'DONE'
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'
    RETRY = 'RETRY'
    NO_NEW_MESSAGES = 'NO_NEW_MESSAGES'

class ParticipateinabciappStates(Enum):
    
    ERRORROUND = 'errorround'
    PREPAREROUND = 'prepareround'
    PAUSEROUND = 'pauseround'
    CHECKROUND = 'checkround'
    EXECUTEROUND = 'executeround'

class BaseState(State, ABC):
    """Base class for states."""
    _state: ParticipateinabciappStates = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._event = None
        self._is_done = False  # Initially, the state is not done

    def act(self) -> None:
        print(f"Performing action for state {self._state}")
        self._is_done = True
        self._event = ParticipateinabciappEvents.DONE

    def is_done(self) -> bool:
        return self._is_done

    @property
    def event(self) -> Optional[str]:
        return self._event


# Define states

class ErrorRound(BaseState):
    """This class implements the behaviour of the state ErrorRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ParticipateinabciappStates.ERRORROUND

class PrepareRound(BaseState):
    """This class implements the behaviour of the state PrepareRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ParticipateinabciappStates.PREPAREROUND

class PauseRound(BaseState):
    """This class implements the behaviour of the state PauseRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ParticipateinabciappStates.PAUSEROUND

class CheckRound(BaseState):
    """This class implements the behaviour of the state CheckRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ParticipateinabciappStates.CHECKROUND

class ExecuteRound(BaseState):
    """This class implements the behaviour of the state ExecuteRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ParticipateinabciappStates.EXECUTEROUND





class ParticipateinabciappFsmBehaviour(FSMBehaviour):
    """This class implements a simple Finite State Machine behaviour."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.register_state(ParticipateinabciappStates.CHECKROUND.value, CheckRound(**kwargs), True)
        
        
        
        self.register_state(ParticipateinabciappStates.ERRORROUND.value, ErrorRound(**kwargs)) 
        self.register_state(ParticipateinabciappStates.PREPAREROUND.value, PrepareRound(**kwargs)) 
        self.register_state(ParticipateinabciappStates.PAUSEROUND.value, PauseRound(**kwargs)) 
        self.register_state(ParticipateinabciappStates.EXECUTEROUND.value, ExecuteRound(**kwargs)) 
        
        self.register_transition(
            source=ParticipateinabciappStates.CHECKROUND.value, 
            event=ParticipateinabciappEvents.DONE,
            destination=ParticipateinabciappStates.PREPAREROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.CHECKROUND.value, 
            event=ParticipateinabciappEvents.NO_NEW_MESSAGES,
            destination=ParticipateinabciappStates.PAUSEROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.ERRORROUND.value, 
            event=ParticipateinabciappEvents.RETRY,
            destination=ParticipateinabciappStates.CHECKROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.EXECUTEROUND.value, 
            event=ParticipateinabciappEvents.DONE,
            destination=ParticipateinabciappStates.PAUSEROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.EXECUTEROUND.value, 
            event=ParticipateinabciappEvents.ERROR,
            destination=ParticipateinabciappStates.ERRORROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.PAUSEROUND.value, 
            event=ParticipateinabciappEvents.DONE,
            destination=ParticipateinabciappStates.CHECKROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.PAUSEROUND.value, 
            event=ParticipateinabciappEvents.TIMEOUT,
            destination=ParticipateinabciappStates.ERRORROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.PREPAREROUND.value, 
            event=ParticipateinabciappEvents.DONE,
            destination=ParticipateinabciappStates.EXECUTEROUND.value
        )
        self.register_transition(
            source=ParticipateinabciappStates.PREPAREROUND.value, 
            event=ParticipateinabciappEvents.TIMEOUT,
            destination=ParticipateinabciappStates.ERRORROUND.value
        )


    def setup(self) -> None:
        """Implement the setup."""
        self.context.logger.info("Setting up Participateinabciapp FSM behaviour.")


    def teardown(self) -> None:
        """Implement the teardown."""
        self.context.logger.info("Tearing down Participateinabciapp FSM behaviour.")

    def act(self) -> None:
        """Implement the act."""
        super().act()
        if self.current is None:
            self.context.logger.info("No state to act on.")
            self.terminate()

    def terminate(self) -> None:
        """Implement the termination."""
        print("Terminating the agent.")
        os._exit(0)