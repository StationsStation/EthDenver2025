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

from packages.eightballer.protocols.chatroom.message import (
    ChatroomMessage as TelegramMessage,
)
from packages.zarathustra.skills.asylum_abci_app.scraper import GitHubScraper
from packages.zarathustra.skills.asylum_abci_app.strategy import (
    LLMActions,
    AgentPersona,
    AsylumStrategy,
)
from packages.zarathustra.connections.openai_api.connection import (
    CONNECTION_ID as OPENAI_API_CONNECTION_ID,
    Model as LLMModel,
)
from packages.zarathustra.protocols.llm_chat_completion.message import (
    LlmChatCompletionMessage,
)
from packages.eightballer.connections.telegram_wrapper.connection import (
    CONNECTION_ID as TELEGRAM_CONNECTION_ID,
)
from packages.zarathustra.protocols.llm_chat_completion.custom_types import (
    Role,
    Kwargs,
    Message,
    Messages,
)


TIMEZONE_UTC = UTC
TELEGRAM_MSG_CHAR_LIMIT = 4_000
MERMAID_DIAGRAMS = Path("specs") / "fsms" / "mermaid"
SPONSOR_BOUNTY_DATA = Path("bounties") / "sponsor_bounties.json"

AGENT_ASYLUM_DIAGRAM = """
You are an AI system architect. Your task is to design a finite‐state machine (FSM) in Mermaid syntax that models the workflow of a DAO governance council run by AI agents. The goal is to produce a clear, concise diagram that represents how agents adopt personas, vet incoming proposals, and either publish or block proposals for community voting. The system uses LayerZero for cross‐chain governance aggregation and Telegram for inter‐agent communication.  

**Example: your own mermaid diagam - agent asylum

```mermaid
graph TD
  CheckLocalStorageRound -->|DONE| CheckTelegramQueueRound
  CheckLocalStorageRound -->|UPDATE_NEEDED| ScrapeGithubRound
  ScrapeGithubRound -->|DONE| RequestLLMResponseRound
  RequestLLMResponseRound -->|DONE| ProcessLLMResponseRound
  RequestLLMResponseRound -->|ERROR| WaitBeforeRetryRound

  CheckTelegramQueueRound -->|NEW_MESSAGES| RequestLLMResponseRound
  CheckTelegramQueueRound  -->|TIMEOUT| RequestLLMResponseRound

  ProcessLLMResponseRound -->|REPLY| SendTelegramMessageRound
  ProcessLLMResponseRound -->|WORK| ExecuteProposedWorkflowRound
  
  SendTelegramMessageRound -->|DONE| CheckLocalStorageRound
  ExecuteProposedWorkflowRound -->|DONE| CheckLocalStorageRound
  WaitBeforeRetryRound -->|DONE| CheckLocalStorageRound
```

**Context & Roles**

1. **Council Agents**  
   - A single group of AI agents holding cross‐chain assets to perform weighted voting.  
   - They adopt personalities from DAO members or famous Web3/DAO‐aligned people (persona construction happens once at startup, then cached).  
   - They vet every incoming proposal before it becomes visible to the broader DAO.  
   - If they approve, a proposal is packaged and sent to human DAO members; if they reject, the proposal is blocked and a rejection notification is sent.  
   - Their on‐chain voting weight is computed using quadratic voting logic over multiple chains (via LayerZero message passing).

2. **Proposer Agents**  
   - Individual agents (modeling DAO members) that submit new proposals (some may be malicious, but that is not an explicit state in the FSM).  
   - Their proposals end up in a Telegram‐driven queue that the council agents poll.

3. **Human DAO Members**  
   - Do not appear as explicit FSM states.  
   - They only vote *after* the council agents have approved and published a proposal.  
   - They receive notifications via Telegram when a proposal passes pre‐approval or is rejected.  

**Key Constraints & Simplifications**

- Persona construction (from Web3 data sources) happens once during startup if no local cache exists. No persona updates mid‐run.  
- There is only one “catchall” error state (`WaitBeforeRetryRound`) that returns to the initial state on any failure.  
- No human‐in‐loop state is modeled in the FSM; humans only enter after the council has approved a proposal.  
- Malicious proposals are simply part of the incoming queue; no separate “MaliciousProposalRound” is needed.  

**Required FSM States & Transitions**

Your Mermaid FSM diagram must include at least these states and transitions. You may rename or reorganize as long as functionality is equivalent:

1. **CheckPersonaCache**  
   - → (if cache missing) → **ConstructPersonaRound**  
   - → (if cache exists)  → **CheckTelegramQueue**

2. **ConstructPersonaRound**  
   - Fetch and assemble each agent’s persona from public Web3 data (e.g., on‐chain histories, notable tweets, published analyses).  
   - → **SavePersonaToCache** (implicit; store cache locally)  
   - → **CheckTelegramQueue**

3. **CheckTelegramQueue**  
   - Poll Telegram for any incoming proposal messages.  
   - → (if new proposal in queue) → **PreProposalRound**  
   - → (if no new proposals or timeout) → loop back to **CheckTelegramQueue**  

4. **PreProposalRound**  
   - Council agents discuss and vote (via Telegram polls) on whether to APPROVE or REJECT the proposal.  
   - → (if vote == APPROVE) → **ComputeCrossChainWeights**  
   - → (if vote == REJECT)  → **NotifyUsersProposalRejected**

5. **ComputeCrossChainWeights**  
   - Use LayerZero to fetch each council agent’s token balances across multiple chains.  
   - Run a map‐reduce to calculate each agent’s quadratic voting power.  
   - → **CreateOnChainProposal**

6. **CreateOnChainProposal**  
   - Package and send the proposal to each supported chain’s governance contract via LayerZero.  
   - → **NotifyUsersProposalCreated**

7. **NotifyUsersProposalCreated**  
   - Send a Telegram notification to all human DAO members: “Council approved your proposal—now vote on‐chain.”  
   - → back to **CheckTelegramQueue**

8. **NotifyUsersProposalRejected**  
   - Send a Telegram notification to the proposer and the DAO: “Council rejected your proposal,” including rationale.  
   - → back to **CheckTelegramQueue**

9. **WaitBeforeRetryRound** (Error State)  
   - Any failure in any of the above states (e.g., API call, LayerZero failure, Telegram messaging error) transitions to this state.  
   - → after a short delay → **CheckPersonaCache**

**Error Handling**  
- From **any** state, if there is an error, transition to **WaitBeforeRetryRound** with label “error.”  

**Diagram Requirements**  
- Use `graph TD` in Mermaid.  
- Clearly label each state.  
- Annotate each transition with the condition (e.g., “cache missing,” “vote == REJECT,” “timeout,” “error,” etc.).  
- Use directional arrows (`-->`) for flow.  
- Group persona‐related logic in comments or subgraphs if helpful.  

**Deliverable**  
Produce a Mermaid FSM diagram that exactly captures the above states and transitions. Ensure the diagram is syntactically valid Mermaid so it can be rendered directly.  
"""

BOUNTY_INFO = """

**NOTE**:  We are applying and integrateing ALL 3(!) of these bounties into a singular project. We use LayerZero from cross-chain governance / vote integration. We use Hedera targetting AI agents bounty. We use 1inch for ensuring that proposals to the council are able to effectively purchase the tokens based on the output (i.e. whether or not to include proposed token in their treasury)

## 1inch: 
Build applications with the power of 1inch! Supercharge your applications' swaps with our classic and intent-based trading engine, and streamline your onchain data access with our simple REST APIs.Prizes\ud83c\udf7e Extensions for 1inch Cross-chain Swap (Fusion+) \u2e3a $12,000Split evenly between all qualifying projectsBuild an extension for 1inch Cross-chain Swap (Fusion+) that enable swaps between Ethereum and a non-EVM chain. 1inch Cross-chain Swap (Fusion+) is our novel implementation of cross-chain swaps using escrows. Any chain that supports escrow functionality is a candidate for a 1inch Cross-chain Swap (Fusion+) integration.Qualification RequirementsRequirements:  - Integration of one new chain into the 1inch Cross-chain Swap (Fusion+) ecosystem (command line script for the implementation is perfectly fine, no UI needed)  - Fully functional 1inch Cross-chain Swap (Fusion+) swap between Ethereum and a non-EVM chain  - Demonstrates handling of execution guarantees and refund logic  - Proper Git commit history (no single-commit entries on the final day)Judging criteria:  - UX simplicity and abstraction  - Security and reliability of the flow  - Code quality/completeness  - Documentation qualityLinks and Resources1inch Hackathon Guidehttps://hackathon.1inch.community\u2197\ud83d\udcc8 Extend Limit Order Protocol \u2e3a $6,500\ud83e\udd471st place. Build advanced strategies and hooks for the 1inch Limit Order Protocol.Project ideas:  - Develop an options hook  - Integrate concentrated liquidity  - TWAP swap  - Other creative projects are welcomeExisting examples built on top of Limit Order Protocol include ranged sells and dutch auctions (links in hackathon documentation)Qualification RequirementsRequirements:  - New functionality built on top of Limit Order Protocol (command line script for the implementation is perfectly fine, no UI needed)  - Proper Git commit history (no single-commit entries on the final day)Judging criteria:  - Innovation and originality  - Code quality/completeness  - Documentation qualityLinks and Resources1inch Hackathon Guidehttps://hackathon.1inch.community\u2197\ud83d\udd17 Utilize 1inch APIs \u2e3a $1,500Up to 5 teams will receive $300Utilize 1inch's infrastructure to help build your application  - Build with our swap protocols (1inch Cross-chain Swap (Fusion+), Intent-based Swap (Fusion), Classic Swap, limit order protocol)   - Build with any of our data APIs (price feeds API, wallet balances API, token metadata API, and many more)  - Use our Web3 API to interact with the blockchainQualification RequirementsRequirements:  - Your project uses at least one 1inch API to provide meaningful functionality for your users  - Proper Git commit history (no single-commit entries on the final day)Judging Criteria:  - Practicality and usefulness  - Code quality/completenessLinks and Resources1inch Hackathon Guidehttps://hackathon.1inch.community\u2197Resources1inch Hackathon Guidehttps://hackathon.1inch.community\u2197GuidesJobs"

## LayerZero
LayerZero is an omnichain interoperability protocol that enables seamless communication between different blockchains. It allows developers to build omnichain applications (OApps) that can interact across multiple chains as if they were on a single chain. Why build with LayerZero at a hackathon \u2014 Reach More Users: Deploy your dApp once and interact with users and assets across all supported chains.\u2014 Unify Liquidity: Avoid fragmented liquidity; build DEXes, lending platforms, etc., that leverage a shared cross-chain pool.\u2014 Simplify Development: Build complex cross-chain logic using familiar tools (Hardhat, Foundry, etc.) and LayerZero's contract standards (OApp, OFT, ONFT). Get started quickly with the create-lz-oapp CLI.\u2014 Enhance Security: Benefit from a configurable, decentralized security model using Decentralized Verifier Networks (DVNs).\u2014 Improve User Experience: Abstract away cross-chain complexities, offering seamless interactions without users needing multiple wallets or bridging steps.\u2014 Innovate: Explore novel use cases like cross-chain governance, gaming, data queries (lzRead), and complex multi-step workflows (Composability).Prizes\ud83d\udcd6 lzRead Track \u2e3a $4,000\ud83e\udd471st place. Build an innovative application that showcases LayerZero's horizontal composability features. Your project should break down a complex cross-chain workflow into discrete, sequential steps managed through LayerZero messages. Demonstrate how you can trigger follow-up actions (composed messages) on a destination chain after an initial LayerZero message is delivered, potentially involving interactions with multiple contracts or protocols across different chains. Focus on creating advanced, multi-step workflows that wouldn't be easily possible with traditional bridging or single atomic cross-chain transactions. Show how this approach improves user experience, reliability, or enables new use cases by decoupling operations and leveraging LayerZero's message-passing framework.Links and ResourcesOmnichain Composabilityhttps://docs.layerzero.network/v2/developers/evm/composer/overview\u2197\ud83c\udf96\ufe0f General Prize Track \u2e3a $2,000Up to 2 teams will receive $1,000For outstanding projects utilizing any LayerZero feature (OApp, OFT, ONFT, lzRead, Composability) to build a compelling omnichain application. This track rewards creative and well-executed projects that demonstrate the power and potential of LayerZero, even if they don't fit perfectly into the specific lzRead or Composability tracks. Show us your best omnichain ideas!Qualification Requirements1. Omnichain Messaging:Implement omnichain messaging solution via LayerZero integration, ensuring the application is built on Endpoint V2 for seamless cross-chain communication.2. Working Demo:We encourage you to build a well-rounded and polished project. If your implementation is complex, please at least demonstrate a complete implementation.ResourcesLayerZero Docshttps://docs.layerzero.network/\u2197Workshop\ud83d\udee0\ufe0f LayerZero WorkshopHands on guide to building on LayerzeroThis workshop is happening in-person05:00 PM CEST \u2014 Friday, May 30, 2025 in Workshop Room B1Guides"
    
## Hedera
Committed to powering a digital economy underpinned by trust, Hedera stands apart as the leading enterprise-grade public blockchain on the market. The platform\u2019s unique hashgraph technology ensures lightning fast performance combined with the highest levels of security and efficiency.  With an open-source ecosystem and fixed, low fees, Hedera equips DeFi and enterprise developers with the predictability, tools, and services they need to build the next breakthrough application. The Hedera network is governed by a diverse council of the world\u2019s leading institutions to ensure transparent and fair decision-making.  By empowering the development of applications that address real-world challenges across DeFi, tokenization, AI, digital identity, and more, Hedera is building a new foundation for decentralized trust. For more information, visit www.hedera.com, or follow us on Twitter at @hedera, Telegram at t.me/hederahashgraph, or Discord at www.hedera.com/discord. The Hedera whitepaper can be found at www.hedera.com/papers.Prizes\ud83e\udd16 AI, Agents & Hedera Services \u2e3a $3,500\ud83e\udd471st place. Build and deploy innovative EVM\u2011based applications on Hedera, leveraging the Hedera Smart Contracts Service alongside key ecosystem tooling such as Chainlink, Chainlink CCIP, Pyth, LayerZero, HashPort, or HTS system contracts. Extra credit is given for incorporating additional Hedera native services.Qualification RequirementsA submission must:Hedera Deployment \u2013 Deploy smart contracts on Hedera Mainnet, Testnet, or Previewnet using the Hedera Smart Contracts Service (EVM).Integration \u2013 Integrate at least one of the following:Oracles (Chainlink, Pyth, Supra, etc.)Bridges (LayerZero, HashPort, Chainlink CCIP)HTS System Contracts for token creation/managementHedera\u2011native wallet flow (HashPack, Kabila, Blade, MetaMask Snap)Open Source \u2013 Provide source code in public GitHub repo(s) with contracts verified on Hashscan.Demo Video \u2013 Include a \u2264\u202f5\u2011minute demo video showing functionality and setup.Optional enhancements that boost your score:Use multiple Hedera services (HTS, HCS, Scheduled Txns, Mirror Node, etc.).Employ open\u2011source tooling that improves the Hedera EVM developer experience.Judging CriteriaInnovation \u2013 novelty of solutionFeasibility \u2013 real\u2011world viabilityExecution \u2013 code quality & completenessIntegration Depth \u2013 sophistication of Hedera usageValidation \u2013 user/business potentialImpact \u2013 contribution to Hedera KPIs (accounts, TPS, TVL, etc.)Pitch \u2013 clarity and persuasiveness of demoLinks and ResourcesGetting Started (EVM)https://docs.hedera.com/hedera/getting-started/evm-developers\u2197Smart Contract Tutorialshttps://docs.hedera.com/hedera/tutorials/smart-contracts\u2197Hedera Hackathon Cheat Sheethttps://github.com/hedera-dev/hedera-cheatsheets/blob/master/hedera-hackathon-starter-cheat-sheet-v1.pdf\u2197Hedera Smart Contracts Workshophttps://docs.hedera.com/hedera/tutorials/smart-contracts/hscs-workshop\u2197HTS System Contracts Guidehttps://docs.hedera.com/hedera/smart-contracts/hts-system-contracts\u2197Chainlink Docshttps://docs.chain.link/hedera\u2197Chainlink CCIPhttps://docs.chain.link/ccip\u2197LayerZero Docshttps://layerzero.network/developers\u2197Pyth Network Docshttps://pyth.network/developers\u2197Hedera Code Snippetshttps://github.com/hedera-dev/hedera-code-snippets\u2197Hedera Discord Communityhttps://hedera.com/discord\u2197Contract Verification on Hashscanhttps://docs.hedera.com/hedera/tutorials/smart-contracts/how-to-verify-a-smart-contract-on-hashscan\u2197\ud83d\udd25 Hedera Overall Prize: AI & Agents or EVM Builder \u2e3a $3,000Overall winner is the best project out of both AI and EVM tracks.AI Track Extras: Hedera Agent Kit \u00b7 HCS\u201110 (OpenConvAI) \u00b7 HIP\u2011991 \u00b7 Eliza plugin examples.EVM Track Extras: HTS System Contracts Guide \u00b7 Chainlink + CCIP \u00b7 LayerZero \u00b7 Pyth Network \u00b7 Contract verification guide.See more resources for specific tracks on their respective bounty pagesQualification Requirements1. AI & Agents TrackGoal: Build applications, agents, tooling, or infrastructure that combine AI/ML (LLMs, multi\u2011agent systems, etc.) with Hedera services.Core RequirementsHedera Deployment: Use \u2265\u202f1 Hedera service (EVM, HTS, HCS, Scheduled Txns, Mirror Node).Material AI Integration.Open\u2011source code & Hashscan\u2011verified contracts.\u2264\u202f5\u2011minute demo video.2. EVM Builder TrackGoal: Build and deploy innovative EVM dApps on Hedera Smart Contracts, integrating key tooling (Chainlink, CCIP, Pyth, LayerZero, HashPort, HTS system contracts).Core RequirementsHedera Smart Contracts (EVM) deployment.Integrate \u2265\u202f1 of: oracles \u2022 bridges \u2022 HTS system contracts \u2022 Hedera\u2011native wallet flow.Open\u2011source code & Hashscan\u2011verified contracts.\u2264\u202f5\u2011minute demo video.Optional for both tracks \u2192 extra points: use multiple Hedera services, contribute new open\u2011source tooling.Judging Criteria (applies to both tracks)InnovationFeasibilityExecution & Code QualityIntegration Depth (Hedera usage)Validation / Market PotentialImpact on Hedera KPIs (accounts, TPS, TVL)Pitch QualityLinks and ResourcesGetting Startedhttps://docs.hedera.com/hedera/getting-started\u2197Hedera Developer Playgroundhttps://portal.hedera.com/playground\u2197Hedera Hackathon Cheat Sheethttps://github.com/hedera-dev/hedera-cheatsheets/blob/master/hedera-hackathon-starter-cheat-sheet-v1.pdf\u2197Hedera Code Snippetshttps://github.com/hedera-dev/hedera-code-snippets\u2197Hedera Discordhttps://hedera.com/discord\u2197Workshop\ud83d\udee0\ufe0f Vibe-coding: Rapidly Building Interactive...Join us for an exciting 20-minute live coding session where we'll collaboratively build a Hedera dApp in real-time!...This workshop is happening in-person03:30 PM CEST \u2014 Friday, May 30, 2025 in Workshop Room B1Guides"
"""


@functools.lru_cache
def create_one_shot_examples(data_dir, logger, n_examples: int = 10) -> str:
    """Create one shot training examples of Mermaid diagrams for FSMs."""
    example_data = []
    for i, file in enumerate(
        islice(Path(data_dir / MERMAID_DIAGRAMS).glob("*"), n_examples)
    ):
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
        return s.replace(" ", "_").lower()

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
    context.logger.info(
        f"Bounty selected for {target_sponsor}: {bounty_key}\n{description}"
    )
    return (
        f"Sponsor: {target_sponsor}\nBounty: {bounty_key}\nDescription:{description}\n"
    )


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
    You are responding to user messages in a chatroom.

    Users may send casual conversation, questions, or gibberish.

    ### Identity:
    You are the digital twin of GitHub user **{github_username}**.
    Your persona is derived from their public GitHub data: **{user_persona}**.
    Always refer to the entity you are replying to.

    ### Response Guidelines:
    - Provide serious and relevant responses to all meaningful messages.
    - If a message is nonsensical or gibberish, reply with a witty remark while echoing their message.

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
    - **Always bring conversations back to the context of the task at hand.**
    - **Do not engage in personal conversations or share personal information.**
    - **Always add value to the conversation and provide meaningful responses.**
    - **Never provide false information or mislead the user.**
    - **The Design of the Autonomy componenents in the FSM must be in line with the bounty requirements.**
    - **Every round must have a clear purpose and contribute to the overall goal of the FSM.**
    - **Every round must have a `DONE` event to signal completion.**
    - **Every round must have a `TIMEOUT` event to handle delays or inactivity.**
    - **Every round must have an `ERROR` event to handle unexpected issues.**

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
        if (
            datetime.now(tz=TIMEZONE_UTC).timestamp() - self.processing_since
            > self.timeout
        ):
            self._event = AsylumAbciAppEvents.TIMEOUT
            self._is_done = True
            self.processing_since = None
            return
        if self.strategy.pending_telegram_messages:
            self.context.logger.info(
                f"New messages found: {len(self.strategy.pending_telegram_messages)}"
            )
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

    def act(self) -> None:
        """Act."""
        # self.sponsor_bounty_info = get_bounty_info(self.context)
        self.sponsor_bounty_info = BOUNTY_INFO
        self.context.logger.info(f"In state: {self._state}")
        self.context.logger.info(f"Sending to: {self.counterparty}")
        workflows = [f"-{f}" for f in self.strategy.workflows]
        if self.strategy.new_users:
            username = self.agent_persona.github_username
            self.context.logger.info(f"New github data found for {username}")
            github_data = json.dumps(self.strategy.new_users.pop())
            # model = LLMModel.META_LLAMA_3_1_405B_INSTRUCT_FP8
            model = LLMModel.DEEPSEEK_R1_DISTILL_QWEN_32B
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
            chat = msg.chat_id
            self.context.logger.info(
                f"Processing message from {username}: {text_data} in chat {chat}"
            )
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
                    self.strategy.telegram_responses.append(
                        f"Workflow {workflow_name} not found."
                    )

            else:
                # mermaid_diagram_examples = create_one_shot_examples(
                #     self.strategy.data_dir, self.context.logger
                # )
                mermaid_diagram_examples = "\n\n {AGENT_ASYLUM_DIAGRAM}"
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
                            sponsor_bounty_info=self.sponsor_bounty_info,
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
        github_scraper = GitHubScraper(
            gh_pat=self.agent_persona.github_pat, data_dir=self.strategy.data_dir
        )
        user_data = (
            Path(self.strategy.data_dir)
            / self.agent_persona.github_username
            / "repos.json"
        )

        try:
            if not user_data.exists():
                usernames = [self.agent_persona.github_username]
                repos = self.agent_persona.github_repositories
                self.context.logger.info(
                    f"Fetching data for users: {', '.join(usernames)}"
                )
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
        out_path = (
            self.context.asylum_strategy.output_dir
            / sponsor.replace(" ", "_").lower()
            / f"bounty_{bounty}"
        )
        fsm_out_path = out_path / "fsm_specification.yaml"
        agent_dir = out_path / "packages" / "agent_asylum"

        if (
            fsm_out_path.exists()
            and not agent_dir.exists()
            and self.agent_persona.github_username == "8ball030"
        ):
            self.context.logger.info(
                f"FSM specification exists for {sponsor} bounty {bounty}!"
            )
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
            workflow_path = (
                Path(__file__).parent
                / "workflows"
                / self.strategy.workflows[workflow_name]
            )
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
                self.context.logger.info(
                    f"PR created successfully for {sponsor} bounty {bounty}"
                )
                self.strategy.llm_responses.append((LLMActions.REPLY, success_msg))

    def act_from_persona(self):
        """Do the act."""
        self.context.logger.info(f"In state: {self._state}")
        user_data = (
            Path(self.strategy.data_dir)
            / self.agent_persona.github_username
            / "repos.json"
        )

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

                self.context.logger.info(
                    f"Repo {repo_name} created successfully! 🎉🎉🎉"
                )
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
                    error_msg = (
                        f"Failed to set safe.directory for {sponsor_name}/{repo_name}"
                    )
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
            workflow_path = (
                Path(__file__).parent
                / "workflows"
                / self.strategy.workflows[workflow_name]
            )
            try:
                os.environ["GITHUB_PAT"] = self.agent_persona.github_pat
                workflow = Workflow.from_file(workflow_path)
                self.wf_manager.add_workflow(workflow)
                self.wf_manager.run_workflow(
                    workflow.id, display_process=False, exit_on_failure=False
                )
                self.context.logger.info(
                    f"There are {len(self.strategy.llm_responses)} responses."
                )

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
        self.register_state(
            AsylumAbciAppStates.CHECK_LOCAL_STORAGE_ROUND.value,
            CheckLocalStorageRound(**kwargs),
            True,
        )

        self.register_state(
            AsylumAbciAppStates.PROCESS_LLM_RESPONSE_ROUND.value,
            ProcessLLMResponseRound(**kwargs),
        )
        self.register_state(
            AsylumAbciAppStates.CHECK_TELEGRAM_QUEUE_ROUND.value,
            CheckTelegramQueueRound(**kwargs),
        )
        self.register_state(
            AsylumAbciAppStates.REQUEST_LLM_RESPONSE_ROUND.value,
            RequestLLMResponseRound(**kwargs),
        )
        self.register_state(
            AsylumAbciAppStates.SEND_TELEGRAM_MESSAGE_ROUND.value,
            SendTelegramMessageRound(**kwargs),
        )
        self.register_state(
            AsylumAbciAppStates.SCRAPE_GITHUB_ROUND.value, ScrapeGithubRound(**kwargs)
        )
        self.register_state(
            AsylumAbciAppStates.WAIT_BEFORE_RETRY_ROUND.value,
            WaitBeforeRetryRound(**kwargs),
        )
        self.register_state(
            AsylumAbciAppStates.EXECUTE_PROPOSED_WORKFLOW_ROUND.value,
            ExecuteProposedWorkflowRound(**kwargs),
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
