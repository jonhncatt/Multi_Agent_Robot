# agent-core

统一的多 agent 运行时内核。

承接内容：
- RoleSpec / RoleContext / RoleResult
- RoleInstance / TaskNode / RunState
- RoleRegistry / RuntimeController
- 通用 orchestration（后续从 app/agent.py 继续抽出）

说明：
- 这里是“多 agent 引擎”，不是具体 office 角色包。
- 具体 roles / tools / prompts 由 capability modules 提供。
- 当前已承接：
  - `RoleSpec / RoleContext / RoleResult`
  - `RoleRegistry / RuntimeController`
  - capability runtime 装配支撑
