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

"""This package contains the behaviours for the AsylumAbciApp."""

import os
from abc import ABC
from enum import Enum
from time import sleep
from typing import Any, cast
from pathlib import Path
from datetime import UTC, datetime
from textwrap import dedent

from aea.skills.behaviours import State, FSMBehaviour
from auto_dev.workflow_manager import Workflow, WorkflowManager

from packages.zarathustra.skills.asylum_abci_app.strategy import AsylumStrategy
from packages.zarathustra.connections.openai_api.connection import CONNECTION_ID


TIMEZONE_UTC = UTC


class AsylumAbciAppEvents(Enum):
    """AsylumAbciAppEvents."""

    ERROR = "ERROR"
    REPLY = "REPLY"
    UPDATE_NEEDED = "UPDATE_NEEDED"
    WORK = "WORK"
    NEW_MESSAGES = "NEW_MESSAGES"
    TIMEOUT = "TIMEOUT"
    DONE = "DONE"


class LLMActions(Enum):
    """LLMActions."""

    WORKFLOW = "workflow"
    REPLY = "reply"


class AsylumAbciAppStates(Enum):
    """AsylumAbciAppStates."""

    PROCESS_LLM_RESPONSE_ROUND = "processllmresponseround"
    CHECK_TELEGRAM_QUEUE_ROUND = "checktelegramqueueround"
    REQUEST_LLM_RESPONSE_ROUND = "requestllmresponseround"
    SEND_TELEGRAM_MESSAGE_ROUND = "sendtelegrammessageround"
    SCRAPE_GITHUB_ROUND = "scrapegithubround"
    WAIT_BEFORE_RETRY_ROUND = "waitbeforeretryround"
    CHECK_LOCAL_STORAGE_ROUND = "checklocalstorageround"
    EXECUTE_PROPOSED_WORKFLOW_ROUND = "executeproposedworkflowround"


class BaseState(State, ABC):
    """Base class for states."""

    _state: AsylumAbciAppStates = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._event = None
        self._is_done = False  # Initially, the state is not done

    def act(self) -> None:
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        self._is_done = True
        self._event = AsylumAbciAppEvents.DONE
        sleep(0.2)

    def is_done(self) -> bool:
        """Is done flag."""
        return self._is_done

    @property
    def event(self) -> str | None:
        """Event."""
        return self._event

    @property
    def strategy(self):
        """Get the strategy."""
        return cast(AsylumStrategy, self.context.asylum_strategy)


class ProcessLLMResponseRound(BaseState):
    """This class implements the behaviour of the state ProcessLLMResponseRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.PROCESS_LLM_RESPONSE_ROUND

    def act(self) -> None:
        """Act."""
        self._is_done = True
        self._event = AsylumAbciAppEvents.WORK
        self.context.logger.info(f"In state: {self._state}")
        while self.strategy.llm_responses:
            action = self.strategy.llm_responses.pop()
            self.context.logger.info(f"Action: {action}")
            if action[0] == LLMActions.REPLY:
                self._event = AsylumAbciAppEvents.REPLY
                self._is_done = True
            elif action[0] == LLMActions.WORKFLOW:
                self._event = AsylumAbciAppEvents.WORK
                self._is_done = True


class CheckTelegramQueueRound(BaseState):
    """This class implements the behaviour of the state CheckTelegramQueueRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.CHECK_TELEGRAM_QUEUE_ROUND
        self.processing_since = None
        self.timeout = 60

    def act(self) -> None:
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        if self.processing_since is None:
            self.processing_since = datetime.now(tz=TIMEZONE_UTC).timestamp()
        if datetime.now(tz=TIMEZONE_UTC).timestamp() - self.processing_since > self.timeout:
            self._event = AsylumAbciAppEvents.TIMEOUT
            self._is_done = True
            self.processing_since = None
        if self.strategy.pending_messages:
            self.context.logger.info(f"New messages found: {len(self.strategy.pending_messages)}")
            self._event = AsylumAbciAppEvents.NEW_MESSAGES
            self._is_done = True
            self.processing_since = None
        sleep(0.5)


class RequestLLMResponseRound(BaseState):
    """This class implements the behaviour of the state RequestLLMResponseRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND

    def act(self) -> None:
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        self.context.logger.info(f"Sending to: {CONNECTION_ID}")
        while self.strategy.pending_messages:
            msg = self.strategy.pending_messages.pop()
            text_data = msg.text
            if text_data.startswith("/work"):
                # we dummy an llm response for the work tol here.
                self.strategy.llm_responses.append((LLMActions.WORKFLOW, "create_new_repo.yaml"))

        # we need to request the llm here.
        self._is_done = True
        self._event = AsylumAbciAppEvents.DONE


class SendTelegramMessageRound(BaseState):
    """This class implements the behaviour of the state SendTelegramMessageRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.SEND_TELEGRAM_MESSAGE_ROUND


class ScrapeGithubRound(BaseState):
    """This class implements the behaviour of the state ScrapeGithubRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.SCRAPE_GITHUB_ROUND


class WaitBeforeRetryRound(BaseState):
    """This class implements the behaviour of the state WaitBeforeRetryRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.WAIT_BEFORE_RETRY_ROUND


class CheckLocalStorageRound(BaseState):
    """This class implements the behaviour of the state CheckLocalStorageRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND


class ExecuteProposedWorkflowRound(BaseState):
    """This class implements the behaviour of the state ExecuteProposedWorkflowRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.EXECUTE_PROPOSED_WORKFLOW_ROUND
        self.wf_manager = WorkflowManager()

    def act(self) -> None:
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        # we now do the work.
        try:
            workflow_path = Path(__file__).parent / "workflows" / "create_new_repo.yaml"
            workflow = Workflow.from_file(workflow_path)
            self.wf_manager.add_workflow(workflow)
            self.wf_manager.run_workflow(workflow.id, display_process=False)
            result_str = dedent(f"""
            Workflow id: {workflow.id}
            Workflow name: {workflow.name}
            Workflow status: {workflow.is_done}
            Workflow is success: {workflow.is_success}
            """)
            self.strategy.llm_responses.append((LLMActions.REPLY, result_str))

        except Exception as e:
            self.context.logger.exception(f"Error: {e}")
        finally:
            self._is_done = True
            self._event = AsylumAbciAppEvents.DONE


class AsylumAbciAppFsmBehaviour(FSMBehaviour):
    """This class implements a simple Finite State Machine behaviour."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.register_state(AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value, CheckLocalStorageRound(**kwargs), True)

        self.register_state(AsylumAbciAppStates.PROCESS_LLM_RESPONSE_ROUND.value, ProcessLLMResponseRound(**kwargs))
        self.register_state(AsylumAbciAppStates.CHECK_TELEGRAM_QUEUE_ROUND.value, CheckTelegramQueueRound(**kwargs))
        self.register_state(AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value, RequestLLMResponseRound(**kwargs))
        self.register_state(AsylumAbciAppStates.SEND_TELEGRAM_MESSAGE_ROUND.value, SendTelegramMessageRound(**kwargs))
        self.register_state(AsylumAbciAppStates.SCRAPE_GITHUB_ROUND.value, ScrapeGithubRound(**kwargs))
        self.register_state(AsylumAbciAppStates.WAIT_BEFORE_RETRY_ROUND.value, WaitBeforeRetryRound(**kwargs))
        self.register_state(
            AsylumAbciAppStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value, ExecuteProposedWorkflowRound(**kwargs)
        )

        self.register_transition(
            source=AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value,
            event=AsylumAbciAppEvents.DONE,
            destination=AsylumAbciAppStates.CHECK_TELEGRAM_QUEUE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value,
            event=AsylumAbciAppEvents.UPDATE_NEEDED,
            destination=AsylumAbciAppStates.SCRAPE_GITHUB_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.CHECK_TELEGRAM_QUEUE_ROUND.value,
            event=AsylumAbciAppEvents.NEW_MESSAGES,
            destination=AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.CHECK_TELEGRAM_QUEUE_ROUND.value,
            event=AsylumAbciAppEvents.TIMEOUT,
            destination=AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value,
            event=AsylumAbciAppEvents.DONE,
            destination=AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.PROCESS_LLM_RESPONSE_ROUND.value,
            event=AsylumAbciAppEvents.REPLY,
            destination=AsylumAbciAppStates.SEND_TELEGRAM_MESSAGE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.PROCESS_LLM_RESPONSE_ROUND.value,
            event=AsylumAbciAppEvents.WORK,
            destination=AsylumAbciAppStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value,
            event=AsylumAbciAppEvents.DONE,
            destination=AsylumAbciAppStates.PROCESS_LLM_RESPONSE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value,
            event=AsylumAbciAppEvents.ERROR,
            destination=AsylumAbciAppStates.WAIT_BEFORE_RETRY_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.SCRAPE_GITHUB_ROUND.value,
            event=AsylumAbciAppEvents.DONE,
            destination=AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.SEND_TELEGRAM_MESSAGE_ROUND.value,
            event=AsylumAbciAppEvents.DONE,
            destination=AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value,
        )
        self.register_transition(
            source=AsylumAbciAppStates.WAIT_BEFORE_RETRY_ROUND.value,
            event=AsylumAbciAppEvents.DONE,
            destination=AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value,
        )

    def setup(self) -> None:
        """Implement the setup."""
        self.context.logger.info("Setting up AsylumAbciApp FSM behaviour.")

    def teardown(self) -> None:
        """Implement the teardown."""
        self.context.logger.info("Tearing down AsylumAbciApp FSM behaviour.")

    def act(self) -> None:
        """Implement the act."""
        super().act()
        if self.current is None:
            self.context.logger.info("No state to act on.")
            self.terminate()

    def terminate(self) -> None:
        """Implement the termination."""
        os._exit(0)
