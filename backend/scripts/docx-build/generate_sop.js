// 生成数据治理 SOP
const fs = require('fs');
const { Document, Packer } = require('docx');
const { defaultStyles, sectionPage, numberingConfig } = require('./common');

const { part1 } = require('./sop_part1');
const { part2 } = require('./sop_part2');
const { part3 } = require('./sop_part3');

const children = [...part1(), ...part2(), ...part3()];

const doc = new Document({
  styles: defaultStyles,
  numbering: numberingConfig,
  sections: [{ properties: sectionPage, children }],
});

Packer.toBuffer(doc).then(buffer => {
  const out = "C:\\Users\\Ruidoww\\Desktop\\RAG\\RAG知识库_数据治理SOP.docx";
  fs.writeFileSync(out, buffer);
  console.log("Generated:", out);
});
