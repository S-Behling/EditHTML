"""Processamento em lote de relatórios Navisworks, com interface própria.

Entrada: pasta com subpastas de relatórios HTML e suas pastas de imagens.
Saída: HTML editável e HTML preenchido por planilha XLSX/XLSM.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from bs4 import BeautifulSoup

from edit_html import CAMPOS_REMOVER, converter
from preencher_descricoes import atualizar_html


BASE = Path(__file__).resolve().parent
ENTRADA_PADRAO = BASE / "relatorios_entrada"
SAIDA_PADRAO = BASE / "relatorios_saida"


def descobrir_imagens(html: Path) -> Path:
    """Identifica uma pasta de imagens correspondente ao HTML."""
    pasta = html.parent
    candidatas = [
        pasta / (html.stem + "_files"),
        pasta / (html.stem + "_arquivos"),
        pasta / "imagens",
        pasta / "images",
    ]
    for candidata in candidatas:
        if candidata.is_dir():
            return candidata

    # Alguns exports possuem o caminho da imagem dentro do próprio HTML.
    soup = BeautifulSoup(html.read_text(encoding="utf-8-sig"), "html.parser")
    subpastas = set()
    for img in soup.find_all("img", src=True):
        src = img["src"].replace("\\", "/")
        if src.startswith(("data:", "http:", "https:")):
            continue
        partes = Path(src).parts
        if len(partes) > 1:
            subpastas.add(partes[0])
    existentes = [pasta / item for item in subpastas if (pasta / item).is_dir()]
    if len(existentes) == 1:
        return existentes[0]
    if len(existentes) > 1:
        raise ValueError("Mais de uma pasta de imagens referenciada; organize um relatório por pasta.")

    # Permite imagens soltas diretamente ao lado do HTML.
    if any(p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} for p in pasta.iterdir() if p.is_file()):
        return pasta
    raise FileNotFoundError(f"Pasta de imagens não encontrada para {html.name}")


def listar_htmls(entrada: Path, saida: Path) -> list[Path]:
    """Não inclui HTMLs gerados anteriormente nem arquivos dentro da pasta de saída."""
    encontrados = []
    for html in sorted(entrada.rglob("*"), key=lambda p: str(p).casefold()):
        if not html.is_file() or html.suffix.lower() not in (".html", ".htm"):
            continue
        if saida == html or saida in html.parents:
            continue
        if html.stem.casefold().endswith(("_editavel", "_preenchido")):
            continue
        encontrados.append(html)
    return encontrados


def processar_lote(entrada: Path, planilha: Path, saida: Path, log=None):
    entrada = entrada.resolve()
    saida = saida.resolve()
    planilha = planilha.resolve()
    if not entrada.is_dir():
        raise NotADirectoryError(f"Pasta de entrada não encontrada: {entrada}")
    if not planilha.is_file() or planilha.suffix.lower() not in (".xlsx", ".xlsm"):
        raise FileNotFoundError("Selecione uma planilha Excel existente (.xlsx ou .xlsm).")
    if entrada == saida:
        raise ValueError("A pasta de saída deve ser diferente da pasta de entrada.")

    arquivos = listar_htmls(entrada, saida)
    if not arquivos:
        raise ValueError("Nenhum HTML original encontrado na pasta de entrada.")
    saida.mkdir(parents=True, exist_ok=True)
    resultados = []

    for numero, html in enumerate(arquivos, 1):
        relativo = html.relative_to(entrada)
        pasta_destino = saida / relativo.parent
        nome_base = html.stem
        editavel = pasta_destino / f"{nome_base}_editavel.html"
        preenchido = pasta_destino / f"{nome_base}_preenchido.html"
        try:
            imagens = descobrir_imagens(html)
            qtd, faltantes = converter(html, imagens, editavel, CAMPOS_REMOVER)
            estatisticas = atualizar_html(editavel, planilha, preenchido)
            situacao = "OK"
            detalhe = (f"{estatisticas['atualizados']} interferências preenchidas; "
                       f"{qtd} imagens incorporadas; {len(faltantes)} imagens ausentes")
        except Exception as exc:
            situacao = "ERRO"
            detalhe = f"{type(exc).__name__}: {exc}"
            # Se a segunda fase falhar, o HTML editável que tiver sido criado continua disponível.
        resultados.append((str(relativo), situacao, detalhe))
        if log:
            log(f"[{numero}/{len(arquivos)}] {situacao} — {relativo}: {detalhe}")

    return resultados


class Interface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EditHTML | Processamento em lote")
        self.geometry("880x570")
        self.minsize(700, 460)
        self.entrada = tk.StringVar(value=str(ENTRADA_PADRAO))
        self.planilha = tk.StringVar()
        self.saida = tk.StringVar(value=str(SAIDA_PADRAO))

        painel = ttk.Frame(self, padding=20)
        painel.pack(fill="both", expand=True)
        ttk.Label(painel, text="Processamento em lote", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(painel, text="Converte todos os relatórios e preenche Description e Responsável pelo par de Element IDs.").pack(anchor="w", pady=(6, 14))
        self.linha(painel, "Pasta dos relatórios", self.entrada, self.escolher_entrada)
        self.linha(painel, "Planilha Excel", self.planilha, self.escolher_planilha)
        self.linha(painel, "Pasta de saída", self.saida, self.escolher_saida)

        ttk.Label(painel, text="Resultado do processamento").pack(anchor="w", pady=(16, 5))
        area = ttk.Frame(painel)
        area.pack(fill="both", expand=True)
        self.log = tk.Text(area, state="disabled", wrap="word", font=("Consolas", 9))
        barra = ttk.Scrollbar(area, command=self.log.yview)
        self.log.configure(yscrollcommand=barra.set)
        self.log.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self.botao = ttk.Button(painel, text="Processar todos os relatórios", command=self.executar)
        self.botao.pack(anchor="e", pady=(12, 0))

    def linha(self, painel, rotulo, variavel, selecionar):
        linha = ttk.Frame(painel)
        linha.pack(fill="x", pady=5)
        ttk.Label(linha, text=rotulo, width=20).pack(side="left")
        ttk.Entry(linha, textvariable=variavel).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(linha, text="Selecionar...", command=selecionar).pack(side="right")

    def escolher_entrada(self):
        valor = filedialog.askdirectory(title="Pasta com relatórios originais", initialdir=str(BASE))
        if valor:
            self.entrada.set(valor)

    def escolher_planilha(self):
        valor = filedialog.askopenfilename(title="Planilha de clashes",
                                           filetypes=[("Excel", "*.xlsx *.xlsm")])
        if valor:
            self.planilha.set(valor)

    def escolher_saida(self):
        valor = filedialog.askdirectory(title="Destino dos HTMLs", initialdir=str(BASE))
        if valor:
            self.saida.set(valor)

    def informar(self, texto):
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def executar(self):
        if not all(v.get().strip() for v in (self.entrada, self.planilha, self.saida)):
            messagebox.showwarning("Campos obrigatórios", "Selecione os três caminhos.")
            return
        self.botao.configure(state="disabled")
        try:
            self.informar("Iniciando processamento...")
            registros = processar_lote(Path(self.entrada.get()), Path(self.planilha.get()),
                                      Path(self.saida.get()), self.informar)
            sucesso = sum(status == "OK" for _, status, _ in registros)
            falhas = len(registros) - sucesso
            self.informar(f"Concluído: {sucesso} relatório(s) processado(s), {falhas} falha(s).")
            messagebox.showinfo("Processamento concluído",
                                f"{sucesso} relatório(s) processado(s).\n{falhas} falha(s).\n"
                                f"Destino: {self.saida.get()}")
        except Exception as erro:
            self.informar(f"Erro: {erro}")
            messagebox.showerror("Erro", str(erro))
        finally:
            self.botao.configure(state="normal")


def main():
    parser = argparse.ArgumentParser(description="Processamento em lote de HTMLs do Navisworks")
    parser.add_argument("--entrada", type=Path, help="Pasta de entrada (padrão: relatorios_entrada)")
    parser.add_argument("--planilha", type=Path, help="Planilha XLSX/XLSM")
    parser.add_argument("--saida", type=Path, help="Pasta de saída (padrão: relatorios_saida)")
    args = parser.parse_args()
    if args.planilha:
        resultados = processar_lote(args.entrada or ENTRADA_PADRAO, args.planilha,
                                  args.saida or SAIDA_PADRAO, print)
        if any(status == "ERRO" for _, status, _ in resultados):
            raise SystemExit(1)
    else:
        app = Interface()
        if args.entrada:
            app.entrada.set(str(args.entrada))
        if args.saida:
            app.saida.set(str(args.saida))
        app.mainloop()


if __name__ == "__main__":
    main()
