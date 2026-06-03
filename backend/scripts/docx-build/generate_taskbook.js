// 生成任务书 V2.0
const fs = require('fs');
const { Document, Packer } = require('docx');
const { defaultStyles, sectionPage, numberingConfig } = require('./common');

const { part1 } = require('./taskbook_part1');
const { part2 } = require('./taskbook_part2');
const { part3 } = require('./taskbook_part3');
const { part4 } = require('./taskbook_part4');

const children = [
  ...part1(),
  ...part2(),
  ...part3(),
  ...part4(),
];

const doc = new Document({
  styles: defaultStyles,
  numbering: numberingConfig,
  sections: [{ properties: sectionPage, children }],
});

Packer.toBuffer(doc).then(buffer => {
  const out = "C:\\Users\\Ruidoww\\Desktop\\RAG\\RAG知识库_完整任务书_V2.0.docx";
  fs.writeFileSync(out, buffer);
  console.log("Generated:", out);
});
