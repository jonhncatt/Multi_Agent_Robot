# Vintage Programmer

[中文 README](README.md)  
[Windows Guide](README.windows.md)

This is a local single-agent workstation. The default main agent is `vintage_programmer`.

## Run

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./run.sh
```

Open:

- <http://127.0.0.1:8080>

### Windows

On Windows, the default recommendation is to skip script activation and call the venv Python directly:

```powershell
py -3.11 -m venv .venv
Copy-Item .env.example .env
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

More detail: [README.windows.md](README.windows.md)

## Minimal `.env`

OpenAI:

```env
MULTI_AGENT_TEAM_LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
```

OpenAI-compatible gateway:

```env
MULTI_AGENT_TEAM_LLM_PROVIDER=openai
OPENAI_API_KEY=your_gateway_key
MULTI_AGENT_TEAM_PROVIDER_OPENAI_BASE_URL=https://your-gateway.example.com/v1
MULTI_AGENT_TEAM_PROVIDER_OPENAI_CA_CERT_PATH=/absolute/path/to/your-root-ca.pem
```

More examples: [.env.example](.env.example)

## API Note

These are this app's own local HTTP endpoints, not OpenAI official APIs:

- `GET /api/health`
- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/session/new`
- `GET /api/session/{session_id}`
- `GET /api/sessions`
- `PATCH /api/session/{session_id}/title`
- `DELETE /api/session/{session_id}`
- `POST /api/upload`

The web UI talks to these local endpoints.

## Agent Specs

The main agent is defined by:

- [agents/vintage_programmer/soul.md](agents/vintage_programmer/soul.md)
- [agents/vintage_programmer/agent.md](agents/vintage_programmer/agent.md)
- [agents/vintage_programmer/tools.md](agents/vintage_programmer/tools.md)
