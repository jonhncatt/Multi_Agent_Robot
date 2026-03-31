# Multi_Agent_Robot

![Mat Multi_Agent_Robot logo](docs/assets/brand/mat-logo-horizontal.jpg)

[中文 README](README.md)

## Final Architecture

The project now follows a **minimal kernel architecture**:

- One stable Kernel (startup, context, health)
- One central LLM router (`app/kernel/llm_router.py`)
- 12 fully independent agent plugins (`app/agents/*_agent`)

Design goal: **least code, least layers, easiest maintenance, isolated failures**.

## Independent Agents (12)

1. worker_agent
2. researcher_agent
3. planner_agent
4. critic_agent
5. executor_agent
6. summarizer_agent
7. coder_agent
8. reviewer_agent
9. coordinator_agent
10. tool_user_agent
11. office_specialist_agent
12. navigator_agent

Each agent folder only has:

- `agent.py` with `handle_task`
- `manifest.json` with description/capabilities/version

## Simplified Layout

```text
app/
├── agents/
├── kernel/
│   ├── host.py
│   └── llm_router.py
├── api/
└── main.py
```

## Quick Start

```bash
git clone https://github.com/jonhncatt/Multi_Agent_Robot.git
cd Multi_Agent_Robot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./run.sh
```

Open: <http://127.0.0.1:8080>

## Key APIs

- `POST /api/chat` (central LLM routing + independent agents)
- `POST /api/chat/stream`
- `GET /api/agents`
- `POST /api/agents/{name}/reload`
- `GET /api/health`

## Generic LLM Env

```env
OFFICETOOL_LLM_PROVIDER=openai
OFFICETOOL_LLM_AUTH_MODE=auto
OFFICETOOL_LLM_API_KEY=<YOUR_API_KEY>
OFFICETOOL_LLM_BASE_URL=https://api.openai.com/v1
OFFICETOOL_LLM_MODEL=gpt-5.1-chat
OFFICETOOL_ROUTER_MODEL=gpt-4o-mini
```

## Evolution Workflow

- Update one agent under `app/agents/<name>_agent/`
- Call `POST /api/agents/{name}/reload`
- Validate immediately without restarting the full kernel

