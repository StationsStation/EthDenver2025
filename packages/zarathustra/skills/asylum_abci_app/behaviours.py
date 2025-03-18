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
from contextlib import chdir

from git import Repo
from aea.skills.behaviours import State, FSMBehaviour
from auto_dev.commands.repo import scaffold_new_repo, create_github_repo
from aea.configurations.base import PublicId
from auto_dev.workflow_manager import Task, Workflow, WorkflowManager

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
TELEGRAM_MSG_CHAR_LIMIT = 4_000
MERMAID_DIAGRAMS = Path("specs") / "fsms" / "mermaid"
SPONSOR_BOUNTY_DATA = Path("bounties") / "sponsor_bounties.json"
BOT_PATTERN = re.compile(r"(🤖.*?🤖)")


@functools.lru_cache
def create_one_shot_examples(data_dir, logger, n_examples: int = 10) -> str:
    """Create one shot training examples of Mermaid diagrams for FSMs."""
    example_data = []
    for i, file in enumerate(islice(Path(data_dir / MERMAID_DIAGRAMS).glob("*"), n_examples)):
        example_data.append(f"{i}. {file.stem}\n{file.read_text()}")
    example_data = "\n\n".join(example_data)
    logger.info(f"FSM Example Data: {example_data}")
    return example_data


@functools.lru_cache
def get_all_bounty_info(data_dir: Path) -> dict[str, dict[str, str]]:
    """Get sponsor bounty data."""
    content = (data_dir / SPONSOR_BOUNTY_DATA).read_text()
    return json.loads(content)


@functools.lru_cache
def get_bounty_info(context) -> str:
    """Get sponsor-specific bounty-specific info."""
    all_bounties = get_all_bounty_info(context.asylum_strategy.data_dir)

    def clean_str(s: str) -> str:
        return s.replace("_", " ").lower()

    all_bounties = {clean_str(k): v for k, v in all_bounties.items()}
    target_sponsor = context.agent_persona.sponsor
    if not (sponsor_bounties := all_bounties.get(target_sponsor)):
        msg = f"{target_sponsor} not in bounty info"
        raise ValueError(msg)
    target_bounty: int = context.agent_persona.bounty
    if not (bounty := next(islice(sponsor_bounties.items(), target_bounty, None))):
        msg = f"Sponsor bounty index {target_bounty} out of range for {target_sponsor}"
        raise ValueError(msg)
    bounty_key, description = bounty
    context.logger.info(f"Bounty selected for {target_sponsor}: {bounty_key}\n{description}")
    return f"Sponsor: {target_sponsor}\nBounty: {bounty_key}\nDescription:{description}\n"


def get_chat_history(context) -> tuple[str, set[str]]:
    """Get most recent telegram chat history."""
    authors = set()
    messages = []
    for text in reversed(context.asylum_strategy.chat_history):
        if bot_match := BOT_PATTERN.search(text):
            authors.add(bot_match.group(1))
            messages.append(text)
        else:
            authors.add("Human")
            messages.append(f"Human agent says:\n{text}")
    agent_conversation = "\n\n".join(f"{i}. {msg}" for i, msg in enumerate(messages))
    return agent_conversation, authors


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
    Always refer to the entity you are replying to.

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
    5. **FSM Naming Rules** (STRICT):
       - **Every state must end with "Round".**
       - **Do not use one-letter state names or abbreviations.**
       - **Do not enclose states in square brackets (`[]`).**
       - **Event names (e.g., "DONE", "ERROR", "TIMEOUT", "RETRY", "MAX_RETRIES").**
       - **Use clear, descriptive names for all states and events.**
    6. The FSM diagram must fit within {telegram_msg_char_limit} characters to ensure it can be sent in a single Telegram message.

    ### Format rules:
    - No bracketed state names (e.g., 'InitializationRound' instead of 'A[InitializationRound]')
    - Transitions are written as `StateA -->|EVENT| StateB`
    - Each state must include all possible transitions, including ERROR and TIMEOUT if applicable

    ### Example FSMs (CORRECT FORMATTING):
    {mermaid_diagram_examples}

    ### Incorrect FSM Examples (NEVER DO THIS):
    ```mermaid
    graph TD
        A[InitializationRound] -->|DONE| B[AgentSetupRound]  # ❌ INCORRECT BRACKETS
        B -->|DONE| C[StakingContractIntegrationRound]
    ```

    ```mermaid
    graph TD
        InitializationRound -->|DONE|> AgentSetupRound  # ❌ INCORRECT ">|" NOTATION
        AgentSetupRound -->|DONE|> StakingContractIntegrationRound
    ```

    ```mermaid
    graph TD
        A -->|DONE| B  # ❌ INCORRECT: STATES MUST HAVE FULL DESCRIPTIVE NAMES
        B -->|ERROR| C
    ```

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

    ### Most recent message exchange leading up to this point (latest messages appear at the top):
    {chat_history}
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

    sponsor_bounty_info: str = ""
    counterparty = str(OPENAI_API_CONNECTION_ID)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND

    def act(self) -> None:  # noqa: PLR0914
        """Act."""
        self.sponsor_bounty_info = get_bounty_info(self.context)
        self.context.logger.info(f"In state: {self._state}")
        self.context.logger.info(f"Sending to: {self.counterparty}")
        workflows = [f"-{f}" for f in self.strategy.workflows]
        if self.strategy.new_users:
            username = self.agent_persona.github_username
            self.context.logger.info(f"New github data found for {username}")
            github_data = json.dumps(self.strategy.new_users.pop())
            model = LLMModel.META_LLAMA_3_1_405B_INSTRUCT_FP8
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
            # We could retrieve chat history and add to prompt
            if text_data.startswith("/help"):
                # we dummy an llm response for the work tol here.
                response = dedent(f"""
                Hi there! I am virtual {self.agent_persona.github_username} I can help you with the following workflows;
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
                mermaid_diagram_examples = create_one_shot_examples(self.strategy.data_dir, self.context.logger)
                model = LLMModel.META_LLAMA_3_3_70B_INSTRUCT
                github_username = self.agent_persona.github_username
                user_persona = self.context.asylum_strategy.user_persona
                chat_history, _ = get_chat_history(self.context)
                self.context.logger.info(f"I AM: {user_persona}")
                content = [
                    Message(
                        role=Role.SYSTEM,
                        content=SYSTEM_PROMPT.format(
                            username=username,
                            github_username=github_username,
                            user_persona=user_persona,
                            telegram_msg_char_limit=TELEGRAM_MSG_CHAR_LIMIT,
                            sponsor_bounty_info=self.sponsor_bounty_info,
                            mermaid_diagram_examples=mermaid_diagram_examples,
                            chat_history=chat_history,
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
            bot_flag = f"🤖{self.context.agent_persona.github_username}🤖 says: "
            msg = bot_flag + self.strategy.telegram_responses.pop()

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
        data_dir = Path(self.strategy.data_dir)
        if not data_dir.exists():
            data_dir.mkdir(parents=True)
        github_scraper = GitHubScraper(gh_pat=self.agent_persona.github_pat, data_dir=self.strategy.data_dir)
        user_data = Path(self.strategy.data_dir) / self.agent_persona.github_username / "repos.json"

        try:
            if not user_data.exists():
                usernames = [self.agent_persona.github_username]
                repos = self.agent_persona.github_repositories
                self.context.logger.info(f"Fetching data for users: {', '.join(usernames)}")
                all_user_data = github_scraper.scrape_user_interactions(
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

        sponsor = self.agent_persona.sponsor.lower().replace(" ", "_")
        bounty = str(self.agent_persona.bounty)
        out_path = self.context.asylum_strategy.output_dir / sponsor.replace(" ", "_").lower() / f"bounty_{bounty}"
        fsm_out_path = out_path / "fsm_specification.yaml"
        agent_dir = out_path / "packages" / "agent_asylum"

        if fsm_out_path.exists() and not agent_dir.exists() and self.agent_persona.github_username == "8ball030":
            self.context.logger.info(f"FSM specification exists for {sponsor} bounty {bounty}!")
            self._run_scaffold_workflow(out_path, sponsor, bounty)
            self._is_done = True
            self._event = AsylumAbciAppEvents.DONE
            return
        self.act_from_persona()

    def _run_scaffold_workflow(self, out_path: Path, sponsor: str, bounty: str):
        """We run the scaffold workflow."""
        with chdir(str(out_path)):
            self.context.logger.info(f"Running scaffold workflow for {out_path}")
            workflow_name = "create_from_fsm"
            workflow_path = Path(__file__).parent / "workflows" / self.strategy.workflows[workflow_name]
            wf = Workflow.from_file(workflow_path)
            new_public_id = PublicId.from_str(f"agent_asylum/{sponsor}_{bounty}")
            kwargs = {
                "new_author": new_public_id.author,
                "new_agent": new_public_id.name,
                "new_skill": new_public_id.name,
                "sponsor": sponsor,
                "bounty": bounty,
            }
            wf.kwargs.update(kwargs)
            wf_manager = WorkflowManager()
            wf_manager.add_workflow(wf)
            wf_manager.run_workflow(wf.id, exit_on_failure=False, display_process=False)

            repo = Repo(".")
            # We create a branch for the new FSM
            branch_name = f"feature/{sponsor}_{bounty}@{datetime.now(tz=TIMEZONE_UTC).strftime('%Y%m%d%H%M%S')}"
            repo.git.checkout("-b", branch_name)
            repo.git.add(".")

            commit_msg = f"Add FSM for {sponsor} bounty {bounty}"
            repo.git.commit("-m", commit_msg)
            repo.git.push("origin", branch_name)
            self.context.logger.info(f"Pushed branch {branch_name} to origin")
            # We now execute a pr into main
            title = f"Add FSM for {sponsor} bounty {bounty} at {datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"

            body = f"""
            This PR adds the FSM for {sponsor} bounty {bounty}.
            Scaffolded using the create_from_fsm workflow.
            Please give the repo some love!
            """

            task = Task(
                command=f"gh pr create --title '{title}' --body '{body}' --base main --head {branch_name}",
            ).work()
            if task.is_failed:
                error_msg = f"Failed to create PR for {sponsor} bounty {bounty}"
                self.context.logger.error(error_msg)
                self.strategy.llm_responses.append((LLMActions.REPLY, error_msg))
            else:
                success_msg = f"PR created successfully for {sponsor} bounty {bounty}. "
                self.context.logger.info(f"PR created successfully for {sponsor} bounty {bounty}")
                self.strategy.llm_responses.append((LLMActions.REPLY, success_msg))

    def act_from_persona(self):
        """Do the act."""
        self.context.logger.info(f"In state: {self._state}")
        user_data = Path(self.strategy.data_dir) / self.agent_persona.github_username / "repos.json"

        if not user_data.exists() or not self.strategy.user_persona:
            self._is_done = True
            self._event = AsylumAbciAppEvents.UPDATE_NEEDED
        else:
            self._is_done = True
            self._event = AsylumAbciAppEvents.DONE

        # non-optimal implmentation as atm only 8baller has write access.
        if self.agent_persona.github_username != "8ball030":
            return

        # we check if the repo is there if not, we execute the workflow for it.
        bounty = str(self.agent_persona.bounty)
        repo_name = "bounty_" + bounty
        sponsor_name = self.agent_persona.sponsor.lower().replace(" ", "_")
        expected_path = Path(self.strategy.output_dir) / sponsor_name / repo_name
        if not expected_path.exists():
            # we need to execute the workflow for the user.
            if not Path(self.strategy.output_dir / sponsor_name).exists():
                Path(self.strategy.output_dir / sponsor_name).mkdir(parents=True)

            with chdir(self.strategy.output_dir / sponsor_name):
                self.context.logger.info(f"Creating new repo: {repo_name}")
                scaffold_new_repo(
                    logger=self.context.logger,
                    name=repo_name,
                    type_of_repo="autonomy",
                    force=True,
                    auto_approve=True,
                    install=False,
                    initial_commit=True,
                    verbose=False,
                )

                self.context.logger.info(f"Creating new repo: {repo_name} on GitHub")

                self.context.logger.info(f"Repo {repo_name} created successfully! 🎉🎉🎉")
                response = create_github_repo(
                    repo_name=f"{sponsor_name}_{repo_name}",
                    token=self.agent_persona.github_pat,
                    user="agent-asylum",
                    private=False,
                    is_org=True,
                )
                self.context.logger.info(f"Response: {response}")

                task = Task(
                    command=f"git config --global --add safe.directory /output/{sponsor_name}/{repo_name}",
                ).work()
                if task.is_failed:
                    error_msg = f"Failed to set safe.directory for {sponsor_name}/{repo_name}"
                    self.context.logger.error(error_msg)
                    self.strategy.llm_responses.append((LLMActions.REPLY, error_msg))
                else:
                    success_msg = f"safe.directory set successfully for {sponsor_name}/{repo_name}. "
                    self.context.logger.info(success_msg)
                    self.strategy.llm_responses.append((LLMActions.REPLY, success_msg))
                repo = Repo(repo_name)
                token = self.agent_persona.github_pat
                remote_url = f"https://{token}@github.com/agent-asylum/{sponsor_name}_bounty_{bounty}.git"
                repo.create_remote("origin", remote_url)
                repo.git.branch("-M", "main")
                repo.git.push("--set-upstream", "origin", "main")

                if response.get("status") == 201:
                    msg = f"""
                    Repo {repo_name} created successfully! 🎉🎉🎉
                    You can find it at: {response.get("html_url")}
                    """
                    self.strategy.llm_responses.append((LLMActions.REPLY, msg))


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
                os.environ["GITHUB_PAT"] = self.agent_persona.github_pat
                workflow = Workflow.from_file(workflow_path)
                self.wf_manager.add_workflow(workflow)
                self.wf_manager.run_workflow(workflow.id, display_process=False, exit_on_failure=False)
                self.context.logger.info(f"There are {len(self.strategy.llm_responses)} responses.")

            except Exception as e:
                self.context.logger.exception(f"Error: {e}")
            finally:
                # as we are sending to the user, we make this very very pretty using emjis and all.
                result_str = dedent(f"""
                {self.agent_persona.github_username} has successfully executed the workflow: {workflow_name} 🎉🎉🎉
                ---
                Workflow id:    {workflow.id}
                Workflow name:  {workflow.name}
                Workflow success: {"✅" if not workflow.is_success else "❌"}
                ---
                Total Tasks: {len(workflow.tasks)}
                Completed Tasks: {len([f for f in workflow.tasks if f.is_done])}
                Failed Tasks: {len([f for f in workflow.tasks if f.is_failed])}
                Successful Tasks: {len([f for f in workflow.tasks if not f.is_failed])}
                ---
                """)
                for task in workflow.tasks:
                    result_str += dedent(
                        # we can do that so much better!
                        f"""\n{"✅" if not task.is_failed else "❌"} Task({task.id}): {task.name}"""
                    )
                bot_flag = f"🤖{self.context.agent_persona.github_username}🤖 says: "
                result_str = bot_flag + "\n" + result_str
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
        try:
            super().act()
        except Exception as e:
            self.context.logger.exception(f"Error in AsylumAbciApp FSM: {e!s}")
            self.context.logger.exception("Terminating AsylumAbciApp FSM.")
            self.terminate()
        if self.current is None:
            self.context.logger.info("No state to act on.")
            self.terminate()

    def terminate(self) -> None:
        """Implement the termination."""
        os._exit(0)
