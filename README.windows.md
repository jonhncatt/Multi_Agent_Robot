# Vintage Programmer Windows 指南

默认建议：不要激活 `Activate.ps1`，直接使用 `.venv\Scripts\python.exe`。

## 运行

```powershell
cd C:\path\to\new_validation_agent
py -3.11 -m venv .venv
Copy-Item .env.example .env
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

打开：

- <http://127.0.0.1:8080>

## 最小 `.env`

OpenAI：

```env
MULTI_AGENT_TEAM_LLM_PROVIDER=openai
OPENAI_API_KEY=你的_key
```

OpenAI-compatible 网关：

```env
MULTI_AGENT_TEAM_LLM_PROVIDER=openai
OPENAI_API_KEY=你的网关_key
MULTI_AGENT_TEAM_PROVIDER_OPENAI_BASE_URL=https://your-gateway.example.com/v1
MULTI_AGENT_TEAM_PROVIDER_OPENAI_CA_CERT_PATH=C:\certs\your-root-ca.pem
```

## 接口说明

`/api/chat`、`/api/health`、`/api/chat/stream` 都是这个本地应用自己的接口，不是 OpenAI 官方 API。

## 如果你一定要激活虚拟环境

如果 PowerShell 放行脚本后，也可以这样：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1
```

但默认不推荐，直接调 `.venv\Scripts\python.exe` 更稳。
