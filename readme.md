# InsightEngine 模块说明

InsightEngine 是 another-mentor 的“智能解析与索引平台”，负责把 notevault 上传的多模态资料转化为高质量结构化数据、向量索引与知识图谱可消费的事件。模块采用事件驱动架构，由若干可独立伸缩的子服务组成，协同完成解析、抽取、向量化与质量治理。

## 1. 服务划分

| 子服务                       | 主要职责                                                                                                            | 输入                                        | 输出                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------- |
| **Parser Service**           | 将原始文件（Markdown/HTML、PDF、Office、图片 OCR、音视频 ASR）解码为结构化段落与附件引用，补充基础元信息            | `notevault.file.uploaded.v1` 事件 / S3 对象 | `insight.file.parsed.v1` 事件（含段落、附件、文本统计）             |
| **Extractor Service**        | 对解析结果执行 NLP 实体/关系/表格抽取、摘要生成、文本清洗与分段，为图谱与索引提供优质信号                           | `insight.file.parsed.v1`                    | `insight.file.extracted.v1`（结构化实体、关系、摘要、清洗后的段落） |
| **Vector Service**           | 批量向量化（Embedding）、向量库写入（Weaviate/Qdrant/pgvector）、倒排/全文索引同步，管理模型版本与灰度策略          | `insight.file.extracted.v1`                 | `insight.file.indexed.v1`（向量 ID、索引位置、版本信息）            |
| **Orchestrator（Pipeline）** | 基于 NATS JetStream / Watermill 调度 parser → extractor → vector → mindgraph 流程，提供重试、死信、优先级、幂等控制 | 订阅各阶段事件                              | 控制事件流、落地任务状态、触发补偿                                  |
| **QA & ModelOps**            | 采集解析/抽取/向量化质量指标，管理模型版本、人工复核、补偿任务与成本监控                                            | 事件流 / 监控指标                           | 仪表板、告警、人工干预面板                                          |

> 早期阶段可将子服务以单体方式部署，后续按负载逐步拆分独立服务与工作队列。

| **Crawler Service**         | 抓取公开 Web 资源与第三方站点（例如哔哩哔哩用户使用情况、特定网站使用情况、知乎热榜等），对抓取结果进行清洗、结构化并以事件发布到管道 | 调度任务 / 外部目标 URL / API 授权         | `insight.crawler.page.fetched.v1`、`insight.crawler.user.activity.v1`（见下文契约） |

## 2. 事件与数据契约

InsightEngine 依赖 NATS JetStream 进行事件编排，核心主题如下：

1. `notevault.file.uploaded.v1`

   ```json
   {
     "event_id": "evt-123",
     "trace_id": "trace-abc",
     "tenant": "tenant-A",
     "payload": {
       "object_key": "user/2025/09/foo.pdf",
       "version": "v1",
       "bucket": "notevault-prod",
       "content_type": "application/pdf",
       "size": 123456,
       "uploader": "user-001"
     }
   }
   ```

2. `insight.file.parsed.v1`

   ```json
   {
     "event_id": "evt-456",
     "trace_id": "trace-abc",
     "tenant": "tenant-A",
     "payload": {
       "object_key": "user/2025/09/foo.pdf",
       "version": "v1",
       "segments": [
         {
           "segment_id": "seg-1",
           "text": "第一段正文……",
           "language": "zh",
           "meta": { "page": 1, "type": "paragraph" }
         }
       ],
       "attachments": [{ "id": "img-1", "type": "image", "object_key": "..." }],
       "stats": { "token_count": 1024 }
     }
   }
   ```

3. `insight.file.extracted.v1`

   ```json
   {
     "payload": {
       "object_key": "user/2025/09/foo.pdf",
       "version": "v1",
       "entities": [{ "type": "Person", "text": "张三", "offset": [0, 2] }],
       "relations": [{ "type": "WorksAt", "head": "张三", "tail": "公司A" }],
       "summary": "文档提到……",
       "clean_segments": ["清洗后的段落……"]
     }
   }
   ```

4. `insight.file.indexed.v1`

   ```json
   {
     "payload": {
       "object_key": "user/2025/09/foo.pdf",
       "version": "v1",
       "vector_ids": ["vec-1", "vec-2"],
       "index": { "type": "qdrant", "collection": "tenant_A" },
       "model_version": "text-embedding-3-small@2025-09-01"
     }
   }
   ```

---

## 爬虫服务（Crawler Service）

目的：以可审计、可重试、可控速率的方式抓取第三方站点与公开 Web 数据，将爬取结果转为同一事件流（供 Parser/Extractor/Vector 使用），并把隐私与合规策略内置到采集流程中。

功能要点：

- 支持多种抓取器（connectors）：Bilibili（API 或页面解析）、知乎热榜（页面/API）、通用网站（HTML 抽取、JS 渲染支持）。
- 可注册的目标与调度：按 tenant、频率、窗口、优先级调度抓取任务。
- 速率限制与并发控制：按目标站点与 tenant 细粒度限速（避免被封禁并满足合规）。
- 授权/登录处理：支持 Cookie/Token 管理、OAuth／API Key 等认证方式的安全存储与轮换。
- 去重与断点续抓：基于 URL 与内容指纹（例如 SHA256）去重并支持断点续抓。
- 结果清洗与分段：把页面或 API 返回标准化为 segments / attachments，添加 meta（source、crawl_time、status_code、response_headers）。
- 事件输出：发布 `insight.crawler.page.fetched.v1` 或 `insight.crawler.user.activity.v1`，链路中携带 `event_id`、`trace_id` 与 `tenant`。

示例事件契约（最小字段）

`insight.crawler.page.fetched.v1`

```json
{
  "event_id": "evt-789",
  "trace_id": "trace-xyz",
  "tenant": "tenant-A",
  "payload": {
    "source": "zhihu/hotlist",
    "object_key": "crawler/zhihu/2025-10-06/hotlist-1.json",
    "url": "https://www.zhihu.com/hot",
    "status_code": 200,
    "fetched_at": "2025-10-06T12:00:00Z",
    "segments": [
      { "segment_id": "seg-1", "text": "热搜条目文本...", "meta": { "rank": 1 } }
    ],
    "stats": { "token_count": 128 }
  }
}
```

`insight.crawler.user.activity.v1`（示例，适用于抓取平台用户使用情况）

```json
{
  "event_id": "evt-790",
  "trace_id": "trace-xyz",
  "tenant": "tenant-A",
  "payload": {
    "source": "bilibili/user_activity",
    "user_id": "user-123",
    "object_key": "crawler/bilibili/user-123/2025-10-06.json",
    "fetched_at": "2025-10-06T12:00:00Z",
    "activities": [ { "type": "view", "target": "av12345", "time": "..." } ],
    "meta": { "auth_used": "api_key|cookie", "rate_limited": false }
  }
}
```

隐私与合规要点：

- 优先使用公开 API；若采用页面抓取，务必遵守目标站点的 robots.txt、服务条款与当地法律。对私有/登录后的数据，应取得用户授权或只抓取用户明确允许的数据范围。
- 日志中对敏感信息（cookie、authorization header、个人身份标识）进行脱敏或仅存加密摘要。
- 提供数据保留策略与删除 API（支持按 tenant / user 的删除请求）。

实现建议（技术栈）：

- HTTP 客户端：httpx（async）、requests（简单同步场景）。
- JS 渲染与自动化：Playwright（无头浏览器），或 Selenium（按需）。
- 解析：beautifulsoup4、lxml、readability、html5lib。JSON API 直接解析并规范化字段。
- 并发/调度：基于 AsyncIO + APScheduler / RQ / Celery 的轻量任务调度；Orchestrator 可把抓取任务作为 pipeline 的一步。
- 代理与反封禁：集成代理池、随机 User-Agent、请求间隔与指数退避。
- 测试：为每个 connector 提供契约测试与回放 mock 响应。

可观测性：

- 指标：`crawler_fetch_latency_seconds`、`crawler_fetch_error_total`、`crawler_rate_limited_total`、`crawler_pages_fetched_total`。
- 跟踪：trace_id 与 event_id 链路贯穿到后续 Parser/Extractor。


> 每个事件应携带 `event_id`、`trace_id`、`tenant` 以及 `payload.business_id（object_key + version）`，用于幂等与端到端追踪。

## 3. 数据存储组件

- **对象存储**：MinIO / S3，用于存放原始文件与解析产生的派生资源。
- **关系型数据库**：PostgreSQL，用于落地段落、抽取结果、索引元数据（可与 notevault 共用实例或独立 schema）。
- **向量库**：Weaviate / Qdrant / pgvector，存储 Embedding，并与 Vector Service 解耦。
- **倒排 / 全文索引**：Meilisearch / Elasticsearch（可按需求接入）。
- **缓存 / 队列状态**：Redis，用于任务幂等、批处理协调与速率控制。

## 4. 部署拓扑（示意）

```text
notevault.uploaded.v1 --> Parser Service --> parsed.v1 --> Extractor Service --> extracted.v1 --> Vector Service --> indexed.v1 --> mindgraph / search API
                         \                                                                               /
                          \--> QA & ModelOps <----------------------------------/
```

Orchestrator 负责订阅每个主题、管理 consumer group、执行重试 / 死信处理并输出运行指标（JetStream ack、backoff、告警等）。

## 5. 路线图对齐

- **M1（基础可用）**

  - Parser Service PoC：支持 Markdown / HTML，输出段落、附件、基础统计。
  - 事件契约与 Orchestrator v0：定义 `insight.file.parsed.v1`，实现基础调度与监控。

- **M2（知识闭环）**

  - 多格式解析：PDF、Office、OCR、ASR。
  - Extractor Service：实体 / 关系 / 表格抽取、摘要生成、文本清洗。
  - Vector Service：批量向量化、向量库适配、模型注册与版本管理。
  - QA & ModelOps：准确度、覆盖率、失败补偿、成本监控。

- **M3（平台化）**
  - 细粒度权限、配额、模型灰度策略。
  - 与 mindgraph / pathplanner 的双向集成（事件 / 查询接口）。

## 6. 可观测性与质量指标

- `parser_latency_seconds`、`parser_error_total`。
- `extractor_entities_per_doc`、`extractor_error_total`。
- `embedding_batch_size`、`vector_latency_seconds`。
- `pipeline_dead_letter_total`、`pipeline_retry_total`。
- 成本与资源：模型调用次数、GPU / CPU 使用率、存储开销。
