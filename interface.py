"""Interface gráfica para converter relatórios HTML do Navisworks."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from edit_html import CAMPOS_REMOVER, converter


class Aplicativo(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EditHTML | Relatórios de Interferências")
        self.geometry("720x360")
        self.minsize(620, 330)
        self.configure(bg="#f3f6fa")
        self.html = tk.StringVar()
        self.imagens = tk.StringVar()
        self.saida = tk.StringVar()
        self.mensagem = tk.StringVar(value="Selecione os arquivos e clique em Gerar relatório.")

        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("TFrame", background="#f3f6fa")
        estilo.configure("TLabel", background="#f3f6fa", foreground="#1f344d", font=("Segoe UI", 10))
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 17, "bold"))
        estilo.configure("TButton", font=("Segoe UI", 10), padding=7)
        estilo.configure("Gerar.TButton", font=("Segoe UI", 11, "bold"), padding=10)

        quadro = ttk.Frame(self, padding=24)
        quadro.pack(fill="both", expand=True)
        ttk.Label(quadro, text="Editar relatório HTML", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(quadro, text="Selecione o relatório original, a pasta de imagens e onde salvar a versão editável.").pack(anchor="w", pady=(3, 20))

        self.linha(quadro, "Arquivo HTML", self.html, self.selecionar_html)
        self.linha(quadro, "Pasta de imagens", self.imagens, self.selecionar_imagens)
        self.linha(quadro, "Salvar HTML em", self.saida, self.selecionar_saida)

        ttk.Label(quadro, textvariable=self.mensagem, wraplength=640).pack(anchor="w", pady=(14, 4))
        self.botao = ttk.Button(quadro, text="Gerar relatório editável", style="Gerar.TButton", command=self.gerar)
        self.botao.pack(anchor="e", pady=(10, 0))

    def linha(self, quadro, titulo, variavel, comando):
        linha = ttk.Frame(quadro)
        linha.pack(fill="x", pady=5)
        ttk.Label(linha, text=titulo, width=17).pack(side="left")
        ttk.Entry(linha, textvariable=variavel).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(linha, text="Selecionar...", command=comando).pack(side="right")

    def selecionar_html(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar HTML original",
            filetypes=[("Arquivos HTML", "*.html *.htm"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            self.html.set(caminho)
            if not self.saida.get():
                p = Path(caminho)
                self.saida.set(str(p.with_name(p.stem + "_editavel.html")))
            if not self.imagens.get():
                p = Path(caminho)
                pasta = p.with_name(p.stem + "_files")
                if pasta.is_dir():
                    self.imagens.set(str(pasta))

    def selecionar_imagens(self):
        caminho = filedialog.askdirectory(title="Selecionar pasta de imagens")
        if caminho:
            self.imagens.set(caminho)

    def selecionar_saida(self):
        sugestao = Path(self.saida.get()) if self.saida.get() else Path(self.html.get() or "relatorio_editavel.html")
        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório editável",
            defaultextension=".html",
            initialdir=str(sugestao.parent),
            initialfile=sugestao.name,
            filetypes=[("Arquivo HTML", "*.html")]
        )
        if caminho:
            self.saida.set(caminho)

    def gerar(self):
        entrada, imagens, saida = [Path(s.strip()) for s in
                                   (self.html.get(), self.imagens.get(), self.saida.get())]
        if not all([self.html.get().strip(), self.imagens.get().strip(), self.saida.get().strip()]):
            messagebox.showwarning("Campos obrigatórios", "Preencha os três caminhos antes de gerar o relatório.")
            return
        if not entrada.is_file():
            messagebox.showerror("Arquivo inválido", "Selecione um arquivo HTML existente.")
            return
        if not imagens.is_dir():
            messagebox.showerror("Pasta inválida", "Selecione uma pasta de imagens existente.")
            return
        if entrada.resolve() == saida.resolve():
            messagebox.showerror("Saída inválida", "Salve em um arquivo diferente do HTML original.")
            return
        self.botao.configure(state="disabled")
        self.mensagem.set("Gerando relatório...")
        self.update_idletasks()
        try:
            qtd, faltando = converter(entrada, imagens, saida, CAMPOS_REMOVER)
            aviso = f"Relatório criado!\nImagens incorporadas: {qtd}."
            if faltando:
                aviso += f"\nAtenção: {len(faltando)} imagem(ns) não encontrada(s)."
            self.mensagem.set(f"Concluído: {saida}")
            messagebox.showinfo("Concluído", aviso + f"\n\nArquivo: {saida}")
        except Exception as erro:
            self.mensagem.set("Erro ao gerar relatório.")
            messagebox.showerror("Erro", str(erro))
        finally:
            self.botao.configure(state="normal")


if __name__ == "__main__":
    Aplicativo().mainloop()
