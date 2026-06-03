// 任务书 V2.0 - Part 4: 费用、风险、验收、环境、迁移
const { H1, H2, H3, P, BR, BULLET, NUM, makeTable, callout, code } = require('./common');

module.exports.part4 = () => [
  H1("5. 费用估算（混合云架构）"),

  H2("5.1 一次性投入"),
  makeTable(
    ["项目", "用量", "费用"],
    [
      ["700 份文档初始入库", "Omni 描述 + Embedding", "¥300-600"],
      ["小型本地服务器（如已有可省）", "8 核 / 32G / 1T SSD", "¥0-8000"],
      ["合计", "", "¥300-8600"],
    ],
    [4000, 3000, 2360]
  ),

  H2("5.2 稳态月度费用（30 人中度使用）"),
  makeTable(
    ["项目", "用量假设", "月费"],
    [
      ["LLM/VLM 调用", "~4600 次问答 + 460 次带图", "¥200-260"],
      ["Rerank 调用", "每次问答 15K token", "¥30-50"],
      ["增量入库", "30-50 份新文档/月", "¥30-50"],
      ["本地基础设施", "Qdrant + PG + Redis + MinIO", "¥0（电费忽略）"],
      ["Embedding（本地 bge-m3）", "CPU 推理", "¥0"],
      ["月度合计", "", "¥260-360"],
    ],
    [3000, 3500, 2860]
  ),

  H2("5.3 三年总成本对比"),
  makeTable(
    ["方案", "首期", "3 年总成本", "数据安全"],
    [
      ["全云端", "¥800", "~¥15,000", "⚠️ 文本片段过云"],
      ["混合云（本方案）⭐", "¥800-8600", "~¥18,000", "✅ 文档不出网"],
      ["全本地", "¥25,000+", "~¥32,000+ 含运维", "✅ 全部本地"],
    ],
    [2500, 2000, 2500, 2360]
  ),
  P("混合云只比全云端贵 ¥3000/3 年，换来「文档原文与客户数据 100% 本地」的核心安全收益。"),

  H1("6. 风险与应对"),
  makeTable(
    ["风险", "等级", "应对"],
    [
      ["元数据质量不达标", "🔴 高", "Week 2 强制 SOP + 业务方逐份审核 + Omni 自动抽取辅助"],
      ["客户别名导致档案错乱", "🔴 高", "建立 customer_alias 表，入库前模糊匹配人工确认"],
      ["销售报告幻觉导致丢单", "🔴 高", "关键字段（金额/日期/产品）走 PG 精确查询，禁止 LLM 生成"],
      ["权限设计粒度不够", "🟡 中", "Phase 2 上线客户级 ACL，覆盖销售跨客户隔离"],
      ["Excel 数据塞 RAG 不准", "🟡 中", "Week 2 强制双轨入库，结构化表入 PG"],
      ["API 用量超预算", "🟢 低", "设置用量告警，定期审计；30 人量级新用户额度充足"],
      ["云端 API 故障", "🟢 低", "本地降级返回检索结果（无 LLM 生成）；后续可加备份模型"],
      ["移动端现场网络差", "🟢 低", "Phase 5 加离线缓存 + 流式输出"],
      ["未来需全本地化", "🟢 低", "七条迁移铁律已保障：改 .env 即可"],
    ],
    [3500, 900, 4960]
  ),

  H1("7. 验收标准（分期）"),

  H2("7.1 Phase 1 验收"),
  BULLET("700 份文档完成元数据治理，准确率 ≥ 95%（业务方抽检 50 份）"),
  BULLET("基础问答 Hit@5 ≥ 80%（评估集 50 条）"),
  BULLET("问答响应时间 < 5 秒"),
  BULLET("文档入库异步处理，前端实时显示进度"),

  H2("7.2 Phase 2 验收"),
  BULLET("客户主数据覆盖 100% 现有客户"),
  BULLET("客户级权限生效，跨客户访问被拒绝并记录审计日志"),
  BULLET("「按客户查档案」功能可用，召回完整率 ≥ 95%"),

  H2("7.3 Phase 3 验收"),
  BULLET("客户对比报告生成时间 < 10 秒"),
  BULLET("精确字段（金额/产品/日期）100% 准确"),
  BULLET("销售试用 10 次以上，满意度 ≥ 8/10"),

  H2("7.4 Phase 4 验收"),
  BULLET("服务路径图覆盖客户全生命周期事件，遗漏率 < 5%"),
  BULLET("自由问答 Agent 工具调用成功率 ≥ 90%"),
  BULLET("Router 意图识别准确率 ≥ 95%"),

  H2("7.5 迁移友好验收（贯穿全期）"),
  BULLET("代码 grep 无任何硬编码 API_URL 或 model_name"),
  BULLET("能在 30 分钟内切换到本地 Ollama 演示"),
  BULLET("Prompt 模板按模型分版本，文件化管理"),

  H1("8. 环境准备清单"),

  H2("8.1 账号与权限"),
  BULLET("注册阿里云账号，完成实名认证"),
  BULLET("开通百炼模型服务，获取 API Key"),
  BULLET("开通 qwen3.5-omni-flash、gte-rerank-v2 模型权限"),

  H2("8.2 本地环境"),
  BULLET("一台开发服务器或个人电脑（推荐 16GB+ 内存，无需 GPU）"),
  BULLET("Docker Desktop 或 Docker Engine"),
  BULLET("Python 3.14 + pip"),
  BULLET("Node.js 22 LTS（前端运行时；Next.js 通过 npm install 自动安装到项目内，无需单独全局安装）"),
  BULLET("Ollama（用于每周验证迁移路径）"),

  H2("8.3 第一周启动命令"),
  code([
    "# 1. 克隆项目",
    "git clone <repo-url> && cd rag-kb",
    "",
    "# 2. 复制环境变量，填入百炼 API Key",
    "cp .env.example .env",
    "# 编辑 .env：LLM_BASE_URL、LLM_MODEL、EMBED_BASE_URL 等",
    "",
    "# 3. 启动所有本地服务（Qdrant/PG/Redis/MinIO/bge-m3）",
    "docker compose up -d",
    "",
    "# 4. 安装后端依赖并启动",
    "pip install -r requirements.txt",
    "uvicorn main:app --reload",
    "",
    "# 5. 启动前端",
    "cd web && npm install && npm run dev",
  ].join("\n")),

  H1("9. 未来演进规划"),

  H2("9.1 短期（6-12 个月）"),
  BULLET("Phase 5：移动端 + 语音输入"),
  BULLET("接入钉钉/飞书机器人"),
  BULLET("LLM 用量持续监控，优化 Prompt 节省 token"),

  H2("9.2 中期（12-24 个月）"),
  BULLET("评估开源 Omni 模型成熟度（Qwen-Omni 开源版等）"),
  BULLET("如开源模型质量达到云端 90%+，启动全本地化迁移"),

  H2("9.3 全本地化迁移方案（备用）"),
  P("若未来需切换全本地（合规升级/成本压力）："),
  makeTable(
    ["角色", "云端", "本地替换"],
    [
      ["LLM/VLM", "qwen3.5-omni-flash", "Qwen2.5-VL-7B 或 MiniCPM-V 2.6"],
      ["Rerank", "gte-rerank-v2", "bge-reranker-v2-m3"],
      ["Embedding", "bge-m3（已本地）", "无需变更"],
    ],
    [1800, 3000, 4560]
  ),
  P("迁移工作量：硬件采购 1 周 + 部署测试 1 周 + 效果调优 1-2 周，合计 3-4 周（前提：严格遵守七条铁律）。"),

  H1("10. 配套文档"),
  BULLET("《RAG 知识库 - 数据治理 SOP》（详述元数据规范、入库审核流程）"),
  BULLET("《RAG 知识库 - 系统架构图》（整体架构、Agent 编排、Pipeline 详图）"),

  new (require('docx').Paragraph)({ children: [new (require('docx').TextRun)({ text: "— 文档结束 —", color: "808080" })], alignment: 1, spacing: { before: 400 } }),
];
