// 共用样式与工具函数
const {
  Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel,
  AlignmentType, BorderStyle, WidthType, ShadingType, PageBreak,
  LevelFormat, PageNumber, Header, Footer,
} = require('docx');

const FONT_HEAD = "Microsoft YaHei";
const FONT_BODY = "Microsoft YaHei";

const defaultStyles = {
  default: { document: { run: { font: FONT_BODY, size: 22 } } },
  paragraphStyles: [
    { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 48, bold: true, font: FONT_HEAD, color: "1F3864" },
      paragraph: { spacing: { before: 240, after: 240 }, alignment: AlignmentType.CENTER } },
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 32, bold: true, font: FONT_HEAD, color: "1F3864" },
      paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 26, bold: true, font: FONT_HEAD, color: "2E75B6" },
      paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 23, bold: true, font: FONT_HEAD, color: "404040" },
      paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 2 } },
  ],
};

const sectionPage = {
  page: {
    size: { width: 12240, height: 15840 },
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
  },
};

const numberingConfig = {
  config: [
    { reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "numbers",
      levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
  ],
};

// 工具函数
const P = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, ...opts })],
  spacing: { after: 100 },
});
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] });
const TITLE = (text) => new Paragraph({ style: "Title", children: [new TextRun(text)] });
const SUB = (text) => new Paragraph({
  children: [new TextRun({ text, italics: true, color: "808080", size: 22 })],
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
});
const BR = () => new Paragraph({ children: [new PageBreak()] });
const BULLET = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: [new TextRun(text)],
});
const NUM = (text) => new Paragraph({
  numbering: { reference: "numbers", level: 0 },
  children: [new TextRun(text)],
});

// 表格
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

const cell = (text, opts = {}) => {
  const { width, bold, fill, bg, color } = opts;
  return new TableCell({
    borders,
    width: { size: width || 2000, type: WidthType.DXA },
    shading: bg ? { fill: bg, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text: String(text), bold: !!bold, color, size: 20 })],
    })],
  });
};

const makeTable = (headers, rows, columnWidths) => {
  const totalWidth = columnWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, { width: columnWidths[i], bold: true, bg: "D5E8F0" })),
      }),
      ...rows.map(row => new TableRow({
        children: row.map((c, i) => cell(c, { width: columnWidths[i] })),
      })),
    ],
  });
};

// 强调框（用一行 1 列的表格模拟）
const callout = (text, bg = "FFF4CE") => {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [new TableRow({ children: [new TableCell({
      borders,
      width: { size: 9360, type: WidthType.DXA },
      shading: { fill: bg, type: ShadingType.CLEAR },
      margins: { top: 120, bottom: 120, left: 160, right: 160 },
      children: [new Paragraph({ children: [new TextRun({ text, bold: true, size: 22 })] })],
    })] })],
  });
};

// 代码块
const code = (text) => new Paragraph({
  children: [new TextRun({ text, font: "Consolas", size: 18 })],
  shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
  spacing: { before: 60, after: 60 },
});

module.exports = {
  defaultStyles, sectionPage, numberingConfig,
  P, H1, H2, H3, TITLE, SUB, BR, BULLET, NUM,
  makeTable, callout, code,
};
