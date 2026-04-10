# Vintage Programmer

[English README](README.en.md)  
[Windows 指南](README.windows.md)

这是一个本地运行的单主 agent 工作台，默认主 agent 是 `vintage_programmer`。

## 运行

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./run.sh
```

默认打开：

- <http://127.0.0.1:8080>

### Windows

Windows 默认建议不要激活脚本，直接调用虚拟环境里的 Python：

```powershell
py -3.11 -m venv .venv
Copy-Item .env.example .env
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

详细说明见 [README.windows.md](README.windows.md)。

## `.env` 最小配置

最简单的 OpenAI 配置：

```env
MULTI_AGENT_TEAM_LLM_PROVIDER=openai
OPENAI_API_KEY=你的_key
```

如果你走 OpenAI-compatible 网关：

```env
MULTI_AGENT_TEAM_LLM_PROVIDER=openai
OPENAI_API_KEY=你的网关_key
MULTI_AGENT_TEAM_PROVIDER_OPENAI_BASE_URL=https://your-gateway.example.com/v1
MULTI_AGENT_TEAM_PROVIDER_OPENAI_CA_CERT_PATH=/absolute/path/to/your-root-ca.pem
```

更多示例见 [.env.example](.env.example)。

## 接口说明

下面这些都是这个项目自己的本地 HTTP 接口，不是 OpenAI 官方 API：

- `GET /api/health`
- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/session/new`
- `GET /api/session/{session_id}`
- `GET /api/sessions`
- `PATCH /api/session/{session_id}/title`
- `DELETE /api/session/{session_id}`
- `POST /api/upload`

浏览器页面和前端工作台就是调用这些本地接口。

## Agent 规范

主 agent 由这三份 markdown 规范定义：

- [agents/vintage_programmer/soul.md](agents/vintage_programmer/soul.md)
- [agents/vintage_programmer/agent.md](agents/vintage_programmer/agent.md)
- [agents/vintage_programmer/tools.md](agents/vintage_programmer/tools.md)
