// 数据治理 SOP - Part 2: 元数据 Schema + 客户主数据
const { H1, H2, H3, P, BR, BULLET, NUM, makeTable, callout, code } = require('./common');

module.exports.part2 = () => [
  H1("3. 元数据 Schema"),

  H2("3.1 文档元数据表 (document_meta)"),
  makeTable(
    ["字段", "类型", "必填", "说明"],
    [
      ["doc_id", "UUID", "是", "系统生成"],
      ["filename", "VARCHAR(255)", "是", "原始文件名"],
      ["storage_path", "VARCHAR(500)", "是", "MinIO/本地路径"],
      ["customer_id", "VARCHAR(50)", "是", "关联客户主数据"],
      ["customer_name_at_doc", "VARCHAR(200)", "是", "文档中出现的客户名（可能是别名）"],
      ["product_ids", "JSON 数组", "否", "涉及的产品 ID 列表"],
      ["doc_type", "ENUM", "是", "见 2.3 类型枚举"],
      ["event_date", "DATE", "是", "业务发生日期"],
      ["event_type", "ENUM", "是", "售前/签约/实施/培训/维保/故障/升级/续约/复盘"],
      ["department", "ENUM", "是", "sales/delivery/service/product"],
      ["sensitivity", "ENUM", "是", "public/internal/confidential"],
      ["tags", "JSON 数组", "否", "自定义标签（如「重大故障」）"],
      ["version", "VARCHAR(20)", "否", "v1、v2"],
      ["is_active", "BOOLEAN", "是", "是否生效（false=已过期）"],
      ["created_by", "VARCHAR(50)", "是", "上传人"],
      ["reviewed_by", "VARCHAR(50)", "否", "审核人"],
      ["reviewed_at", "TIMESTAMP", "否", "审核时间"],
    ],
    [2200, 1700, 800, 4660]
  ),

  H2("3.2 必填字段说明"),
  callout("以下字段缺一不可，否则文档不得入库。Omni 自动抽取后由业务方人工确认。", "FFF4CE"),
  BULLET("customer_id：决定权限与档案归属"),
  BULLET("doc_type：决定是否走结构化路径"),
  BULLET("event_date：决定时间轴/路径图位置"),
  BULLET("event_type：决定服务路径中的节点类型"),
  BULLET("sensitivity：决定哪些角色能看（如合同金额仅高管+财务）"),

  H1("4. 客户主数据管理"),

  H2("4.1 客户主表 (customer)"),
  makeTable(
    ["字段", "类型", "必填", "说明"],
    [
      ["customer_id", "VARCHAR(50)", "是", "主键，如 CUST_001"],
      ["short_name", "VARCHAR(50)", "是", "简称（用于文件命名）"],
      ["full_name", "VARCHAR(200)", "是", "工商注册全称"],
      ["industry", "VARCHAR(100)", "否", "行业"],
      ["level", "ENUM", "否", "S/A/B/C 客户级别"],
      ["sales_owner", "VARCHAR(50)", "是", "客户负责人（销售）"],
      ["service_owner", "VARCHAR(50)", "否", "售后负责人"],
      ["status", "ENUM", "是", "active/inactive/lost"],
      ["created_at", "TIMESTAMP", "是", ""],
    ],
    [2200, 1700, 800, 4660]
  ),

  H2("4.2 客户别名表 (customer_alias)"),
  P("解决「同一客户多种叫法」的问题："),
  code([
    "customer_id | alias",
    "------------+------------------",
    "CUST_001    | ABC科技",
    "CUST_001    | ABC公司",
    "CUST_001    | ABC Co.",
    "CUST_001    | abc科技有限",
    "CUST_001    | 阿里巴巴ABC事业部",
  ].join("\n")),

  H2("4.3 客户产品关联 (customer_product)"),
  makeTable(
    ["字段", "类型", "说明"],
    [
      ["customer_id", "VARCHAR(50)", "客户 ID"],
      ["product_id", "VARCHAR(50)", "产品 ID"],
      ["purchase_date", "DATE", "购买日期"],
      ["scale", "INT", "用户/规模数"],
      ["status", "ENUM", "active/expired/upgrading"],
      ["contract_amount", "DECIMAL", "合同金额"],
    ],
    [2500, 2000, 4860]
  ),

  H2("4.4 客户主数据维护流程"),
  NUM("初始来源：从 CRM 系统导入（如有），否则销售总监维护 Excel 模板"),
  NUM("每周同步：Excel → PostgreSQL（脚本化）"),
  NUM("新增客户：销售提交申请，销售总监审核后录入"),
  NUM("别名补充：入库时发现新别名 → 提示运营人员确认 → 追加到别名表"),
  NUM("客户合并：业务变动（如收购）时，将多个 customer_id 合并到主 ID，旧 ID 进归档表"),
  BR(),
];
