// 任务书 V2.0 - Part 2: 技术架构 + 7条迁移铁律
const { H1, H2, H3, P, BR, BULLET, NUM, makeTable, callout, code } = require('./common');

module.exports.part2 = () => [
  H1("3. 技术架构"),

  H2("3.1 整体架构说明"),
  P("采用「混合云」架构，将数据安全敏感的部分全部保留在本地，仅将算力密集且非数据存储的 LLM 推理调用云端 API："),
  BULLET("【本地】文档原文、向量库（Qdrant）、客户主数据（PostgreSQL）、Embedding 模型、后端 API、Agent 编排"),
  BULLET("【云端】LLM/VLM 推理（Qwen3.5-Omni-Flash）、Rerank（gte-rerank-v2）"),
  P("好处：核心数据资产不出网；模型效果接近旗舰；运维负担小；未来切换全本地仅需修改环境变量。"),

  H2("3.2 技术选型清单"),
  makeTable(
    ["层级", "组件", "技术选型", "部署位置", "说明"],
    [
      ["多模态推理", "LLM + VLM", "qwen3.5-omni-flash", "云端百炼", "一站式：文本+图片+音频+视频"],
      ["重排", "Rerank", "gte-rerank-v2", "云端百炼", "提升 Top-K 召回准确率"],
      ["向量化", "Embedding", "bge-m3", "本地 Docker", "1024 维，中英双语，本地+云端通用"],
      ["向量存储", "向量数据库", "Qdrant", "本地 Docker", "数据 100% 本地"],
      ["后端服务", "API 框架", "FastAPI + Python 3.14", "本地", "异步、高性能"],
      ["RAG 编排", "框架", "LlamaIndex", "本地", "检索 + 重排封装"],
      ["Agent 编排", "工作流", "LlamaIndex Workflows", "本地", "多 Agent 路由"],
      ["异步任务", "队列", "Celery + Redis", "本地 Docker", "700 份文档批量入库"],
      ["元数据", "关系库", "PostgreSQL", "本地 Docker", "用户、客户、文档元数据"],
      ["文件存储", "对象存储", "MinIO 或本地 FS", "本地", "原始文档保存"],
      ["前端", "Web 应用", "Next.js 15（基于 Node.js 22 LTS）", "本地", "问答 + 管理后台 + 报告"],
      ["移动端（P5）", "PWA", "Next.js 15 PWA 模式", "本地", "现场使用"],
      ["容器编排", "部署", "Docker Compose", "本地", "一键启动所有服务"],
    ],
    [1200, 1300, 2200, 1600, 3060]
  ),

  H2("3.3 关键设计决策"),

  H3("3.3.1 多 Agent 架构（Router + 专门 Agent）"),
  P("所有用户请求统一从聊天入口进入，由 Router Agent 识别意图后分发到对应的专门 Agent："),
  code([
    "用户输入",
    "  ↓",
    "Router Agent (Omni 意图识别)",
    "  ↓",
    "  ├─ BaseQA Agent       ← 基础 RAG 问答（纯 Pipeline）",
    "  ├─ ComparisonAgent    ← 客户对比报告（工作流 Agent，形态1）",
    "  ├─ ServicePathAgent   ← 服务路径图（工作流 Agent，形态1）",
    "  └─ FreeQAAgent        ← 自由问答（工具调用 Agent，形态2）",
  ].join("\n")),
  P("Router 同时承担「会话状态管理」职责，跨 Agent 切换时保持上下文（如当前客户、上次意图）。"),

  H3("3.3.2 结构化双轨入库（关键设计）"),
  P("700 份文档不能统一塞向量库，必须按数据特征分轨："),
  makeTable(
    ["文档类型", "处理路径", "查询方式", "示例"],
    [
      ["结构化表（一行一记录）", "解析后导入 PostgreSQL", "Agent SQL 查询", "客户清单、维保记录表、续费跟踪表"],
      ["半结构化报告", "Omni 抽取关键事实 + 向量化", "Agent 双路检索（SQL+向量）", "项目复盘、调研报告"],
      ["纯文本文档", "切片 → 向量化", "向量检索", "FAQ、操作手册、培训资料"],
      ["PPT", "每页转图 → Omni 描述 → 向量化", "向量检索", "产品介绍、方案演示"],
      ["复杂 Excel 报表", "截图 → Omni 描述 → 向量化", "向量检索", "带合并单元格的财务报表"],
    ],
    [1700, 2500, 2500, 2660]
  ),

  H3("3.3.3 客户级权限（升级版）"),
  P("不再使用「按部门隔离」的粗粒度权限，改为「客户 + 文档类型」双维度："),
  code([
    "user_customer_acl  -- 用户能访问哪些客户",
    "  sales_001 → [CUST_A, CUST_B]",
    "  service_001 → [CUST_A, CUST_C, CUST_D]",
    "  manager_001 → ALL",
    "",
    "document_type_acl  -- 不同文档类型谁能看",
    "  合同/金额类: [客户负责人, 财务, 高管]",
    "  实施记录:    [客户负责人, 售后团队]",
    "  一般文档:    [全员]",
  ].join("\n")),
  P("Qdrant 检索时先按 customer_id IN (用户可见列表) 过滤，再做向量相似度，性能与安全双提升。"),

  H3("3.3.4 关键字段精确查询（销售场景幻觉控制）"),
  callout("销售带 AI 生成的报告去客户现场，数据错一个就可能丢单。关键字段必须走数据库精确查询，不能让 LLM 自由生成。", "FFE0E0"),
  P("分类处理："),
  BULLET("【精确字段，走 PostgreSQL】客户名、产品名、合同金额、签约日期、续费状态、负责人"),
  BULLET("【模糊字段，走 RAG + LLM】使用情况描述、客户反馈、问题总结、建议话术"),

  H3("3.3.5 知识缺口反馈机制"),
  P("检索置信度低于阈值时，触发缺口流程，让系统越用越准："),
  NUM("给用户：诚实回复「暂未收录此问题，已记录」"),
  NUM("给系统：日志（query, timestamp, user, customer_context）"),
  NUM("给运营：每周汇总 Top 缺口问题"),
  NUM("给业务：定向补充文档，回填知识库"),

  H2("3.4 七条迁移友好铁律（开发规范）"),
  callout("以下规范从第 1 周开始强制执行，是「未来切换全本地 LLM 仅需改环境变量」的根本保证。违反任一条都会导致迁移成本翻倍。", "E0F0FF"),
  NUM("所有模型调用走 LlamaIndex 统一抽象，禁止 import dashscope 直接调用"),
  NUM("模型相关配置全部走环境变量（LLM_BASE_URL / MODEL_NAME / EMBED_BASE_URL 等）"),
  NUM("优先使用 OpenAI-Compatible API 协议（百炼与 Ollama 均支持，零代码切换）"),
  NUM("Embedding 强制选 bge-m3（本地 + 云端均可，迁移时不重算向量）"),
  NUM("Prompt 模板抽取到独立 prompts/ 目录，按模型分版本"),
  NUM("关键参数（chunk_size / top_k / temperature / rerank_n）走 config.yaml"),
  NUM("测试期每周用本地 Ollama 跑一次小模型验证，确保迁移路径通畅"),
  BR(),
];
