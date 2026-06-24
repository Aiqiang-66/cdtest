#!/usr/bin/env python3
import argparse
import csv
import html
import re
import zipfile
from pathlib import Path


def xml_escape(value):
    return html.escape(str(value or ""), quote=True)


def safe_name(value):
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value.strip() or "app_test")
    value = re.sub(r"\s+", "_", value)
    return value[:80] or "app_test"


def docx_paragraph(text):
    text = xml_escape(text)
    return (
        "<w:p><w:r><w:t xml:space=\"preserve\">"
        + text
        + "</w:t></w:r></w:p>"
    )


def docx_heading(text, level):
    """Generate heading paragraph with proper font size and bold."""
    text = xml_escape(text.lstrip("# "))
    font_sizes = {1: 32, 2: 28, 3: 24, 4: 22, 5: 20, 6: 18}
    sz = font_sizes.get(level, 22)
    return (
        f'<w:p>'
        f'<w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr>'
        f'<w:r><w:rPr><w:b/><w:sz w:val="{sz}"/></w:rPr>'
        f'<w:t xml:space="preserve">{text}</w:t></w:r>'
        f'</w:p>'
    )


def docx_bold_paragraph(text):
    """Generate paragraph with bold text (for standalone bold lines)."""
    text = xml_escape(text)
    return (
        '<w:p><w:r><w:rPr><w:b/></w:rPr>'
        f'<w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
    )


def parse_markdown_line(line):
    """Parse a markdown line and return (type, text, extra).
    type: 'heading', 'bold', 'table_row', 'normal'
    """
    stripped = line.strip()
    if not stripped:
        return ('empty', '', None)

    # Heading detection
    heading_match = re.match(r'^(#{1,6})\s+(.*)', stripped)
    if heading_match:
        level = len(heading_match.group(1))
        return ('heading', heading_match.group(2), level)

    # Bold text detection (whole line is bold with **)
    if stripped.startswith('**') and stripped.count('**') >= 2:
        inner = re.sub(r'^\*\*|\*\*$', '', stripped)
        return ('bold', inner, None)

    # Table row detection
    if stripped.startswith('|') and stripped.endswith('|'):
        cells = [c.strip() for c in stripped.strip('|').split('|')]
        return ('table', '|'.join(cells), cells)

    return ('normal', stripped, None)


def write_docx(markdown_path, docx_path):
    lines = Path(markdown_path).read_text(encoding="utf-8").splitlines()
    body = []
    for line in lines:
        typ, text, extra = parse_markdown_line(line)
        if typ == 'empty':
            body.append('<w:p><w:r><w:t xml:space="preserve"> </w:t></w:r></w:p>')
        elif typ == 'heading':
            body.append(docx_heading(text, extra))
        elif typ == 'bold':
            body.append(docx_bold_paragraph(text))
        elif typ == 'table':
            # Render table row with tab-separated content
            body.append(docx_paragraph(' | '.join(extra)))
        else:
            body.append(docx_paragraph(text))
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(body)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        "</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    docx_path = Path(docx_path)
    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def cell_ref(row_idx, col_idx):
    letters = ""
    col = col_idx
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row_idx}"


def write_xlsx(csv_path, xlsx_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            rows.append(row)
    max_cols = max((len(r) for r in rows), default=1)
    sheet_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx in range(1, max_cols + 1):
            value = row[c_idx - 1] if c_idx <= len(row) else ""
            ref = cell_ref(r_idx, c_idx)
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{xml_escape(value)}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{r_idx}">' + "".join(cells) + "</row>")
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="测试用例" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    xlsx_path = Path(xlsx_path)
    with zipfile.ZipFile(xlsx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-md", required=True)
    parser.add_argument("--cases-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--prefix", default="app_test")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = safe_name(args.prefix)
    docx_path = out_dir / f"{prefix}_测试方案.docx"
    xlsx_path = out_dir / f"{prefix}_测试用例.xlsx"

    write_docx(args.plan_md, docx_path)
    write_xlsx(args.cases_csv, xlsx_path)

    print(f"TEST_PLAN_DOCX={docx_path}")
    print(f"TEST_CASE_XLSX={xlsx_path}")


if __name__ == "__main__":
    main()
