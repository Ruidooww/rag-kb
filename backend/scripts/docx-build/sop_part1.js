// 数据治理 SOP - Part 1
const { TITLE, SUB, H1, H2, H3, P, BR, BULLET, NUM, makeTable, callout, code } = require('./common');

module.exports.part1 = () => [
  new (require('docx').Paragraph)({ children: [new (require('docx').TextRun)("")], spacing: { before: 2400 } }),
  TITLE("RAG 知识库"),
  TITLE("数据治理 SOP"),
  SUB("Data Governance Standard Operating Procedure"),
  SUB(""),
  SUB("版本 V1.0  |  2026 年 6 月"),
  SUB("配套文档：《RAG 知识库 - 完整任务书 V2.0》"),
  BR(),

  H1("0. 文档目的"),
  callout("本文档定义 RAG 知识库的数据治理规范。所有文档入库前必须遵守本 SOP，否则不得进入向量库或客户档案系统。", "FFF4CE"),
  P("数据治理是整个 RAG 项目的命门——元数据准确性直接决定所有 Agent 输出质量。本 SOP 由项目组、销售/售后、IT 共同遵守。"),

  H1("1. 治理范围"),
  BULLET("700 份历史文档（Word + Excel + PPT）的元数据回填"),
  BULLET("未来新增文档的入库规范"),
  BULLET("客户主数据的录入与维护"),
  BULLET("客户别名的识别与绑定"),
  BULLET("文档生命周期（生效、过期、归档）"),
  BR(),

  H1("2. 文件命名规范（强制）"),
  callout("文件命名是元数据的「第一道防线」。命名不规范的文档一律退回，不得入库。", "FFE0E0"),

  H2("2.1 命名格式"),
  code("[客户简称]_[文档类型]_[YYYYMMDD]_[版本].docx"),

  H2("2.2 字段说明"),
  makeTable(
    ["字段", "规则", "示例"],
    [
      ["客户简称", "客户主数据表中登记的 4-8 字简称", "ABC、华润集团、星巴克中国"],
      ["文档类型", "见下方文档类型枚举", "实施报告、维保记录"],
      ["YYYYMMDD", "业务发生日期（非文件创建日期）", "20240615"],
      ["版本", "v1、v2 等，无版本可省", "v2"],
    ],
    [1500, 4500, 3360]
  ),

  H2("2.3 文档类型枚举"),
  makeTable(
    ["大类", "类型", "标签值"],
    [
      ["售前", "调研报告", "presales_research"],
      ["售前", "方案建议书", "presales_proposal"],
      ["售前", "POC 报告", "presales_poc"],
      ["签约", "合同", "contract"],
      ["签约", "报价单", "quotation"],
      ["签约", "SOW 范围说明", "sow"],
      ["实施", "实施计划", "delivery_plan"],
      ["实施", "实施报告", "delivery_report"],
      ["实施", "上线确认书", "delivery_signoff"],
      ["培训", "培训材料", "training_material"],
      ["培训", "培训记录", "training_record"],
      ["维保", "巡检报告", "maintenance_inspection"],
      ["维保", "故障报告", "maintenance_incident"],
      ["维保", "升级报告", "maintenance_upgrade"],
      ["续约", "续约合同", "renewal"],
      ["复盘", "项目复盘", "review"],
      ["产品", "产品文档", "product_doc"],
      ["产品", "FAQ", "faq"],
    ],
    [1500, 3360, 4500]
  ),

  H2("2.4 命名示例"),
  code([
    "✅ 正确：",
    "  ABC_实施报告_20240615_v2.docx",
    "  华润_合同_20230501.pdf",
    "  星巴克_维保_20250120.xlsx",
    "",
    "❌ 错误：",
    "  ABC公司实施报告（最终版）.docx       ← 无日期、有冗余字",
    "  20240615.docx                          ← 无客户、无类型",
    "  abc-impl-report-final.docx             ← 英文混乱",
  ].join("\n")),
  BR(),
];
