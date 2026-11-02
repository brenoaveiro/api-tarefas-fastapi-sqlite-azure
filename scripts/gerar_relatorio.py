#!/usr/bin/env python3
"""
Converte docs/RELATORIO_TECNICO.md em docs/relatorio-final.docx.

Formatacao: papel A4, fonte Arial, corpo tamanho 11, todo o texto em preto,
paragrafos justificados, capa simples em preto e branco, sem cabecalho,
sem rodape e sem numeracao de paginas. Insere as imagens referenciadas no
Markdown (![legenda](caminho)) com a legenda abaixo de cada figura.

Uso:   python scripts/gerar_relatorio.py
Requer: python-docx e pillow (requirements-dev.txt).

Cobre o subconjunto de Markdown usado no relatorio: titulos ##/###, paragrafos,
listas com "-", tabelas "|...|", imagens e **negrito**/*italico*/`codigo`.
"""

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
MD_PATH = BASE / "docs" / "RELATORIO_TECNICO.md"
DOCX_PATH = BASE / "docs" / "relatorio-final.docx"
FONTE = "Arial"
PRETO = RGBColor(0, 0, 0)

CAPA = {
    "prova": "GLOBAL SOLUTION",
    "disciplina": "Disciplina: Cloud",
    "trabalho": "Trabalho: API",
    "titulo": "CyberIncident API",
    "subtitulo": "Plataforma de Gerenciamento de Incidentes de Segurança Cibernética",
    "aluno": "Aluno: Breno Aveiro",
    "data": "Data: 02/11/2026",
}


def _fonte(run_or_style, tamanho=None, negrito=None, italico=None):
    f = run_or_style.font
    f.name = FONTE
    f.color.rgb = PRETO
    if tamanho:
        f.size = Pt(tamanho)
    if negrito is not None:
        f.bold = negrito
    if italico is not None:
        f.italic = italico
    el = run_or_style.element if hasattr(run_or_style, "element") else run_or_style._element
    rpr = el.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for atr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(atr), FONTE)
    for atr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rfonts.attrib.pop(qn(atr), None)


def _configurar(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)          # A4
    sec.top_margin, sec.bottom_margin = Cm(3), Cm(2)
    sec.left_margin, sec.right_margin = Cm(3), Cm(2)
    sec.different_first_page_header_footer = False                 # sem cabecalho/rodape
    normal = doc.styles["Normal"]
    _fonte(normal, 11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for nome, tam in (("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 11)):
        st = doc.styles[nome]
        _fonte(st, tam, negrito=True)
        st.paragraph_format.space_before = Pt(14 if nome == "Heading 1" else 10)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.keep_with_next = True
    _fonte(doc.styles["List Bullet"], 11)


TOKEN = re.compile(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)")


def _inline(par, texto, tamanho=11, negrito_base=False):
    for parte in TOKEN.split(texto):
        if not parte:
            continue
        neg, ita = negrito_base, False
        if parte.startswith("**") and parte.endswith("**"):
            parte, neg = parte[2:-2], True
        elif parte.startswith("`") and parte.endswith("`"):
            parte = parte[1:-1]
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            parte, ita = parte[1:-1], True
        run = par.add_run(parte)
        _fonte(run, tamanho, neg, ita)


def _par(doc, texto="", alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, tamanho=11, negrito=False, espaco_depois=None):
    p = doc.add_paragraph()
    p.alignment = alinhamento
    if texto:
        _inline(p, texto, tamanho, negrito)
    if espaco_depois is not None:
        p.paragraph_format.space_after = Pt(espaco_depois)
    return p


def _capa(doc):
    c = WD_ALIGN_PARAGRAPH.CENTER
    for _ in range(3):
        _par(doc, "", c)
    _par(doc, CAPA["prova"], c, 16, True)
    _par(doc, CAPA["disciplina"], c, 13)
    _par(doc, CAPA["trabalho"], c, 13)
    for _ in range(5):
        _par(doc, "", c)
    _par(doc, CAPA["titulo"], c, 26, True)
    _par(doc, CAPA["subtitulo"], c, 14)
    for _ in range(7):
        _par(doc, "", c)
    _par(doc, CAPA["aluno"], c, 12)
    _par(doc, CAPA["data"], c, 12)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _sumario(doc, linhas):
    doc.add_heading("Sumário", level=1)
    for l in linhas:
        if l.startswith("## "):
            _par(doc, l[3:].strip(), WD_ALIGN_PARAGRAPH.LEFT, 11, espaco_depois=2)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _bordas(tabela):
    tbl = tabela._tbl
    props = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "000000")
        b.append(e)
    props.append(b)


def _tabela(doc, linhas):
    celulas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in linhas]
    celulas = [r for r in celulas if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    n = max(len(r) for r in celulas)
    t = doc.add_table(rows=len(celulas), cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _bordas(t)
    for i, r in enumerate(celulas):
        for j in range(n):
            cel = t.cell(i, j)
            cel.text = ""
            p = cel.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(2)
            _inline(p, r[j] if j < len(r) else "", 9.5, negrito_base=(i == 0))
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def _imagem(doc, alt, caminho):
    arq = (MD_PATH.parent / caminho).resolve()
    if not arq.exists():
        raise FileNotFoundError(f"Imagem nao encontrada: {arq}")
    with Image.open(arq) as im:
        w, h = im.size
    largura = 15.5
    altura = largura * h / w
    limite = 20.5 if "diagramas" in caminho else 20.0      # diagramas altos: limite menor
    if altura > limite:                     # imagens muito altas: limita pela altura
        altura = limite
        largura = altura * w / h
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(arq), width=Cm(largura))
    leg = _par(doc, alt, WD_ALIGN_PARAGRAPH.CENTER, 10, espaco_depois=12)
    for r in leg.runs:
        _fonte(r, 10, False, False)


def converter():
    linhas = MD_PATH.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    doc = Document()
    _configurar(doc)
    _capa(doc)
    _sumario(doc, linhas)

    i, buffer = 0, []

    def fechar_paragrafo():
        nonlocal buffer
        if buffer:
            _par(doc, " ".join(buffer))
            buffer = []

    primeiro_h1_visto = False
    while i < len(linhas):
        l = linhas[i]
        if l.startswith("# ") and not primeiro_h1_visto:
            primeiro_h1_visto = True               # titulo ja esta na capa
        elif l.startswith("## "):
            fechar_paragrafo()
            doc.add_heading(l[3:].strip(), level=1)
        elif l.startswith("### "):
            fechar_paragrafo()
            doc.add_heading(l[4:].strip(), level=2)
        elif l.lstrip().startswith("|"):
            fechar_paragrafo()
            bloco = []
            while i < len(linhas) and linhas[i].lstrip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            _tabela(doc, bloco)
            continue
        elif (m := re.fullmatch(r"!\[(.*)\]\((.*)\)", l.strip())):
            fechar_paragrafo()
            _imagem(doc, m.group(1), m.group(2))
        elif l.startswith("- "):
            fechar_paragrafo()
            p = doc.add_paragraph(style="List Bullet")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _inline(p, l[2:].strip())
        elif l.strip() == "":
            fechar_paragrafo()
        else:
            buffer.append(l.strip())
        i += 1
    fechar_paragrafo()

    # nenhum cabecalho/rodape/numeracao: garante que ficam vazios
    for s in doc.sections:
        for parte in (s.header, s.footer, s.first_page_header, s.first_page_footer):
            parte.is_linked_to_previous = True
    doc.save(DOCX_PATH)
    print(f"Relatorio DOCX gerado em: {DOCX_PATH}")


if __name__ == "__main__":
    converter()
