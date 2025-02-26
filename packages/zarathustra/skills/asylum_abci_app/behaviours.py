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

from packages.eightballer.protocols.chatroom.message import ChatroomMessage as TelegramMessage
from packages.zarathustra.skills.asylum_abci_app.scraper import GitHubScraper
from packages.zarathustra.skills.asylum_abci_app.strategy import LLMActions, AsylumStrategy
from packages.zarathustra.connections.openai_api.connection import (
    CONNECTION_ID as OPENAI_API_CONNECTION_ID,
    Model as LLMModel,
)
from packages.zarathustra.protocols.llm_chat_completion.message import LlmChatCompletionMessage
from packages.eightballer.connections.telegram_wrapper.connection import CONNECTION_ID as TELEGRAM_CONNECTION_ID
from packages.zarathustra.protocols.llm_chat_completion.custom_types import Role, Kwargs, Message, Messages


TIMEZONE_UTC = UTC

MERMAID_DIAGRAMS = Path(__file__).parent / "mermaid_diagrams"
THIS_MERMAID_PATH = MERMAID_DIAGRAMS / "asylum_abci_app.mmd"


SYSTEM_PROMPT = dedent("""
    You are responding to user messages sent via a Telegram channel.
    Users may send any kind of message, including casual conversation, questions, or gibberish.
    Your goal is to generate a serious and relevant response to all meaningful messages.

    However, if a message is nonsensical or gibberish, respond with a witty remark while including an echo of their message.

    Always reference (and tag) the user by their username (@{username}) in a natural and appropriate way within your response.
""")  # noqa: E501


class AsylumAbciAppEvents(Enum):
    """AsylumAbciAppEvents."""

    ERROR = "ERROR"
    REPLY = "REPLY"
    UPDATE_NEEDED = "UPDATE_NEEDED"
    WORK = "WORK"
    NEW_MESSAGES = "NEW_MESSAGES"
    TIMEOUT = "TIMEOUT"
    DONE = "DONE"


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

        self.data_dir = Path(__file__).parent / "data"
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)
        self.github_scraper = GitHubScraper(data_dir=str(self.data_dir))

    def act(self) -> None:
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        self._is_done = True
        self._event = AsylumAbciAppEvents.DONE
        sleep(1)

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
        self.context.logger.info(f"In state: {self._state}")

        if self.strategy.pending_workflows:
            self._event = AsylumAbciAppEvents.WORK
            self._is_done = True
            return

        if self.strategy.llm_responses:
            self.context.logger.info("Processing LLM responses")
            action, text = self.strategy.llm_responses.pop()
            self.context.logger.info(f"Action: {action}: {text}")
            if action == LLMActions.REPLY:
                self._event = AsylumAbciAppEvents.REPLY
                self._is_done = True
                self.strategy.telegram_responses.append(text)
            elif action == LLMActions.WORKFLOW:
                self._event = AsylumAbciAppEvents.WORK
                self._is_done = True

        for msg in self.strategy.telegram_responses:
            self.context.logger.info(f"Telegram response: {msg}")
            self._event = AsylumAbciAppEvents.REPLY
            self._is_done = True
        sleep(1)


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
            return
        if datetime.now(tz=TIMEZONE_UTC).timestamp() - self.processing_since > self.timeout:
            self._event = AsylumAbciAppEvents.TIMEOUT
            self._is_done = True
            self.processing_since = None
            return
        if self.strategy.pending_telegram_messages:
            self.context.logger.info(f"New messages found: {len(self.strategy.pending_telegram_messages)}")
            self._event = AsylumAbciAppEvents.NEW_MESSAGES
            self._is_done = True
            self.processing_since = None
        sleep(0.5)


class RequestLLMResponseRound(BaseState):
    """This class implements the behaviour of the state RequestLLMResponseRound."""

    counterparty = str(OPENAI_API_CONNECTION_ID)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND

    def act(self) -> None:
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        self.context.logger.info(f"Sending to: {self.counterparty}")
        workflows = [f"-{f}" for f in self.strategy.workflows]
        while self.strategy.pending_telegram_messages:
            msg = self.strategy.pending_telegram_messages.pop()
            text_data = msg.text
            username = msg.from_user
            if text_data.startswith("/help"):
                # we dummy an llm response for the work tol here.
                response = dedent(f"""
                Hi there! I am a bot. I can help you with the following workflows;
                {workflows}
                """)
                response = response.format(workflows="\n".join(workflows))
                self.strategy.telegram_responses.append(response)
            elif text_data.startswith("/workflow"):
                workflow_name = text_data.split()[1]
                if workflow_name in self.strategy.workflows:
                    self.strategy.pending_workflows.append(workflow_name)
                else:
                    self.strategy.telegram_responses.append(f"Workflow {workflow_name} not found.")
            else:
                THIS_MERMAID_PATH.read_text()
                model = LLMModel.META_LLAMA_3_3_70B_INSTRUCT
                content = [
                    Message(role=Role.SYSTEM, content=SYSTEM_PROMPT.format(username=username)),
                    Message(role=Role.USER, content=text_data, name=username),
                ]
                messages = Messages(content)
                self.create_and_send(
                    performative=LlmChatCompletionMessage.Performative.CREATE,
                    model=model,
                    messages=messages,
                    kwargs=Kwargs({}),
                )

        # we need to request the llm here.
        self._is_done = True
        self._event = AsylumAbciAppEvents.DONE

    def create_and_send(self, **kwargs) -> None:
        """Create and send a message."""
        message, _dialogue = self.context.llm_chat_completion_dialogues.create(
            counterparty=self.counterparty,
            **kwargs,
        )
        self.context.outbox.put_message(message)


class SendTelegramMessageRound(BaseState):
    """This class implements the behaviour of the state SendTelegramMessageRound."""

    counterparty = str(TELEGRAM_CONNECTION_ID)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.SEND_TELEGRAM_MESSAGE_ROUND

    def act(self):
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        while self.strategy.telegram_responses:
            text = self.strategy.telegram_responses.pop()
            self.context.logger.info(f"Sending message: {text}")
            self.create_and_send(
                performative=TelegramMessage.Performative.MESSAGE,
                chat_id="-4765622287",
                text=text,
            )
        self._is_done = True
        self._event = AsylumAbciAppEvents.DONE

    def create_and_send(self, send=True, **kwargs) -> None:
        """Create and send a message."""
        message, _dialogue = self.context.telegram_dialogues.create(
            counterparty=self.counterparty,
            **kwargs,
        )
        if send:
            self.context.outbox.put_message(message)


class ScrapeGithubRound(BaseState):
    """This class implements the behaviour of the state ScrapeGithubRound."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.SCRAPE_GITHUB_ROUND

    def act(self) -> None:
        """Perform GitHub data collection."""
        self.context.logger.info(f"In state: {self._state}")
        usernames = ["8ball030"]
        try:
            self.context.logger.info(f"Fetching data for users: {', '.join(usernames)}")
            all_user_data = self.github_scraper.scrape_user_interactions(
                usernames=usernames,
                repos=["https://github.com/valory-xyz/open-autonomy"],
            )
            self.context.shared_state["user_issues"] = all_user_data
            self._is_done = True
            self._event = AsylumAbciAppEvents.DONE

        except Exception as e:
            self.context.logger.exception(f"Error fetching GitHub data: {e!s}")


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

    def act(self):
        """Do the act."""
        self.context.logger.info(f"In state: {self._state}")
        username = "8ball030"
        user_data = self.data_dir / username

        if not user_data.exists():
            self._is_done = True
            self._event = AsylumAbciAppEvents.UPDATE_NEEDED
        else:
            self._is_done = True
            self._event = AsylumAbciAppEvents.DONE


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

        while self.strategy.pending_workflows:
            workflow_name = self.strategy.pending_workflows.pop()
            workflow_path = Path(__file__).parent / "workflows" / self.strategy.workflows[workflow_name]
            try:
                workflow = Workflow.from_file(workflow_path)
                self.wf_manager.add_workflow(workflow)
                self.wf_manager.run_workflow(workflow.id, display_process=False)
                self.context.logger.info(f"There are {len(self.strategy.llm_responses)} responses.")

            except Exception as e:
                self.context.logger.exception(f"Error: {e}")
            finally:
                result_str = dedent(f"""
                Workflow id: {workflow.id}
                Workflow name: {workflow.name}

                Total Tasks: {len(workflow.tasks)}
                Completed Tasks: {len([f for f in workflow.tasks if f.is_done])}
                Failed Tasks: {len([f for f in workflow.tasks if f.is_failed])}
                Successful Tasks: {len([f for f in workflow.tasks if not f.is_failed])}

                Workflow status: {workflow.is_done}
                Workflow is success: {workflow.is_success}
                """)
                for task in workflow.tasks:
                    result_str += dedent(
                        f"""- Task({task.id}): {task.name}: {task.is_done} - Success: {task.is_failed}"""
                    )

                self.strategy.telegram_responses.append(result_str)

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
