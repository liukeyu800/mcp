# DB-Agent 使用说明

本项目提供一个将自然语言问题自动转为 SQL 并查询数据库的服务，默认提供“本地规则引擎”兜底方案，同时兼容基于 LangGraph + LLM 的规划执行链路。

## 快速开始
1. 安装依赖（Windows PowerShell 示例）
   - `pip install -r requirement.txt`
2. 配置环境（在项目根目录下创建/修改 `.env`）
   - 关键项（示例，按需修改）：
     - LLM_PROVIDER=ollama 或 openai
     - OLLAMA_BASE=http://<your_ollama_host>:11434
     - OLLAMA_MODEL=<your_ollama_model>
     - OPENAI_API_KEY=sk-***（若使用 OpenAI）
     - OPENAI_MODEL=gpt-4o-mini 等（若使用 OpenAI）
     - 数据库连接配置（例如 DB_URL / DB_HOST / DB_NAME / DB_USER / DB_PASS 等，按项目已有字段为准）
3. 启动服务
   - `python -m app.server`
   - 服务默认监听：http://127.0.0.1:9621
4. 健康检查
   - `GET /health` 返回 `{ "ok": true }`

## 主要接口
- `POST /plan`
  - 入参 JSON：
    - `question`: 必填，自然语言问题
    - `thread_id`: 选填，会话 ID（不传则自动生成，用于多轮记忆/追踪）
  - 返回 JSON（核心字段）：
    - `answer.data`: 查询结果数组
    - `steps`: 决策与执行轨迹（含生成的 SQL 及预览）
    - `known_tables`: 相关表名
    - `thread_id`: 会话 ID
  - 决策模式（由环境变量 `DECIDER` 控制）：
    - `DECIDER=simple`（默认）：启用“本地规则引擎”，不依赖外部 LLM，立刻可用。
      - 能力：从中文问题中解析卫星代号（如 PRSS-1）或中文名（包含“卫星”的短语），自动生成联表 SQL：
        - 从 `aircraft_info` 联到 `aircraft_team`（条件：`aircraft_team.aircraft_id = aircraft_info.id`）
        - 查询负责人与联系方式：`manage_leader`(+phone)、`overall_contact`(+phone)、`center_contact`(+phone)
      - 中文编码纠偏：对 `publicity_name`、`manage_leader`、`overall_contact`、`center_contact` 做 latin1→utf8 纠偏，避免中文乱码。
    - 其他值（如 `DECIDER=llm`）：启用 LangGraph + LLM 规划器链路。
      - 需要 `.env` 中正确配置 `LLM_PROVIDER` 及其对应参数（Ollama 或 OpenAI）。
      - 已在 LLM 请求处禁用系统代理环境（使用 `trust_env=False`），若需经代理访问，请自行按需调整 `app/planner_decide.py`。

- `POST /list_tables`
  - 列出当前数据库可见的表。
- `POST /describe_table`
  - 入参：`table` 表名；返回该表的字段信息。
- `POST /read_query`
  - 入参：`sql`，可选 `limit`（默认 1000）、`read_only`（默认 true）；执行读查询。

## 使用示例
- 示例问题：
  - “查询巴基斯坦遥感卫星一号（PRSS-1）的负责人姓名和电话”
  - “PRSS-1 的总体联系人电话是多少？”
  - “查询高分一号的在轨中心联系人及电话”
- PowerShell 调用示例：
  ```powershell
  $body = @{ question = "查询巴基斯坦遥感卫星一号（PRSS-1）的负责人姓名和电话" }
  Invoke-RestMethod -Uri http://127.0.0.1:9621/plan -Method Post -Body ($body | ConvertTo-Json) -ContentType 'application/json'
  ```
- curl 调用示例：
  ```bash
  curl -s http://127.0.0.1:9621/plan \
    -H 'Content-Type: application/json' \
    -d '{"question":"查询巴基斯坦遥感卫星一号（PRSS-1）的负责人姓名和电话"}'
  ```

## 切换到 LLM 驱动（可选）
- 设置环境变量：`DECIDER=llm`，然后启动服务。
- 确保 `.env` 中的 LLM 配置可用：
  - 若使用 Ollama：`LLM_PROVIDER=ollama`，设置 `OLLAMA_BASE`、`OLLAMA_MODEL`。
  - 若使用 OpenAI：`LLM_PROVIDER=openai`，设置 `OPENAI_API_KEY`、`OPENAI_MODEL`。
- 如需通过代理访问 LLM，请根据你的网络环境修改 `app/planner_decide.py`（默认禁用系统代理变量）。

## 代码位置导览
- `app/server.py`：
  - `/plan` 入口；本地规则引擎（`DECIDER=simple`）；中文乱码纠偏；数据库辅助接口。
- `app/planner.py`：
  - LangGraph 状态机编排（decide/act/judge）与 MemorySaver（checkpointer）。
- `app/planner_decide.py`：
  - LLM 请求实现及网络设置（禁用系统代理 `trust_env=False`）。
- `app/db.py`、`app/tools.py`、`app/guard.py`：
  - 数据库读写、工具函数与 SQL 安全（只读/LIMIT 约束等）。

## 故障排查
- 返回 500：
  - 早期需在 LangGraph 中提供 `thread_id`；当前 `/plan` 已在 LLM 模式下自动注入 `configurable.thread_id`。
- LLM 请求超时：
  - 检查 `.env` 中的 LLM 地址/模型是否可达；如需代理，请调整 `planner_decide.py`；或者使用默认 `DECIDER=simple` 先完成查询。
- 中文乱码：
  - `/plan` 的本地规则引擎返回中已增加对关键中文字段的 latin1→utf8 纠偏。

## 注意
- 请勿提交任何密钥到版本库（如 `OPENAI_API_KEY`）。
- `/read_query` 默认只读与限制行数，生产环境请配合 `guard.py` 做更严格的 SQL 安全策略。