// 生成系统架构图文档
const fs = require('fs');
const { Document, Packer } = require('docx');
const { defaultStyles, sectionPage, numberingConfig } = require('./common');

const { part1 } = require('./arch_part1');
const { part2 } = require('./arch_part2');
const { part3 } = require('./arch_part3');

const children = [...part1(), ...part2(), ...part3()];

const doc = new Document({
  styles: defaultStyles,
  numbering: numberingConfig,
  sections: [{ properties: sectionPage, children }],
});

Packer.toBuffer(doc).then(buffer => {
  const out = "C:\\Users\\Ruidoww\\Desktop\\RAG\\RAG知识库_系统架构图.docx";
  fs.writeFileSync(out, buffer);
  console.log("Generated:", out);
});
