"""Genera GUIA_DE_USO.docx a partir de GUIA_DE_USO.md (requiere: pip install python-docx).

Uso:  python docs/build_docx.py
Soporta el Markdown que usa la guía: títulos, párrafos, viñetas, listas numeradas, tablas, citas y bloques de código.
"""
import os
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "GUIA_DE_USO.md")
DST = os.path.join(HERE, "GUIA_DE_USO.docx")


def shade(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), color)
    tc_pr.append(sh)


def runs(p, text, size=None):
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r.font.color.rgb = RGBColor(0x9A, 0x2A, 0x2A)
        elif part.startswith("*") and len(part) > 2:
            r = p.add_run(part[1:-1])
            r.italic = True
        else:
            r = p.add_run(part)
        if size:
            r.font.size = Pt(size)


def build(src=SRC, dst=DST):
    lines = open(src, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)
    for name, size in (("Heading 1", 20), ("Heading 2", 15), ("Heading 3", 12.5)):
        h = doc.styles[name]
        h.font.name = "Calibri"
        h.font.size = Pt(size)
        h.font.color.rgb = RGBColor(0x0B, 0x5C, 0x4D)

    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            i += 1
            buf = []
            while not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.5)
            r = p.add_run("\n".join(buf))
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
            p_pr = p._p.get_or_add_pPr()
            sh = OxmlElement("w:shd")
            sh.set(qn("w:val"), "clear")
            sh.set(qn("w:fill"), "F0F0F0")
            p_pr.append(sh)
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-|]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            i -= 1
            t = doc.add_table(rows=len(rows), cols=len(rows[0]))
            t.style = "Table Grid"
            for ri, row in enumerate(rows):
                for ci, txt in enumerate(row):
                    c = t.cell(ri, ci)
                    c.text = ""
                    runs(c.paragraphs[0], txt, 10)
                    if ri == 0:
                        shade(c, "DCEFEA")
                        for r in c.paragraphs[0].runs:
                            r.bold = True
            doc.add_paragraph()
        elif ln.startswith("# "):
            doc.add_heading(ln[2:], 1)
        elif ln.startswith("## "):
            doc.add_heading(ln[3:], 2)
        elif ln.startswith("### "):
            doc.add_heading(ln[4:], 3)
        elif ln.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            runs(p, ln[2:])
            for r in p.runs:
                r.italic = True
        elif re.match(r"^\s*- ", ln):
            indent = len(ln) - len(ln.lstrip())
            p = doc.add_paragraph(style="List Bullet" if not indent else "List Bullet 2")
            runs(p, re.sub(r"^\s*- ", "", ln))
        elif re.match(r"^\s*\d+\. ", ln):
            indent = len(ln) - len(ln.lstrip())
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.9 + 0.7 * (indent > 0))
            p.paragraph_format.first_line_indent = Cm(-0.6)
            m = re.match(r"^\s*(\d+)\. (.*)", ln)
            runs(p, m.group(1) + ".  " + m.group(2))
        elif ln.strip():
            runs(doc.add_paragraph(), ln)
        i += 1
    doc.save(dst)
    return dst


if __name__ == "__main__":
    print("Generado:", build())
