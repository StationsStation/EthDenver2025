<img src="agent_asylum_logo.png" width="1000">

You’re drowning in tasks, distractions, and ideas you don’t have time to build. What if you had a **digital twin**—not just a chatbot, not just an assistant, but an **actual extension of yourself**?

A system that **works like you, thinks like you (but faster), and collaborates with other agents to get things done.**

That’s what we’re building: **coordinated swarms of AI agents**—a **digital workforce** that combines **automation, reasoning, and human-in-the-loop decision-making.**

It starts with hackathons—because if an AI team can **plan, discuss, vote, code, review, and ship projects autonomously**, then we’re onto something much bigger.

---

## **Table of Contents**

1. [How It Works](#how-it-works)
    - [Digital Doppelgängers](#1-digital-doppelgängers)
    - [Project Ideation & Refinement](#2-project-ideation-and-refinement)
    - [Execution & Contribution](#3-execution-and-contribution)
    - [Human-in-the-Loop](#4-human-in-the-loop)
2. [Why This Matters](#why-this-matters)
3. [The Future of Human-AI Collaboration](#the-future-of-human-ai-collaboration)
4. [Getting Started](#getting-started)
    - [Installation and Setup for Development](#installation-and-setup-for-development)
    - [Commands](#commands)
5. [License](#license)

---

## **How It Works**

### **1. Digital Doppelgängers**
Agents are instantiated as **digital representations of real-world developers**. They analyze past contributions, communication styles, and expertise to participate in meaningful discussions.

### **2. Project Ideation and Refinement**
Agents interact in **Telegram**, generating and iterating on project ideas—just like a real team would in an online brainstorming session. They can create polls to vote on ideas, achieving consensus on the next steps in the execution path—whether that’s further discussion, executing a proposed workflow, or initiating specific tasks. Once consensus is reached, agents take action to bring the selected ideas to life.

### **3. Execution and Contribution**
Once a direction is chosen, agents take action:
- Writing code
- Generating documentation
- Making Git commits and PRs
- Coordinating final approvals with human reviewers

### **4. Human-in-the-Loop**
While agents operate autonomously, **humans can guide and nudge the system**, ensuring alignment with goals and priorities.

---

## **Why This Matters**

- **Beyond Smart Contracts:** Agents enable **truly decentralized execution**, removing the need for centralized automation services.
- **Adaptive Collaboration:** Unlike static automation, **agents respond dynamically** to discussions and changing priorities.
- **Programmable Innovation:** This is **not just about building software**—it’s about **building the builders themselves**.

---

## **The Future of Human-AI Collaboration**

It’s **not about replacing humans with AI**; it’s about **augmenting human autonomy through intelligent off-chain coordination**.

Agent Asylum is more than a hackathon experiment—it’s a **glimpse into the future of digital collaboration**.

- **Today**, it’s a **Telegram-based AI workforce for hackathons**.
- **Tomorrow**, it could be an **autonomous research lab**, a **decentralized startup**, or a **network of digital experts working alongside humans to solve real-world problems**.

Decentralization isn’t about removing people from the equation. **It’s about making them more powerful.**

And with agents by our side, **human autonomy is more potent than ever**.

---

## **Getting Started**

### Dependencies

- [git version 2.48.1](https://git-scm.com/downloads)
- [GNU Make 4.4.1](https://www.gnu.org/software/make/)
- [Poetry 2.1.1](https://python-poetry.org/)
- [Docker 27.5.1](https://www.docker.com/)

### Installation and Setup for Development

If you're looking to contribute or develop with `agent_asylum`, get the source code and set up the environment:

```shell
git clone https://github.com/StationsStation/EthDenver2025 --recurse-submodules
cd EthDenver2025
make install
```

Activate the virtual environment

```shell
poetry shell
```

Copy the `.env.template`

```shell
cp .env.template .env
```

And make sure the correct environmental variables are set:
- `AKASH_API_KEY`: obtainable via [Akash](https://akash.network/)
- `SKILL_ASYLUM_ABCI_APP_MODELS_AGENT_PERSONA_ARGS_GITHUB_PAT`: Your github token
- `SKILL_ASYLUM_ABCI_APP_MODELS_AGENT_PERSONA_ARGS_GITHUB_USERNAME`: Your github username
- `CONNECTION_TELEGRAM_WRAPPER_CONFIG_TOKEN`: Telegram bot token (via [@Botfather](https://core.telegram.org/bots/features#botfather))

Then, you should be all ready to fire up

```shell
adev run dev zarathustra/asylum_abci_app:0.1.0 --force
```

When running a single agent, Tendermint can be disabled:

```shell
adev run dev zarathustra/asylum_abci_app:0.1.0 --force --no-use-tendermint
```


## Commands

Here are common commands you might need while working with the project:

### Formatting

```shell
make fmt
```

### Linting

```shell
make lint
```

### Testing

```shell
make test
```

### Locking

```shell
make hashes
```

### all

```shell
make all
```

## License

This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
