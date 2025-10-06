# InsightEngine TODO

本 TODO 文档基于 `module/README.md` 与 `module/insightengine/readme.md` 的设计，目标是把模块化的工作拆解为 M1/M2/M3 可交付项，带验收标准、优先级、开发提示与常用命令，方便快速落地与验收。

---

## 快速说明

- 语言: Python 3.11+
- 运行时/框架建议: FastAPI (控制面)、nats-py (JetStream)、asyncio 异步
- 本地依赖建议: Postgres、MinIO、NATS (JetStream)、Redis、Qdrant（或 Weaviate）

---

## 工作分期与高优先级任务

### M1（基础可用 / 最小可交付） — 优先级: 高

目标: 实现从文件上传事件到解析事件的闭环，搭建本地开发栈，保证可观察性与幂等。

任务清单:

1. 添加依赖与开发环境

   - 在 `pyproject.toml` 填入基本依赖（见 Implementation 段）
   - 创建 `docker-compose.dev.yml`（包含 Postgres、MinIO、NATS、Redis、Qdrant）
   - 验收: `docker compose -f docker-compose.dev.yml up` 后依赖服务可联通

2. Parser Service PoC

   - 路径: `src/insightengine/services/parser/`
   - 功能: 订阅 `notevault.file.uploaded.v1`；支持 Markdown + PDF（使用 PyMuPDF 或 markdown-it-py）；输出 `insight.file.parsed.v1`
   - 事件字段: `event_id, trace_id, tenant, payload.object_key, payload.version, segments[], attachments[], stats`
   - 验收: 上传示例文件后，在 NATS 中能看到 `insight.file.parsed.v1`，并能通过 HTTP health endpoint 查询状态

3. Orchestrator v0

   - 路径: `src/insightengine/services/orchestrator/`
   - 功能: 订阅解析事件，管理 ack/retry/死信（DLQ）逻辑，导出 Prometheus 指标（parser_latency_seconds、parser_error_total、pipeline_retry_total）
   - 验收: 故意抛出异常的消息进入 DLQ，重试计数可见，Prometheus 可抓到基本指标

4. 基本 DB/元数据 schema

   - 使用 Alembic/SQLAlchemy 建立 `files`, `segments`, `events` 三张表，events 存 processed_event_id 用于幂等
   - 验收: 能在 DB 中查询到 parsed 段落和事件处理记录

5. 本地开发 README 与示例脚本
   - `scripts/publish-sample.py`: 用于发布 `notevault.file.uploaded.v1` 测试事件
   - README 节点包括运行步骤与常用命令

6. Crawler Service PoC

- 路径: `src/insightengine/services/crawler/`
- 功能: 支持至少一个 connector（例如知乎热榜或 Bilibili 公共页面），实现页面抓取 → 结果清洗 → 发布 `insight.crawler.page.fetched.v1`。
- 要点: 简单的速率限制（每个目标每分钟 N 次）、URL 去重、错误重试（指数退避）、保存原始响应到对象存储。
- 验收: 在本地 dev stack 下执行 crawler PoC，可以看到 `insight.crawler.page.fetched.v1` 事件，且在对象存储中有相应原始抓取文件。

### M2（知识闭环 / 功能完善） — 优先级: 中高

目标: 引入复杂解析、抽取、向量化和 ModelOps 能力，覆盖常见文件格式与抽取能力。

任务清单:

1. 多格式解析扩展

   - 增加 Office（docx、xlsx、pptx）、OCR（pytesseract 或 Tika）、ASR（whisper 后端）支持
   - 验收: 对应格式的示例文件能被解析并生成 `insight.file.parsed.v1`

2. Extractor Service

   - 路径: `src/insightengine/services/extractor/`
   - 功能: 订阅 `insight.file.parsed.v1`，抽取实体/关系/摘要（spaCy / transformers），输出 `insight.file.extracted.v1`
   - 验收: 样例文档输出 entities/relations/summary，结构化 JSON 满足 contract

3. Vector Service

   - 路径: `src/insightengine/services/vector/`
   - 功能: 批量 embedding（sentence-transformers 或 调用 cloud provider），写入 Qdrant/Weaviate/pgvector；维护 model_version
   - 验收: `insight.file.indexed.v1` 事件包含 vector_ids 与 model_version，向量库可检索相似段落

4. QA & ModelOps 基础

   - 指标采集（accuracy proxies、coverage、latency）、人工复核 API（admin endpoints）
   - 验收: 可以在 admin API 查看抽取样本与标注任务，能触发补偿重跑

5. 可观测性与日志完善
   - 集成 OpenTelemetry / Prometheus / Grafana dash
   - 验收: Trace 可以跨服务追踪（trace_id 贯穿），关键指标展示在 Grafana

6. Crawler 扩展（M2）

- 拓展 connectors：Bilibili（可选 API 或页面解析）、更多站点的热榜/用户行为数据、通用 HTML connector（带 CSS/XPath 支持）。
- 增加 JS 渲染能力（Playwright）用于抓取需要渲染的页面。
- 授权管理：安全存储并轮换 Cookie/API Key；UI 或 API 用于注册抓取目标与授权凭证。
- 数据治理：内容指纹、隐私脱敏、采集白名单/黑名单规则。
- 验收: 新增 connector 的契约测试通过；抓取到的页面能够被 Parser/Extractor 正确消费并进入向量化流程。

### M3（平台化 / 生产化） — 优先级: 中

目标: 模型注册、灰度、权限、多租户与自动化运维。

任务清单:

1. Model Registry（mlflow 或自建）
2. 灰度与回滚策略（基于 model_version 的路由与 A/B）
3. 多租户隔离（索引命名空间、限速、配额）
4. 长流程编排（Temporal）与补偿流程完善

5. Crawler 平台化

- 多租户抓取配额与隔离：按 tenant 限速、限额、命名空间隔离抓取产物。
- 抗封禁与代理池：商业代理轮换、失败转代理、反爬策略检测与自动退避。
- 法律与合规自动化：在抓取目标注册时自动检查 robots.txt、记录同意/授权凭证、暴露删除/保留策略 API。
- 运维：爬虫作业监控面板（成功率、平均延迟、被封禁次数）、告警与自动重试策略。


---

## 事件契约摘录（最小必需字段）

- `notevault.file.uploaded.v1`

```json
{
  "event_id": "",
  "trace_id": "",
  "tenant": "",
  "payload": {
    "object_key": "",
    "version": "",
    "bucket": "",
    "content_type": "",
    "size": 0
  }
}
```

- `insight.file.parsed.v1`

```json
{
  "event_id": "",
  "trace_id": "",
  "tenant": "",
  "payload": {
    "object_key": "",
    "version": "",
    "segments": [
      {
        "segment_id": "",
        "text": "",
        "meta": {}
      }
    ],
    "attachments": [],
    "stats": {}
  }
}
```

- `insight.file.extracted.v1`

```json
{
  "payload": {
    "object_key": "",
    "version": "",
    "entities": [],
    "relations": [],
    "summary": "",
    "clean_segments": []
  }
}
```

- `insight.file.indexed.v1`

```json
{
  "payload": {
    "object_key": "",
    "version": "",
    "vector_ids": [],
    "index": {
      "type": "qdrant",
      "collection": ""
    },
    "model_version": ""
  }
}
```

> 要求: 每条事件必须包含 `event_id`、`trace_id`、`tenant` 与唯一 `business_id`（`object_key+version`）以便幂等与追踪。

---

## Implementation 建议（库/工具清单）

- Core: FastAPI, pydantic, uvicorn
- Events: nats-py (JetStream)
- DB: SQLAlchemy (async) + asyncpg + Alembic
- Storage: minio (minio-py) 或 boto3
- Parser libs: PyMuPDF, markdown-it-py, python-docx, openpyxl, python-pptx
- OCR/ASR: pytesseract / whisper 或 后端转写服务
- NLP: spaCy, transformers, sentence-transformers
- Vector: qdrant-client 或 weaviate-client / pgvector
- Observability: prometheus-client, opentelemetry, grafana
- Jobs/Worker: Dramatiq 或 Celery（如需复杂重试、长任务）

---

## 本地开发与常用命令（示例）

- 启动本地依赖（在模块根目录）

```powershell
docker compose -f docker-compose.dev.yml up -d
```

- 安装依赖并在 venv 中运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 或使用 poetry / pipx 基于 pyproject
```

- 启动 Parser PoC

```powershell
python -m src.insightengine.services.parser.app
```

- 发布测试事件

```powershell
python scripts/publish-sample.py --file samples/test.md
```

---

## 测试与质量门（建议）

- 单元: pytest + pytest-asyncio（覆盖 parser 的文本拆分、extractor 的实体抽取逻辑）
- 集成: 在 CI 中使用 docker-compose 启动依赖，运行 end-to-end smoke test（upload→parsed→extracted→indexed）
- Lint/Format: ruff, black

---

## 验收标准（示例）

- M1 验收: 在本地 dev stack 下上传 sample 文件，能在 NATS 中看到解析事件并在 Postgres 中落地 segments，Prometheus 展示 parser latency。
- M2 验收: Extractor 输出 entities/relations/summary，向量库检索返回 top-k 相似段落，QA 面板显示抽取覆盖率指标。

---

## 分配与估时（建议模板）

- 每项任务填入: 负责人、预计工时、验收日期、依赖项

示例:

- Parser PoC: 负责人 = @alice；预计 = 3 天；依赖 = docker-compose.dev；验收 = 上传 test.md 触发 parsed 事件

---

## 后续扩展建议（可选）

- 提供一个 admin 界面对索引与模型版本进行人工干预
- 支持按 tenant 的索引隔离与回滚
- 提供模型影子流量（shadow traffic）用于评估新模型

---

如果你希望，我可以立刻执行下列任一项:

1. 在 `pyproject.toml` 中加入推荐依赖并生成 `requirements.txt` + `docker-compose.dev.yml`（M1 所需）。
2. 生成 Parser Service starter（`src/insightengine/services/parser/` 含 FastAPI app、NATS subscriber、解析实现与测试脚本）。
3. 生成 `IMPLEMENTATION.md`（将 TODO 转为 sprint backlog）。

回复 1/2/3 来选择下一步，或说明你要先看哪些部分再开始。
