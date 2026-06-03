// 任务书 V2.0 - Part 3: 实施计划 P1-P5
const { H1, H2, H3, P, BR, BULLET, NUM, makeTable, callout, code } = require('./common');

module.exports.part3 = () => [
  H1("4. 实施计划（分期）"),

  H2("4.1 总览"),
  makeTable(
    ["Phase", "周期", "里程碑", "交付物"],
    [
      ["P1：基础 RAG", "4 周", "Demo 可用 + 元数据治理就绪", "可问答 Demo + 数据治理 SOP 落地"],
      ["P2：客户档案", "3 周", "客户主数据 + 权限上线", "支持「按客户查文档」"],
      ["P3：对比 Agent", "3 周", "销售对比报告上线", "客户对比报告功能 + 前端表格"],
      ["P4：路径 Agent", "3 周", "服务路径图上线", "时间轴报告 + 自由问答 Agent"],
      ["P5：移动端", "可选", "PWA + 语音", "现场销售可用"],
    ],
    [1900, 1400, 2600, 3460]
  ),

  H2("4.2 Phase 1（4 周）：基础 RAG + 数据治理"),

  H3("Week 1：环境搭建 + 迁移友好基础"),
  BULLET("注册阿里云百炼，开通 qwen3.5-omni-flash、gte-rerank-v2 模型"),
  BULLET("编写 docker-compose.yml，启动 Qdrant、PostgreSQL、Redis、MinIO"),
  BULLET("本地部署 bge-m3 Embedding（CPU 即可，无需 GPU）"),
  BULLET("搭建 FastAPI 项目骨架，按「七条铁律」配置环境变量与 config.yaml"),
  BULLET("集成 LlamaIndex，跑通最小 RAG Pipeline（5 份测试文档）"),
  BULLET("交付：Demo 环境 + README + 环境变量切换演示（百炼 ↔ Ollama）"),

  H3("Week 2：数据治理 + 文档分类入库（关键周）"),
  callout("Week 2 是整个项目最关键的一周。元数据准确性决定所有后续 Agent 的输出质量。详见《数据治理 SOP》。", "FFF4CE"),
  BULLET("制定文件命名规范：[客户简称]_[文档类型]_[YYYYMMDD]_[版本].docx"),
  BULLET("定义元数据 Schema：customer_id、event_date、event_type、doc_type 等"),
  BULLET("建立客户主数据表 + 别名表（先用 Excel 维护，后续接 CRM）"),
  BULLET("Omni 自动抽取元数据 → 业务方逐份审核 → 入库"),
  BULLET("结构化双轨入库：结构化表入 PG，非结构化文档入 Qdrant"),
  BULLET("Celery 异步入库，前端显示进度"),
  BULLET("交付：700 份文档完成元数据治理与入库；客户主数据表上线"),

  H3("Week 3：效果调优 + 评估集建设"),
  BULLET("业务方编写 50 条「黄金评估集」（query + 期望文档 + 期望关键信息）"),
  BULLET("跑评估，统计 Hit@5、MRR 指标"),
  BULLET("如 Hit@5 < 85%，A/B 测试是否加 Rerank（gte-rerank-v2）"),
  BULLET("调优 Chunk 大小、Top-K、Prompt 模板"),
  BULLET("开放 5-10 名内部用户试用，收集反馈"),
  BULLET("交付：调优报告 + 评估集 + 反馈记录"),

  H3("Week 4：评估决策 + Phase 2 启动"),
  BULLET("全员 30 人开放测试"),
  BULLET("统计 API 用量与费用，预测稳态成本"),
  BULLET("评估是否进入 Phase 2（客户档案 Agent）"),
  BULLET("启动客户主数据梳理（接 CRM 或继续维护 Excel）"),
  BULLET("交付：Phase 1 总结报告 + Phase 2 启动会"),

  H2("4.3 Phase 2（3 周）：客户档案 + 权限"),
  BULLET("Week 5：客户主数据补全（联系人、产品关联、合同信息）"),
  BULLET("Week 6：客户级权限实施（user_customer_acl + document_type_acl）"),
  BULLET("Week 7：「按客户查档案」功能上线（结构化检索 + 元数据过滤）"),
  BULLET("交付：客户档案查询功能、权限审计日志"),

  H2("4.4 Phase 3（3 周）：客户对比 Agent"),
  BULLET("Week 8：Comparison Agent 工作流设计（实体识别→检索→抽取→对比）"),
  BULLET("Week 9：报告模板系统（产品/规模/续费/满意度等字段固化）"),
  BULLET("Week 10：前端对比表组件 + 销售试用 + 调优"),
  BULLET("交付：客户对比报告功能（1v1，未来支持 1vN）"),

  H2("4.5 Phase 4（3 周）：服务路径 Agent + 自由问答"),
  BULLET("Week 11：ServicePathAgent 工作流（事件抽取 + 时间轴生成）"),
  BULLET("Week 12：前端时间轴组件 + 售后试用"),
  BULLET("Week 13：FreeQA Agent（工具调用形态），统一 Router 上线"),
  BULLET("交付：服务路径图功能、自由问答 Agent、Router 整合"),

  H2("4.6 Phase 5（可选）：移动端 + 语音"),
  BULLET("PWA 改造，客户档案离线缓存"),
  BULLET("Omni 直接处理语音输入"),
  BULLET("隐私模式（客户在场时脱敏显示）"),
  BULLET("交付：销售/售后现场可用"),
  BR(),
];
