# RAG 知识库项目 - 任务清单

> **配套文档**：完整任务书 V2.0、数据治理 SOP、系统架构图
> **总任务数**：53 个（不含已完成的 3 个文档生成任务）
> **总周期**：13 周（Phase 1-4，Phase 5 可选）
> **架构**：混合云（数据本地 + LLM 云端）
> **最后更新**：2026-06-03

---

## 📋 任务总览

| 阶段 | 周次 | 任务数 | 状态 |
|------|------|--------|------|
| ✅ 文档生成（已完成） | - | 3 | 完成 |
| Phase 1：基础 RAG + 数据治理 | W1-W4 | 28 | 待启动 |
| Phase 2：客户档案 + 权限 | W5-W7 | 3 | 待启动 |
| Phase 3：客户对比 Agent | W8-W10 | 3 | 待启动 |
| Phase 4：服务路径 + 自由问答 | W11-W13 | 3 | 待启动 |
| Phase 5（可选）：移动端 | - | 2 | 待启动 |
| 贯穿全期 | - | 2 | 持续 |
| **合计** | **13 周** | **53** | - |

---

## ✅ 已完成（文档产出）

- [x] **#1 生成完整任务书 V2.0** ✅
- [x] **#2 生成数据治理 SOP** ✅
- [x] **#3 生成系统架构图文档** ✅

---

## 🎯 顶层 Phase 里程碑

- [ ] **#4 Phase 1：基础 RAG + 数据治理（4 周）**
  - 完成基础 RAG Demo + 700 份文档元数据治理与入库 + 评估调优 + 全员开放测试
  - 交付：可问答 Demo、SOP 落地、评估集、调优报告

- [ ] **#5 Phase 2：客户档案 + 权限（3 周）** *blocked by #4*
  - 客户主数据补全 + 客户级 ACL 上线 + 按客户查档案功能
  - 交付：客户档案查询功能、权限审计日志

- [ ] **#6 Phase 3：客户对比 Agent（3 周）** *blocked by #5*
  - Comparison Agent 工作流 + 报告模板系统 + 前端对比表组件
  - 交付：销售可用的客户对比报告功能

- [ ] **#7 Phase 4：服务路径 Agent + 自由问答（3 周）** *blocked by #6*
  - ServicePath Agent + 时间轴组件 + FreeQA Agent + Router 整合
  - 交付：服务路径图功能、统一聊天入口

- [ ] **#8 Phase 5（可选）：移动端 PWA + 语音** *blocked by #7*
  - PWA 改造、语音输入、隐私模式、离线缓存
  - 交付：销售/售后现场可用

---

## 🚀 Phase 1：基础 RAG + 数据治理（4 周）

### Week 1：环境搭建 + 迁移友好基础

- [ ] **#9 Week 1 里程碑**
  - 注册百炼、Docker 起服务、bge-m3 本地部署、FastAPI 骨架、最小 RAG Pipeline 跑通、环境变量切换演示

#### Day 1（周一）

- [ ] **#13 阿里云百炼账号 + API Key + 模型开通**（1 小时）
  1. 注册阿里云账号完成实名
  2. 进百炼控制台开通模型服务
  3. 在「模型广场」开通 `qwen3.5-omni-flash` 和 `gte-rerank-v2` 权限
  4. 创建 API Key 并妥善保存
  5. 控制台→费用→开启用量告警（建议阈值 ¥500/月）

- [ ] **#14 本地环境检查 + 工具安装**（2 小时）
  1. 安装 Docker Desktop（验证 `docker --version`）
  2. 安装 Python 3.14（验证 `python --version`）
  3. 安装 Node.js 22 LTS（验证 `node --version`）
  4. 安装 Git
  5. 安装 VSCode/Cursor + Python/Pylance/Docker 插件
  6. 安装 Ollama（用于每周迁移路径验证）

- [ ] **#15 初始化 Git 仓库与项目结构**（1 小时）
  - 创建项目目录 `rag-kb/`，初始化 git 仓库
  - 目录结构：`backend/`、`web/`、`docker/`、`scripts/`、`prompts/`、`docs/`、`config/`、`tests/`
  - 基础文件：`.env.example`、`.gitignore`、`README.md`、`docker-compose.yml`

#### Day 2（周二）

- [ ] **#16 编写 docker-compose.yml 启动本地服务**
  1. Qdrant (`qdrant/qdrant`)
  2. PostgreSQL 16
  3. MinIO（或本地 FS 简化）
  4. bge-m3 Embedding 服务（推荐 `infinity-embedding` 或 `sentence-transformers` 容器）
  5. 验证所有服务 health check 通过
  6. 持久化卷映射到 `./data/`

- [ ] **#17 编写 .env.example 与 config.yaml**（按七条迁移铁律）
  1. `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`
  2. `RERANK_BASE_URL` / `RERANK_MODEL`
  3. `EMBED_BASE_URL` / `EMBED_MODEL`
  4. `POSTGRES_URL` / `QDRANT_URL` / `MINIO_ENDPOINT`
  5. `config.yaml` 放 `chunk_size` / `top_k` / `rerank_n` / `temperature`
  6. 实际 `.env` 添加到 `.gitignore`

#### Day 3（周三）

- [ ] **#18 搭建 FastAPI 项目骨架**
  1. 创建 `backend/` Poetry 或 uv 项目
  2. 安装核心依赖：`fastapi`、`uvicorn`、`llama-index`、`pydantic`、`psycopg`、`qdrant-client`、`httpx`
  3. 项目分层：`app/api/`、`app/agents/`、`app/services/`、`app/models/`、`app/core/`
  4. `main.py` + `/health` endpoint
  5. 配置加载（`pydantic-settings` 读 `.env`）
  6. 启动 `uvicorn main:app --reload` 验证

- [ ] **#19 LlamaIndex 抽象层封装（迁移铁律 #1）** 🔒 关键
  1. 用 LlamaIndex `OpenAILike` 封装 LLM（百炼兼容 OpenAI 接口）
  2. 用 `OpenAIEmbedding` 封装本地 bge-m3
  3. 用 Rerank 封装 `gte-rerank-v2`
  4. **严禁直接 `import dashscope`**
  5. 所有模型参数从 config 读取
  6. 写单元测试验证 LLM/Embedding/Rerank 各自能跑通

#### Day 4（周四）

- [ ] **#20 最小 RAG Pipeline 跑通（5 份测试文档）**
  1. 准备 5 份测试文档（含 1 份带图 PDF）
  2. 写 ingest 脚本：解析 → 切片 → bge-m3 向量化 → 入 Qdrant
  3. 写 query API：query → Embedding → Qdrant Top-30 → Rerank → Omni 生成
  4. `POST /query` 测试接口能返回带引用的答案
  5. 记录端到端延迟

#### Day 5（周五）

- [ ] **#21 环境变量切换演示（迁移铁律验收）** 🔒 验收点
  1. 本地 Ollama 拉取 `qwen2.5:7b` 模型
  2. 复制 `.env` 为 `.env.local`，改 `LLM_BASE_URL` 指向 ollama
  3. **不改任何业务代码**，重启服务
  4. 验证 `/query` 接口仍能返回答案（质量可能下降但流程通）
  5. 记录切换步骤到 `docs/migration-test.md`

- [ ] **#22 Week 1 交付物整理**
  1. `README.md` 写完整：项目概述、目录结构、启动步骤、环境变量说明
  2. `docs/architecture.md` 简述当前架构
  3. 录一个 5 分钟 Demo 视频（上传文档+提问）
  4. Week 1 周报：完成项 + 风险 + 下周计划

---


### Week 2（关键周）：数据治理 + 700 份文档入库

> ⚠️ **本周是整个项目最关键的一周。元数据准确性决定所有后续 Agent 的输出质量。**

- [ ] **#10 Week 2 里程碑** *blocked by #9*
  - 命名规范、元数据 Schema、客户主数据、Omni 自动抽取 + 业务方审核、双轨入库、异步处理

#### Day 1（周一）

- [ ] **#23 制定文件命名规范与文档类型枚举**
  1. 定义 `[客户简称]_[文档类型]_[YYYYMMDD]_[版本]` 格式
  2. 完成 18 类文档类型枚举（售前/签约/实施/培训/维保/续约/复盘/产品）
  3. 写成 `docs/naming-convention.md`
  4. 业务方代表会议确认
  5. 输出文件命名检查脚本 `scripts/check_naming.py`

- [ ] **#24 建立客户主数据表与别名表**
  1. 设计 4 张 PG 表：`customer` / `customer_alias` / `customer_product` / `document_meta`
  2. 写 alembic migration 创建表结构
  3. 从 CRM 或销售总监 Excel 初始化客户主数据
  4. 别名表预填已知别名
  5. 写 `scripts/match_customer.py` 模糊匹配工具

#### Day 2（周二）

- [ ] **#25 Omni 元数据自动抽取脚本**
  1. 编写 `prompts/extract_metadata.txt`（抽取客户名、业务日期、产品、事件类型、文档类型、敏感程度）
  2. `scripts/batch_extract.py`：扫 `./historical_docs` 目录，对每份文档调 Omni 抽取，输出 `metadata.xlsx`
  3. 集成客户别名匹配
  4. 对 PPT/复杂 Excel 走截图+VLM
  5. 测试抽取 10 份样本

- [ ] **#26 跑 700 份文档批量元数据抽取**
  1. 整理 700 份历史文档到统一目录
  2. 跑 `batch_extract.py` 并发 5 抽取（预估 1-2 小时）
  3. 输出 `metadata.xlsx` 含所有字段
  4. 标记 Omni 置信度低的项供重点审核
  5. 记录失败文档清单

#### Day 3-4（周三~周四）

- [ ] **#27 业务方分组审核元数据** 👥 三组并行
  - **销售组**：~200 份合同/方案/客户文档
  - **售后组**：~300 份实施/维保/培训
  - **产品组**：~200 份产品文档/FAQ
  - 审核工具：`metadata.xlsx` 改完上传
  - 审核重点：客户 ID、业务日期、事件类型、敏感程度
  - 预估每人 6-8 小时

- [ ] **#28 结构化双轨入库逻辑实现**
  - 实现 `backend/app/services/ingest.py`：
  1. 文档类型判定（结构化 Excel / 非结构化文档 / 视觉文档）
  2. **结构化路径**：pandas 读 Excel → 写入 PG 业务表（如 `maintenance_records`）
  3. **非结构化路径**：解析 → 切片 → bge-m3 → Qdrant
  4. **视觉路径**：PPT 每页转 PNG → Omni 描述 → 入 Qdrant
  5. 全部带 metadata（`customer_id`、`event_date`、`doc_type` 等）

#### Day 5（周五）

- [ ] **#29 FastAPI BackgroundTasks 异步入库 + 进度查询**
  1. `POST /documents/upload`：保存文件 → 写 PG（`status=uploaded`）→ BackgroundTasks 触发 ingest
  2. ingest worker 更新状态：`uploaded → extracted → pending_review → approved`
  3. `GET /documents/{id}/status` 查询
  4. 前端轮询展示进度
  5. 失败重试机制

- [ ] **#30 700 份文档正式入库 + 抽检**
  1. 用审核通过的 `metadata.xlsx` 跑 `scripts/batch_ingest.py`
  2. 监控入库进度（预估 6 小时单线程，2 小时并发 5）
  3. 入库完成后随机抽 50 份做元数据准确性抽检（目标 ≥95%）
  4. 抽检不通过的批量更正
  5. 输出 Week 2 入库报告

---

### Week 3：效果调优 + 评估集建设

- [ ] **#11 Week 3 里程碑** *blocked by #10*
  - 50 条黄金评估集、Hit@5/MRR 测算、Rerank A/B、Chunk/Top-K/Prompt 调优、5-10 人试用

#### Day 1（周一）

- [ ] **#31 业务方编写 50 条黄金评估集**
  - 销售/售后/产品 各出 ~17 条真实问题
  - 每条包含：`query`、`expected_doc_id`、`expected_answer_contains`
  - 存为 `evaluation/golden_qa.jsonl`

#### Day 2（周二）

- [ ] **#32 评估脚本与基线测试**
  1. `scripts/evaluate.py` 跑评估集，计算 Hit@1/Hit@3/Hit@5、MRR、答案关键词命中率
  2. 跑当前 Pipeline 基线
  3. 输出 `evaluation_report_baseline.md`
  4. 标记失败 case 用于调优

#### Day 3（周三）

- [ ] **#33 Rerank A/B 测试与决策**
  - A 组：无 Rerank，Top-5 直接喂 LLM
  - B 组：Top-30 → `gte-rerank-v2` → Top-5
  - 对比 Hit@5、MRR、延迟、成本
  - 如 B 组提升 ≥5 个点则启用 Rerank
  - 输出对比报告

#### Day 3-4（周三~周四）

- [ ] **#34 Chunk 大小与 Top-K 调优**
  - 网格搜索：`chunk_size ∈ [500, 800, 1200]` × `top_k ∈ [10, 20, 30]` × `rerank_n ∈ [3, 5, 8]`
  - 每种组合跑评估集，选 Hit@5 最优组合
  - ⚠️ chunk 变更需要全量重新切片+向量化
  - 结果写入 `config.yaml`

#### Day 4（周四）

- [ ] **#35 Prompt 模板调优（答案引用与拒答）**
  1. `prompts/base_qa.txt`：要求引用原文+段落+文档名
  2. 加入拒答规则：检索置信度 < 阈值时回复「暂未收录」
  3. 加入幻觉控制：关键数字必须来自检索内容
  4. 跑评估对比改进前后效果
  5. Prompt 按模型分版本（如 `prompts/base_qa.qwen.txt`）

#### Day 5（周五）

- [ ] **#36 5-10 人内部试用 + 反馈收集**
  1. 选 5-10 名跨部门用户（销售 3、售后 3、产品 2）
  2. 提供试用账号 + 5 分钟培训
  3. 试用 3 天
  4. 反馈表收集：问答准确度、响应速度、引用质量、不满意 case
  5. 整理 Bad Case 清单

---

### Week 4：评估决策 + Phase 2 启动

- [ ] **#12 Week 4 里程碑** *blocked by #11*
  - 全员 30 人开放测试、API 用量与费用统计、Phase 2 启动会

#### Day 1（周一）

- [ ] **#37 知识缺口反馈机制实现**
  1. 后端：低置信度查询写入 `knowledge_gaps` 表（query/user/timestamp/customer_ctx）
  2. 前端：答案旁加 👍/👎 按钮，差评写入 `feedback` 表
  3. 管理后台：每周缺口 Top-N 报表
  4. SOP：业务方定期补文档回填

#### Day 2-3（周二~周三）

- [ ] **#38 全员 30 人开放测试**
  1. 创建全员账号
  2. 全员邮件通知 + 15 分钟视频培训
  3. 监控 API 用量与费用
  4. 收集反馈（满意度问卷）
  5. Top 10 高频问题 + Top 10 失败 case

#### Day 4（周四）

- [ ] **#39 API 用量与费用分析 + 稳态预测**
  1. 从百炼控制台拉 4 周用量数据
  2. 按 LLM/Rerank 分类统计
  3. 测算月度稳态成本
  4. 与任务书 §5.2 预估对比
  5. 如超预算分析原因（提示太长？Top-K 太大？）
  6. 输出费用报告

#### Day 5（周五）

- [ ] **#40 Phase 1 总结 + Phase 2 启动**
  1. Phase 1 总结报告：交付项、评估指标、用户满意度、费用、风险
  2. Phase 2 启动会：客户档案功能宣讲、客户主数据梳理任务分配
  3. 决策：是否按时进入 Phase 2 / 是否调整范围

---

## 📦 Phase 2：客户档案 + 权限（3 周）

### Week 5

- [ ] **#41 客户主数据补全（联系人/产品/合同）**
  1. 扩展 `customer` 表加联系人字段（`contact_name` / `phone` / `email` / `role`）
  2. 完善 `customer_product` 关联关系
  3. 新建 `contract` 表（合同号/金额/起止日期/续费状态）
  4. 从 CRM/财务系统或人工录入
  5. 数据质量检查脚本

### Week 6

- [ ] **#42 客户级权限 ACL 实施**
  1. 建 `user_customer_acl` + `document_type_acl` 两张表
  2. 实现权限中间件（依赖注入到所有需要鉴权的 endpoint）
  3. Qdrant 检索时强制注入 `customer_id IN (允许列表)` filter
  4. 跨权限访问审计日志
  5. 管理后台 UI 配置权限

### Week 7

- [ ] **#43 按客户查档案功能**
  1. `GET /customers/{id}/profile`：返回客户基本信息 + 产品 + 合同
  2. `GET /customers/{id}/documents`：按 `customer_id` 过滤的文档列表（分页 + 按类型筛选）
  3. 前端客户档案页 UI
  4. 权限校验贯穿
  5. 集成测试覆盖跨客户访问被拒

---

## 🤖 Phase 3：客户对比 Agent（3 周）

### Week 8

- [ ] **#44 Comparison Agent 工作流设计与实现**
  1. 用 LlamaIndex Workflows 实现 4 步：实体识别 → PG 精确字段查询 → Qdrant 模糊字段检索 → Omni 对比报告生成
  2. 关键字段（金额/产品/续费）强制走 PG，**不走 LLM 生成**
  3. 输出标准化 JSON schema
  4. 单元测试覆盖典型 case

### Week 9

- [ ] **#45 报告模板系统**
  1. 建 `report_template` 表（`template_id` / `name` / `fields_json` / `prompt`）
  2. 预置 3 个模板：客户对比、项目复盘、续约前评估
  3. Agent 按模板填字段
  4. 模板可由运营在管理后台编辑
  5. 版本化管理

### Week 10

- [ ] **#46 前端对比表组件 + 销售试用**
  1. Next.js 对比表组件：自适应列、差异高亮、导出 PDF/Excel
  2. 销售话术 Tips 折叠面板
  3. 选 5 名销售 1 周试用
  4. 收集反馈调优 prompt 和字段
  5. 上线给销售部门

---

## 📈 Phase 4：服务路径 Agent + 自由问答（3 周）

### Week 11

- [ ] **#47 ServicePath Agent 实现**
  1. LlamaIndex Workflow 4 步：客户识别 → 全档案+结构化记录检索 → 事件抽取（并发 Omni）→ 时间轴整合
  2. 事件类型规范化
  3. 关键事件标记规则（重大故障/续约前/上线）
  4. 输出标准化 timeline JSON

### Week 12

- [ ] **#48 前端时间轴组件 + 售后试用**
  1. `react-chrono` 或自研时间轴组件
  2. 关键节点高亮（颜色/图标）
  3. 点击节点跳到原文档
  4. 售后团队 5 人试用
  5. 优化事件聚合逻辑

### Week 13

- [ ] **#49 FreeQA Agent + Router 整合**
  1. FreeQA Agent 用 LlamaIndex Tool-calling 形态，提供 4 个工具：`search_documents`、`query_customer`、`query_product`、`query_contract`
  2. Router Agent：用 Omni 做意图识别分发到 BaseQA / Comparison / ServicePath / FreeQA
  3. 统一聊天入口 UI
  4. 会话上下文管理（当前客户记忆）
  5. 端到端集成测试

---

## 📱 Phase 5（可选）：移动端 PWA + 语音

- [ ] **#50 PWA 改造（Next.js 配置 + Service Worker）**
  1. `next-pwa` 集成
  2. `manifest.json` 配置（图标/启动画面）
  3. 关键页面离线缓存策略
  4. 客户档案本地缓存（IndexedDB）
  5. 安卓/iOS 主屏图标测试

- [ ] **#51 语音输入 + 隐私模式**
  1. 前端 Web Speech API 或 Omni 语音输入
  2. 隐私模式开关：开启后非当前客户名脱敏显示「客户X」
  3. 屏幕闲置 3 分钟自动锁屏
  4. 客户在场友好的极简 UI

---

## 🔁 贯穿全期的循环任务

- [ ] **#52 每周 Ollama 本地迁移验证** 🔒
  - **频率**：每周五下午
  - 1) 切 `.env` 到 Ollama 本地小模型
  - 2) 跑评估集前 10 条
  - 3) 验证 Pipeline 通畅
  - 4) 记录效果差异
  - 5) 修复任何不兼容的硬编码
  - **目的**：确保「七条铁律」始终成立，迁移路径不被破坏

- [ ] **#53 每周数据治理质量抽检**
  - **频率**：每周（Week 3 起）
  - 1) 抽 20 份近期入库文档
  - 2) 元数据准确性核查
  - 3) 别名表新增项确认
  - 4) 失败 case 工单化
  - 5) 月度生成治理报告
  - 累积 Bad Case 用于改进抽取 Prompt

---

## 📊 关键里程碑节点

| 时间 | 节点 | 验收 |
|------|------|------|
| Week 1 末 | Demo 可用 | 5 份文档可问答 + 迁移路径通畅 |
| Week 2 末 | 数据治理完成 | 700 份文档入库，抽检准确率 ≥95% |
| Week 3 末 | 调优完成 | 评估集 Hit@5 ≥ 85% |
| Week 4 末 | Phase 1 完成 | 30 人开放测试 + 费用预测 |
| Week 7 末 | Phase 2 完成 | 客户档案 + 客户级权限上线 |
| Week 10 末 | Phase 3 完成 | 销售可用客户对比报告 |
| Week 13 末 | Phase 4 完成 | 服务路径图 + 统一入口上线 |

---

## ⚠️ 关键风险监控点

| 风险 | 监控时机 | 触发条件 | 应对 |
|------|---------|---------|------|
| 元数据准确率不达标 | Week 2 末抽检 | < 95% | 暂停入库，加大审核投入 |
| 评估准确率不达标 | Week 3 末 | Hit@5 < 75% | 重新审视 Chunk / Prompt / 是否补文档 |
| API 费用超支 | 每周 | 月度预测 > ¥500 | 优化 Prompt、降 Top-K、看是否换更便宜模型 |
| 客户别名错乱 | 任意 | 用户反馈档案串台 | 立即停权限相关 Agent，回查别名表 |
| 销售幻觉投诉 | Phase 3 上线后 | 任意一次错误数据导致客户问题 | 立即下线 Comparison Agent，加强精确字段约束 |
| 七条铁律被破坏 | 每周 Ollama 测试 | 切换 .env 后 Pipeline 跑不通 | 立即定位硬编码，回滚或修复 |

---

## 🛠 工具与术语速查

| 术语 | 含义 |
|------|------|
| **Omni** | qwen3.5-omni-flash，云端多模态 LLM（文本+图片+音频+视频） |
| **bge-m3** | 本地 Embedding 模型，1024 维，迁移友好 |
| **Rerank** | gte-rerank-v2，云端重排模型 |
| **Hit@5** | Top-5 召回准确率 |
| **MRR** | Mean Reciprocal Rank，正确文档排名倒数的均值 |
| **七条铁律** | 任务书 §3.4，迁移友好架构的开发规范 |
| **双轨入库** | 结构化数据入 PG，非结构化数据入 Qdrant |
| **客户级 ACL** | 不是按部门隔离，是按客户隔离权限 |
| **Workflow Agent** | 工作流形态 Agent（步骤固定，可控） |
| **Tool-using Agent** | 工具调用形态 Agent（LLM 自主选工具） |

---

## 📝 使用本清单的方法

1. **每日早会**：用本文档对照昨天完成、今天计划、阻塞
2. **更新方式**：
   - 完成任务：将 `- [ ]` 改为 `- [x]`
   - 同步更新到 Claude Code 的 TaskList（让我帮你 `TaskUpdate #N completed`）
3. **遇到风险**：参考"关键风险监控点"，及时上报
4. **每周复盘**：周五下午查看本周完成项 + 下周计划

---

_文档版本：v1.0  |  生成时间：2026-06-03  |  共 53 个待办任务_

---

## 🕸 Phase 4 扩展：客户关系图（新增 +1.5 周）

> 嵌入 Phase 4，在 Week 13 之后追加。基于已有 PG 数据，无需新数据源。

- [ ] **#54 客户关系图后端 API**
  - `GET /customers/{id}/network` 返回节点+边 JSON
  - **节点类型**：客户、产品、合同、联系人、相关客户
  - **边类型**：has_product / signed_contract / belongs_to / similar_industry
  - 数据来源：已有 `customer` / `customer_product` / `contract` / `user_customer_acl` 表
  - 输出格式遵循 react-flow 标准（`{nodes: [], edges: []}`）

- [ ] **#55 前端关系图组件** *blocked by #54*
  - 集成 React Flow 或 vis-network 库
  - 客户档案页添加"关系图" Tab
  - 功能：节点点击跳转详情、按类型过滤（产品/人员/合同）、自适应布局、导出 PNG
  - 兼容移动端（PWA 模式下可缩放）

- [ ] **#56 NetworkAgent + Router 集成** *blocked by #49, #55*
  - 新增 `NetworkAgent`：识别"相关方/关系/网络/谁连着谁"类问题
  - 直接调用 `/customers/{id}/network` 返回图数据 + Omni 生成简短文字摘要
  - Router 添加 `network` 意图分支
  - 端到端测试：聊天框输入 → 自动渲染关系图

---
