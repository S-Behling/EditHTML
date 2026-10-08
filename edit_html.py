#!/usr/bin/env python3
"""Converte relatórios HTML do Navisworks em relatórios editáveis e autônomos."""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup, Tag

# CONFIGURAÇÃO: altere livremente os nomes dos campos a eliminar.
CAMPOS_REMOVER = ["Distance", "Clash Point", "Grid Location", "Item Type"]
OPCOES_PRIORIDADE = ["Alta", "Média", "Baixa"]


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.strip())
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


def par_nome_valor(node: Tag):
    """Lê um namevaluepair, sem confundir pares internos."""
    nome = node.find("span", class_="name", recursive=False)
    valor = node.find("span", class_="value", recursive=False)
    return nome, valor


def criar_par(soup: BeautifulSoup, nome: str, controle: Tag) -> Tag:
    par = soup.new_tag("span", attrs={"class": "namevaluepair"})
    rotulo = soup.new_tag("span", attrs={"class": "name"})
    rotulo.string = nome
    valor = soup.new_tag("span", attrs={"class": "value"})
    valor.append(controle)
    par.extend([rotulo, valor])
    return par


def criar_input(soup: BeautifulSoup, valor: str = "") -> Tag:
    controle = soup.new_tag("input", attrs={
        "type": "text", "maxlength": "3", "size": "3",
        "class": "editavel curto", "value": valor[:3],
        "aria-label": "Código de até 3 caracteres",
    })
    return controle



def substituir_tolerancia(soup: BeautifulSoup) -> None:
    """Substitui Tolerance por campos editáveis de metadados do relatório."""
    for animation in soup.select("div.animation"):
        # Somente pares imediatamente dentro do cabeçalho de cada relatório,
        # sem alterar os campos particulares das interferências.
        pares = animation.find_all("span", class_="namevaluepair", recursive=False)
        tolerancia = None
        existentes = set()
        for par in pares:
            nome, _ = par_nome_valor(par)
            if nome is None:
                continue
            chave = normalizar(nome.get_text(" ", strip=True))
            if chave in {"data", "arquivo", "versao"}:
                existentes.add(chave)
            if chave in {"tolerance", "tolerancia"}:
                tolerancia = par

        if tolerancia is not None:
            ponto = tolerancia
            for titulo in ("Data", "Arquivo", "Versão"):
                if normalizar(titulo) not in existentes:
                    controle = soup.new_tag("input", attrs={
                        "type": "text", "maxlength": "20", "size": "20",
                        "class": "editavel metadado",
                        "value": "", "aria-label": titulo,
                    })
                    novo = criar_par(soup, titulo, controle)
                    ponto.insert_after(novo)
                    ponto = novo
            tolerancia.decompose()



def transformar_campos(soup: BeautifulSoup, remover: list[str]) -> None:
    removidos = {normalizar(nome) for nome in remover}

    # Cada interferência é tratada isoladamente.
    for viewpoint in soup.select("div.viewpoint"):
        pares = list(viewpoint.select("span.namevaluepair"))
        for par in pares:
            if par.find_parent("div", class_="viewpoint") is not viewpoint:
                continue
            nome, valor = par_nome_valor(par)
            if nome is None or valor is None:
                continue
            chave = normalizar(nome.get_text(" ", strip=True))
            original = valor.get_text(" ", strip=True)

            if chave in removidos:
                par.decompose()
            elif chave == "description":
                valor.clear()
                campo = soup.new_tag("textarea", attrs={
                    "class": "editavel descricao", "rows": "2",
                    "aria-label": "Descrição da interferência",
                })
                campo.string = original
                valor.append(campo)
            elif chave in ("status", "prioridade"):
                nome.string = "Prioridade"
                valor.clear()
                selecao = soup.new_tag("select", attrs={
                    "class": "editavel prioridade",
                    "aria-label": "Prioridade",
                })
                for opcao in OPCOES_PRIORIDADE:
                    item = soup.new_tag("option", value=opcao)
                    item.string = opcao
                    if normalizar(original) == normalizar(opcao):
                        item["selected"] = ""
                    selecao.append(item)
                valor.append(selecao)
            elif chave == "layer":
                nome.string = "Pavimento"

        # Adiciona Responsável imediatamente abaixo do par Name.
        for par in viewpoint.select("span.namevaluepair"):
            nome, _ = par_nome_valor(par)
            if nome and normalizar(nome.get_text(strip=True)) == "name":
                seguinte = par.find_next_sibling("span", class_="namevaluepair")
                seguinte_nome = par_nome_valor(seguinte)[0] if seguinte else None
                if not (seguinte_nome and normalizar(seguinte_nome.get_text(strip=True)) == "responsavel"):
                    par.insert_after(criar_par(soup, "Responsável", criar_input(soup)))
                break

        # Adiciona Disciplina dentro de cada bloco Item 1 e Item 2.
        for titulo in viewpoint.find_all("h4", class_="clashobject"):
            if normalizar(titulo.get_text(" ", strip=True)) not in {"item 1", "item 2"}:
                continue
            proximo_titulo = titulo.find_next_sibling("h4", class_="clashobject")
            bloco = []
            for irmao in titulo.next_siblings:
                if irmao is proximo_titulo:
                    break
                if isinstance(irmao, Tag) and "namevaluepair" in irmao.get("class", []):
                    bloco.append(irmao)
            existente = any(
                (par_nome_valor(par)[0] is not None and
                 normalizar(par_nome_valor(par)[0].get_text(strip=True)) == "disciplina")
                for par in bloco
            )
            if not existente:
                novo = criar_par(soup, "Disciplina", criar_input(soup))
                (bloco[-1] if bloco else titulo).insert_after(novo)


STYLE = """
<style id="edithtml-estilo">
body {font-family:Arial, sans-serif; margin:24px; color:#243247; background:#f4f7fb;}
h1,h2 {color:#172e4b;}
.animation {background:#fff; padding:18px; border-radius:10px; border:1px solid #dce3ec;}
.viewpoint {background:#fff; border:1px solid #b9c8d9; border-radius:8px;
  padding:18px; margin:18px 0; min-height:160px; overflow:auto; break-inside:avoid;}
.viewpoint img {width:210px; height:auto; max-height:210px; object-fit:contain;
  float:left; margin:0 20px 12px 0; border-radius:6px;}
.namevaluepair {display:block; margin:6px 0;}
.namevaluepair > .name {display:inline-block; width:135px; font-weight:600; color:#24517c; vertical-align:top;}
.namevaluepair > .value {display:inline-block; max-width:calc(100% - 150px);}
.editavel {font:inherit; padding:5px 8px; border:1px solid #a8b6c9; border-radius:5px;
  background:white; color:#202d3c; box-sizing:border-box;}
.descricao {width:min(520px, 55vw); min-height:65px; resize:vertical;}
.curto {width:65px; text-transform:uppercase;}
.metadado {width:210px; max-width:100%;}
.prioridade {min-width:110px;}
h4.clashobject {clear:both; margin:16px 0 8px; color:#172e4b;}
.acoes {position:sticky; bottom:0; background:#f4f7fb; padding:16px;
  display:flex; gap:12px; justify-content:center; border-top:1px solid #dce3ec;}
.acoes button {cursor:pointer; border:0; background:#245c91; color:white;
  border-radius:6px; font-size:15px; padding:12px 20px;}
.acoes button:hover {background:#173e66;}
@media print {
  @page {size:A4; margin:12mm;}
  body {background:white; margin:0; color:black; font-size:10pt;}
  .acoes {display:none!important;}
  .animation,.viewpoint {border:0; box-shadow:none; padding:5px; margin:8px 0;}
  .viewpoint {break-inside:avoid; page-break-inside:avoid;}
  .viewpoint img {width:150px; max-height:150px;}
  .editavel {border:0; padding:0; appearance:none; background:transparent;
    color:black; resize:none;}
  .descricao {width:350px; white-space:pre-wrap;}
}
</style>
"""

SCRIPT = r"""
<script id="edithtml-script">
(function() {
  function salvarHTML() {
    // Serializar dados digitados: valores atuais não são automaticamente atributos HTML.
    const copia = document.documentElement.cloneNode(true);
    const atuais = document.querySelectorAll('input.editavel, textarea.editavel, select.editavel');
    const copiados = copia.querySelectorAll('input.editavel, textarea.editavel, select.editavel');
    atuais.forEach((atual, i) => {
      const salvo = copiados[i];
      if (!salvo) return;
      if (atual.tagName === 'TEXTAREA') {
        salvo.textContent = atual.value;
      } else if (atual.tagName === 'SELECT') {
        Array.from(salvo.options).forEach((opt, j) => {
          opt.selected = (j === atual.selectedIndex);
          if (j === atual.selectedIndex) opt.setAttribute('selected', '');
          else opt.removeAttribute('selected');
        });
      } else {
        salvo.setAttribute('value', atual.value);
      }
    });
    const arquivo = '<!DOCTYPE html>\n' + copia.outerHTML;
    const blob = new Blob([arquivo], {type:'text/html;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = (document.title || 'relatorio') .replace(/[\\/:*?"<>|]/g, '_') + '_preenchido.html';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }
  window.salvarHTML = salvarHTML;
  window.salvarPDF = function() { window.print(); };
})();
</script>
"""


def incorporar_imagens(soup: BeautifulSoup, pasta: Path, entrada: Path) -> tuple[int, list[str]]:
    arquivos = {p.name.casefold(): p for p in pasta.rglob("*") if p.is_file()}
    total = 0
    faltando = []
    for img in soup.find_all("img"):
        origem = img.get("src", "")
        if origem.startswith("data:") or origem.startswith(("http:", "https:")):
            continue
        nome = Path(unquote(urlsplit(origem.replace("\\", "/")).path)).name
        candidato = arquivos.get(nome.casefold())
        if candidato is None:
            faltando.append(origem)
            continue
        mime = mimetypes.guess_type(candidato.name)[0] or "application/octet-stream"
        img["src"] = f"data:{mime};base64,{base64.b64encode(candidato.read_bytes()).decode('ascii')}"
        total += 1
    # A versão antiga do Navisworks envolve as imagens em links para caminhos externos.
    for a in soup.find_all("a"):
        if a.find("img") and a.get("href", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            del a["href"]
    return total, faltando


def converter(entrada: Path, pasta: Path, saida: Path, remover: list[str]) -> tuple[int, list[str]]:
    if not entrada.is_file():
        raise FileNotFoundError(f"HTML não encontrado: {entrada}")
    if not pasta.is_dir():
        raise NotADirectoryError(f"Pasta de imagens não encontrada: {pasta}")
    if entrada.resolve() == saida.resolve():
        raise ValueError("A saída deve ser diferente do arquivo HTML original.")

    soup = BeautifulSoup(entrada.read_text(encoding="utf-8-sig"), "html.parser")
    if soup.html is None:
        raise ValueError("Arquivo de entrada não contém uma estrutura HTML válida.")
    if soup.head is None:
        soup.html.insert(0, soup.new_tag("head"))
    if soup.body is None:
        raise ValueError("Arquivo de entrada não contém a tag body.")

    # Remove recursos injetados em execuções anteriores.
    for tag_id in ("edithtml-estilo", "edithtml-script", "edithtml-acoes"):
        existente = soup.find(id=tag_id)
        if existente:
            existente.decompose()

    substituir_tolerancia(soup)
    transformar_campos(soup, remover)
    qtd, faltando = incorporar_imagens(soup, pasta, entrada)

    # Insere os recursos como tags reais (não como texto escapado).
    estilo = BeautifulSoup(STYLE, "html.parser").find("style")
    script = BeautifulSoup(SCRIPT, "html.parser").find("script")
    soup.head.append(estilo)
    if soup.head.find("meta", charset=True) is None:
        soup.head.insert(0, soup.new_tag("meta", charset="utf-8"))
    if soup.title is None:
        titulo = soup.new_tag("title")
        titulo.string = entrada.stem
        soup.head.append(titulo)
    acoes = soup.new_tag("div", attrs={"id": "edithtml-acoes", "class": "acoes"})
    for rotulo, funcao in (("Salvar HTML", "salvarHTML()"), ("Salvar PDF", "salvarPDF()")):
        botao = soup.new_tag("button", attrs={"type": "button", "onclick": funcao})
        botao.string = rotulo
        acoes.append(botao)
    soup.body.append(acoes)
    soup.body.append(script)

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(str(soup), encoding="utf-8")
    return qtd, faltando


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transforma um relatório HTML do Navisworks em HTML editável com imagens incorporadas."
    )
    parser.add_argument("html", type=Path, help="Caminho do HTML original")
    parser.add_argument("imagens", type=Path, help="Caminho da pasta com as imagens")
    parser.add_argument("-o", "--saida", type=Path, help="Arquivo HTML de saída")
    parser.add_argument(
        "--remover", nargs="*", default=None,
        help="Substitui CAMPOS_REMOVER; informe os nomes entre aspas."
    )
    args = parser.parse_args()
    saida = args.saida or args.html.with_name(args.html.stem + "_editavel.html")
    qtd, faltando = converter(args.html, args.imagens, saida,
                             CAMPOS_REMOVER if args.remover is None else args.remover)
    print(f"HTML gerado: {saida.resolve()}")
    print(f"Imagens incorporadas: {qtd}")
    if faltando:
        print("Aviso: imagens não encontradas:", *faltando, sep="\n  ")


if __name__ == "__main__":
    main()
