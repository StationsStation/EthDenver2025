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

"""This package contains the behaviours for the AsymlumAbciApp."""

import os
from abc import ABC
from typing import Optional, Any
from aea.skills.behaviours import FSMBehaviour, State
from enum import Enum


class AsymlumabciappEvents(Enum):
    
    ERROR = 'ERROR'
    REPLY = 'REPLY'
    UPDATE_NEEDED = 'UPDATE_NEEDED'
    WORK = 'WORK'
    NEW_MESSAGES = 'NEW_MESSAGES'
    TIMEOUT = 'TIMEOUT'
    DONE = 'DONE'

class AsymlumabciappStates(Enum):
    
    PROCESS_LLM_RESPONSE_ROUND = 'processllmresponseround'
    CHECK_TELEGRAM_QUEUE_ROUND = 'checktelegramqueueround'
    REQUEST_LLM_RESPONSE_ROUND = 'requestllmresponseround'
    SEND_TELEGRAM_MESSAGE_ROUND = 'sendtelegrammessageround'
    SCRAPE_GITHUB_ROUND = 'scrapegithubround'
    WAIT_BEFORE_RETRY_ROUND = 'waitbeforeretryround'
    CHECK_LOCAL_STORAGE_ROUND = 'checklocalstorageround'
    EXECUTE_PROPOSED_WORKFLOW_ROUND = 'executeproposedworkflowround'

class BaseState(State, ABC):
    """Base class for states."""
    _state: AsymlumabciappStates = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._event = None
        self._is_done = False  # Initially, the state is not done

    def act(self) -> None:
        print(f"Performing action for state {self._state}")
        self._is_done = True
        self._event = AsymlumabciappEvents.DONE

    def is_done(self) -> bool:
        return self._is_done

    @property
    def event(self) -> Optional[str]:
        return self._event


# Define states

class ProcessLLMResponseRound(BaseState):
    """This class implements the behaviour of the state ProcessLLMResponseRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.PROCESS_LLM_RESPONSE_ROUND

    def act(self) -> None:
        print(f"Performing action for state {self._state}")
        self._is_done = True
        self._event = AsymlumabciappEvents.REPLY

class CheckTelegramQueueRound(BaseState):
    """This class implements the behaviour of the state CheckTelegramQueueRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.CHECK_TELEGRAM_QUEUE_ROUND

    def act(self) -> None:
        print(f"Performing action for state {self._state}")
        self._is_done = True
        self._event = AsymlumabciappEvents.NEW_MESSAGES

class RequestLLMResponseRound(BaseState):
    """This class implements the behaviour of the state RequestLLMResponseRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND

class SendTelegramMessageRound(BaseState):
    """This class implements the behaviour of the state SendTelegramMessageRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.SEND_TELEGRAM_MESSAGE_ROUND

class ScrapeGithubRound(BaseState):
    """This class implements the behaviour of the state ScrapeGithubRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.SCRAPE_GITHUB_ROUND

class WaitBeforeRetryRound(BaseState):
    """This class implements the behaviour of the state WaitBeforeRetryRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.WAIT_BEFORE_RETRY_ROUND

class CheckLocalStorageRound(BaseState):
    """This class implements the behaviour of the state CheckLocalStorageRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND

class ExecuteProposedWorkflowRound(BaseState):
    """This class implements the behaviour of the state ExecuteProposedWorkflowRound."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsymlumabciappStates.EXECUTE_PROPOSED_WORKFLOW_ROUND


class AsymlumabciappFsmBehaviour(FSMBehaviour):
    """This class implements a simple Finite State Machine behaviour."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.register_state(AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND.value, CheckLocalStorageRound(**kwargs), True)
        
        self.register_state(AsymlumabciappStates.PROCESS_LLM_RESPONSE_ROUND.value, ProcessLLMResponseRound(**kwargs)) 
        self.register_state(AsymlumabciappStates.CHECK_TELEGRAM_QUEUE_ROUND.value, CheckTelegramQueueRound(**kwargs)) 
        self.register_state(AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND.value, RequestLLMResponseRound(**kwargs)) 
        self.register_state(AsymlumabciappStates.SEND_TELEGRAM_MESSAGE_ROUND.value, SendTelegramMessageRound(**kwargs)) 
        self.register_state(AsymlumabciappStates.SCRAPE_GITHUB_ROUND.value, ScrapeGithubRound(**kwargs)) 
        self.register_state(AsymlumabciappStates.WAIT_BEFORE_RETRY_ROUND.value, WaitBeforeRetryRound(**kwargs)) 
        self.register_state(AsymlumabciappStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value, ExecuteProposedWorkflowRound(**kwargs)) 
        
        self.register_transition(
            source=AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND.value, 
            event=AsymlumabciappEvents.DONE,
            destination=AsymlumabciappStates.CHECK_TELEGRAM_QUEUE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND.value, 
            event=AsymlumabciappEvents.UPDATE_NEEDED,
            destination=AsymlumabciappStates.SCRAPE_GITHUB_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.CHECK_TELEGRAM_QUEUE_ROUND.value, 
            event=AsymlumabciappEvents.NEW_MESSAGES,
            destination=AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.CHECK_TELEGRAM_QUEUE_ROUND.value, 
            event=AsymlumabciappEvents.TIMEOUT,
            destination=AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value, 
            event=AsymlumabciappEvents.DONE,
            destination=AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.PROCESS_LLM_RESPONSE_ROUND.value, 
            event=AsymlumabciappEvents.REPLY,
            destination=AsymlumabciappStates.SEND_TELEGRAM_MESSAGE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.PROCESS_LLM_RESPONSE_ROUND.value, 
            event=AsymlumabciappEvents.WORK,
            destination=AsymlumabciappStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND.value, 
            event=AsymlumabciappEvents.DONE,
            destination=AsymlumabciappStates.PROCESS_LLM_RESPONSE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND.value, 
            event=AsymlumabciappEvents.ERROR,
            destination=AsymlumabciappStates.WAIT_BEFORE_RETRY_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.SCRAPE_GITHUB_ROUND.value, 
            event=AsymlumabciappEvents.DONE,
            destination=AsymlumabciappStates.REQUEST_LLM_RESPONSE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.SEND_TELEGRAM_MESSAGE_ROUND.value, 
            event=AsymlumabciappEvents.DONE,
            destination=AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND.value
        )
        self.register_transition(
            source=AsymlumabciappStates.WAIT_BEFORE_RETRY_ROUND.value, 
            event=AsymlumabciappEvents.DONE,
            destination=AsymlumabciappStates.CHECK_LOCAL_STORAGE_ROUND.value
        )


    def setup(self) -> None:
        """Implement the setup."""
        self.context.logger.info("Setting up Asymlumabciapp FSM behaviour.")


    def teardown(self) -> None:
        """Implement the teardown."""
        self.context.logger.info("Tearing down Asymlumabciapp FSM behaviour.")

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
