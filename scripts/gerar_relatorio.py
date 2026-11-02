#!/usr/bin/env python3
"""
Converte docs/RELATORIO_TECNICO.md em docs/relatorio-final.docx,
aplicando a formatacao academica exigida: papel A4, fonte Arial 11,
margens consistentes, numeracao de paginas e titulos hierarquicos.

Uso:
    python scripts/gerar_relatorio.py

Dependencia: python-docx (ja incluida em requirements-dev.txt).

Limitacoes conhecidas: este conversor cobre o subconjunto de Markdown
usado em RELATORIO_TECNICO.md (titulos #/##/###, paragrafos, listas com
"-", tabelas "|...|", blocos de codigo com ```` ``` ````, negrito
**texto**). Nao e um conversor Markdown generico.
"""

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "docs" / "RELATORIO_TECNICO.md"
DOCX_PATH = BASE_DIR / "docs" / "relatorio-final.docx"

FONT_NAME = "Arial"
FONT_SIZE = Pt(11)


def _configurar_pagina(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)   # A4
    section.page_height = Cm(29.7)  # A4
    section.top_margin = Cm(3)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2)


def _configurar_estilo_padrao(document: Document) -> None:
    estilo = document.styles["Normal"]
    estilo.font.name = FONT_NAME
    estilo.font.size = FONT_SIZE
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_NAME)


def _adicionar_numero_pagina(document: Document) -> None:
    section = document.sections[0]
    footer = section.footer
    paragrafo = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = paragrafo.add_run()
    run.font.name = FONT_NAME
    run.font.size = Pt(10)

    campo_inicio = OxmlElement("w:fldChar")
    campo_inicio.set(qn("w:fldCharType"), "begin")
    instrucao = OxmlElement("w:instrText")
    instrucao.set(qn("xml:space"), "preserve")
    instrucao.text = "PAGE"
    campo_fim = OxmlElement("w:fldChar")
    campo_fim.set(qn("w:fldCharType"), "end")

    run._r.append(campo_inicio)
    run._r.append(instrucao)
    run._r.append(campo_fim)


def _adicionar_sumario_automatico(document: Document) -> None:
    paragrafo = document.add_paragraph()
    run = paragrafo.add_run()
    run.font.name = FONT_NAME

    campo_inicio = OxmlElement("w:fldChar")
    campo_inicio.set(qn("w:fldCharType"), "begin")
    instrucao = OxmlElement("w:instrText")
    instrucao.set(qn("xml:space"), "preserve")
    instrucao.text = 'TOC \\o "1-3" \\h \\z \\u'
    campo_separador = OxmlElement("w:fldChar")
    campo_separador.set(qn("w:fldCharType"), "separate")
    texto_aviso = OxmlElement("w:t")
    texto_aviso.text = "Sumario — atualize este campo no Word (botao direito > Atualizar campo)."
    campo_fim = OxmlElement("w:fldChar")
    campo_fim.set(qn("w:fldCharType"), "end")

    run._r.append(campo_inicio)
    run._r.append(instrucao)
    run._r.append(campo_separador)
    run._r.append(texto_aviso)
    run._r.append(campo_fim)


def _adicionar_paragrafo_com_negrito(document, texto: str, estilo=None):
    paragrafo = document.add_paragraph(style=estilo)
    partes = re.split(r"(\*\*.*?\*\*)", texto)
    for parte in partes:
        if not parte:
            continue
        negrito = parte.startswith("**") and parte.endswith("**")
        conteudo = parte[2:-2] if negrito else parte
        run = paragrafo.add_run(conteudo)
        run.bold = negrito
        run.font.name = FONT_NAME
        run.font.size = FONT_SIZE
    return paragrafo


def _adicionar_tabela(document, linhas_tabela):
    linhas = [l for l in linhas_tabela if not re.match(r"^\|[\s\-:|]+\|$", l)]
    dados = [
        [c.strip() for c in linha.strip().strip("|").split("|")]
        for linha in linhas
    ]
    if not dados:
        return
    n_colunas = len(dados[0])
    tabela = document.add_table(rows=0, cols=n_colunas)
    tabela.style = "Light Grid Accent 1"
    for i, linha in enumerate(dados):
        celulas = tabela.add_row().cells
        for j, valor in enumerate(linha[:n_colunas]):
            celulas[j].text = valor
            for paragrafo in celulas[j].paragraphs:
                for run in paragrafo.runs:
                    run.font.name = FONT_NAME
                    run.font.size = Pt(10)
                    if i == 0:
                        run.bold = True
    document.add_paragraph()


def converter_markdown_para_docx(markdown_texto: str, document: Document) -> None:
    linhas = markdown_texto.splitlines()
    i = 0
    dentro_bloco_codigo = False
    buffer_codigo = []
    buffer_tabela = []

    while i < len(linhas):
        linha = linhas[i]

        if linha.strip().startswith("```"):
            if dentro_bloco_codigo:
                p = document.add_paragraph("\n".join(buffer_codigo))
                for run in p.runs:
                    run.font.name = "Consolas"
                    run.font.size = Pt(9)
                buffer_codigo = []
                dentro_bloco_codigo = False
            else:
                dentro_bloco_codigo = True
            i += 1
            continue

        if dentro_bloco_codigo:
            buffer_codigo.append(linha)
            i += 1
            continue

        if linha.strip().startswith("|"):
            buffer_tabela.append(linha)
            if i + 1 >= len(linhas) or not linhas[i + 1].strip().startswith("|"):
                _adicionar_tabela(document, buffer_tabela)
                buffer_tabela = []
            i += 1
            continue

        if linha.startswith("# "):
            document.add_heading(linha[2:].strip(), level=1)
        elif linha.startswith("## "):
            document.add_heading(linha[3:].strip(), level=2)
        elif linha.startswith("### "):
            document.add_heading(linha[4:].strip(), level=3)
        elif linha.strip().startswith("- "):
            _adicionar_paragrafo_com_negrito(document, linha.strip()[2:], estilo="List Bullet")
        elif linha.strip() == "---":
            document.add_page_break()
        elif linha.strip() == "":
            pass
        else:
            _adicionar_paragrafo_com_negrito(document, linha)

        i += 1


def main() -> None:
    if not MD_PATH.exists():
        raise SystemExit(f"Arquivo nao encontrado: {MD_PATH}")

    markdown_texto = MD_PATH.read_text(encoding="utf-8")

    document = Document()
    _configurar_pagina(document)
    _configurar_estilo_padrao(document)
    _adicionar_numero_pagina(document)

    titulo = document.add_heading("API de Gerenciamento de Tarefas na Azure", level=0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitulo = document.add_paragraph("Relatorio Tecnico")
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitulo.runs:
        run.font.size = Pt(14)
        run.font.name = FONT_NAME

    document.add_page_break()
    document.add_heading("Sumario", level=1)
    _adicionar_sumario_automatico(document)
    document.add_page_break()

    # Remove o cabecalho de titulo duplicado do markdown (ja inserido acima)
    linhas_md = markdown_texto.splitlines()
    try:
        indice_sumario = next(
            idx for idx, l in enumerate(linhas_md) if l.strip() == "## Sumario"
        )
        indice_fim_sumario = next(
            idx for idx, l in enumerate(linhas_md[indice_sumario:], start=indice_sumario)
            if l.strip() == "---" and idx > indice_sumario
        )
        linhas_md = linhas_md[indice_fim_sumario + 1:]
    except StopIteration:
        pass

    converter_markdown_para_docx("\n".join(linhas_md), document)

    DOCX_PATH.parent.mkdir(parents=True, exist_ok=True)
    document.save(DOCX_PATH)
    print(f"Relatorio DOCX gerado em: {DOCX_PATH}")
    print(
        "Observacao: o campo de sumario (TOC) e inserido como um campo de "
        "atualizacao automatica do Word. Abra o arquivo no Microsoft Word "
        "e pressione F9 (ou botao direito > Atualizar campo) sobre o "
        "sumario para que os titulos e numeros de pagina sejam preenchidos."
    )


if __name__ == "__main__":
    main()
