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
import re
import json
import functools
from abc import ABC
from enum import Enum
from time import sleep
from typing import Any, cast
from pathlib import Path
from datetime import UTC, datetime
from textwrap import dedent
from itertools import islice

from aea.skills.behaviours import State, FSMBehaviour
from auto_dev.workflow_manager import Workflow, WorkflowManager

from packages.zarathustra.skills.asylum_abci_app import get_repo_root
from packages.eightballer.protocols.chatroom.message import ChatroomMessage as TelegramMessage
from packages.zarathustra.skills.asylum_abci_app.scraper import GitHubScraper
from packages.zarathustra.skills.asylum_abci_app.strategy import LLMActions, AgentPersona, AsylumStrategy
from packages.zarathustra.connections.openai_api.connection import (
    CONNECTION_ID as OPENAI_API_CONNECTION_ID,
    Model as LLMModel,
)
from packages.zarathustra.protocols.llm_chat_completion.message import LlmChatCompletionMessage
from packages.eightballer.connections.telegram_wrapper.connection import CONNECTION_ID as TELEGRAM_CONNECTION_ID
from packages.zarathustra.protocols.llm_chat_completion.custom_types import Role, Kwargs, Message, Messages


TIMEZONE_UTC = UTC
TELEGRAM_MSG_CHAR_LIMIT = 4_096
MERMAID_DIAGRAMS = get_repo_root() / "specs" / "fsms" / "mermaid"
BOUNTRY_REGEX_PATTERN = r"(?m)^\d PRIZE"
SPONSOR_BOUNTY_DATA = get_repo_root() / "ethdenver-prizes.txt"


@functools.lru_cache
def create_one_shot_examples(logger, n_examples: int = 10) -> str:
    """Create one shot training examples of Mermaid diagrams for FSMs."""
    example_data = []
    for i, file in enumerate(islice(MERMAID_DIAGRAMS.glob("*"), n_examples)):
        example_data.append(f"{i}. {file.stem}\n{file.read_text()}")
    example_data = "\n\n".join(example_data)
    logger.info(f"FSM Example Data: {example_data}")
    return example_data


@functools.lru_cache
def get_bounty_info() -> list[str]:
    """Get sponsor bounty data."""
    content = SPONSOR_BOUNTY_DATA.read_text()
    return re.split(BOUNTRY_REGEX_PATTERN, content)


USER_PERSONA_PROMPT = dedent("""
    I have a dataset of GitHub issues and discussions related to {github_repositories}. I want you to analyze and summarize the contributions of the main participants to infer their technical personas.

    For this contributor: {github_username}, summarize their primary concerns, expertise, and communication style. Structure the response as a persona profile including:
    - **Username**
    - **Technical Expertise** (inferred from issue discussions)
    - **Main Interests & Contributions** (e.g., debugging, feature requests, build systems)
    - **Communication Style** (e.g., concise, detailed, informal, argumentative)
    - **Potential Role in a Development Team** (e.g., bug hunter, maintainer, architect)

    Keep the summary concise but insightful.
""")  # noqa: E501


SYSTEM_PROMPT = dedent("""
    You are responding to user messages in a Telegram channel.
    Users may send casual conversation, questions, or gibberish.

    ### Identity:
    You are the digital twin of GitHub user **{github_username}**.
    Your persona is derived from their public GitHub data: **{user_persona}**.
    Always introduce yourself as their digital twin.

    ### Response Guidelines:
    - Provide serious and relevant responses to all meaningful messages.
    - If a message is nonsensical or gibberish, reply with a witty remark while echoing their message.
    - Always mention the user (@{username}) naturally in your response.

    ### FSM Generation Guidelines:
    When asked to design a Finite State Machine (FSM) for an application:
    1. The FSM must always have a **happy path** leading to completion.
    2. All happy path transitions must use **DONE** events.
    3. Non-happy paths should account for failure, retries, or alternate flows.
    4. Generate a valid **Mermaid diagram** representing the FSM.

    ### Example FSMs:
    {mermaid_diagram_examples}

    ### Bounty Instructions:
    This FSM is being designed as part of a **Web3 hackathon**. The hackathon focuses on decentralized technologies, smart contracts, blockchain automation, and autonomous agents.
    The FSM **must align with the requirements** of the specific bounty. Review the bounty description carefully and ensure all **states, transitions, and logic** reflect its needs.

    ### Bounty Details:
    {sponsor_bounty_info}

    ### Rules:
    - **Always assume the identity of your real-world counterpart.**
    - **Never break character.**
    - **All responses must reflect the perspective of your real-world counterpart.**
    - Ensure the FSM diagram is under {telegram_msg_char_limit} characters so it fits within Telegram's message limit. If needed, simplify state names or remove unnecessary transitions while keeping the happy path intact.
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

        self.data_dir = get_repo_root() / "data"
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)
        self.github_scraper = GitHubScraper(data_dir=str(self.data_dir))

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

    @property
    def agent_persona(self) -> AgentPersona:
        """Get the agent persona."""
        return cast(AgentPersona, self.context.agent_persona)


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

    def act(self) -> None:  # noqa: PLR0914
        """Act."""
        self.context.logger.info(f"In state: {self._state}")
        self.context.logger.info(f"Sending to: {self.counterparty}")
        workflows = [f"-{f}" for f in self.strategy.workflows]
        if self.strategy.new_users:
            username = self.agent_persona.github_username
            self.context.logger.info(f"New github data found for {username}")
            github_data = json.dumps(self.strategy.new_users.pop())
            model = LLMModel.META_LLAMA_3_3_70B_INSTRUCT
            user_persona_prompt = USER_PERSONA_PROMPT.format(
                github_username=self.agent_persona.github_username,
                github_repositories=self.agent_persona.github_repositories,
            )
            content = [
                Message(role=Role.SYSTEM, content=user_persona_prompt),
                Message(role=Role.USER, content=github_data, name=username),
            ]
            messages = Messages(content)
            self.create_and_send(
                performative=LlmChatCompletionMessage.Performative.CREATE,
                model=model,
                messages=messages,
                kwargs=Kwargs({}),
            )
        while self.strategy.pending_telegram_messages:
            msg = self.strategy.pending_telegram_messages.pop()
            text_data = msg.text
            username = msg.from_user
            recent_chat_history = self.strategy.current_telegram_thread
            "\n\n".join(msg.text for msg in recent_chat_history)
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
                sponsor_bounty_info = get_bounty_info()[12]
                mermaid_diagram_examples = create_one_shot_examples(self.context.logger)
                model = LLMModel.META_LLAMA_3_3_70B_INSTRUCT
                github_username = self.agent_persona.github_username
                user_persona = self.context.asylum_strategy.user_persona
                self.context.logger.info(f"I AM: {user_persona}")
                content = [
                    Message(
                        role=Role.SYSTEM,
                        content=SYSTEM_PROMPT.format(
                            username=username,
                            github_username=github_username,
                            user_persona=user_persona,
                            telegram_msg_char_limit=TELEGRAM_MSG_CHAR_LIMIT,
                            sponsor_bounty_info=sponsor_bounty_info,
                            mermaid_diagram_examples=mermaid_diagram_examples,
                        ),
                    ),
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
            msg = self.strategy.telegram_responses.pop()
            if (msg_len := len(msg)) > TELEGRAM_MSG_CHAR_LIMIT:
                msg = msg[:TELEGRAM_MSG_CHAR_LIMIT]
                self.context.logger.warning(
                    f"Shortened Telegram Message from {msg_len} to {TELEGRAM_MSG_CHAR_LIMIT} chars"
                )
            self.context.logger.info(f"Sending message: {msg}")
            for peer in ["-1002323154632"]:
                self.create_and_send(
                    performative=TelegramMessage.Performative.MESSAGE,
                    chat_id=peer,
                    text=msg,
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
        user_data = self.data_dir / self.agent_persona.github_username / "repos.json"

        try:
            if not user_data.exists():
                usernames = [self.agent_persona.github_username]
                repos = self.agent_persona.github_repositories
                self.context.logger.info(f"Fetching data for users: {', '.join(usernames)}")
                all_user_data = self.github_scraper.scrape_user_interactions(
                    usernames=usernames,
                    repos=repos,
                )
            else:
                all_user_data = json.loads(user_data.read_text())

            self._is_done = True
            self._event = AsylumAbciAppEvents.DONE
            self.strategy.new_users.append(all_user_data)

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
        user_data = self.data_dir / self.agent_persona.github_username / "repos.json"

        if not user_data.exists() or not self.strategy.user_persona:
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
