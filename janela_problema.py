"""
Janela "Detalhes do problema": mostra o tamanho de cada limite, o valor e
o peso de cada item, um grafico e permite exportar tudo para o Excel.
"""
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import problemas
from instancias import PASTA_PROJETO


def br(x, casas=0):
    try:
        s = f"{float(x):,.{casas}f}"
    except (TypeError, ValueError):
        return "-"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


class JanelaProblema(tk.Toplevel):
    def __init__(self, pai, item, abrir_pasta):
        super().__init__(pai)
        self.item, self.abrir_pasta = item, abrir_pasta
        self.inst = problemas.carregar(item)
        inst = self.inst
        self.frete = problemas.eh_frete(item)
        self.limites = problemas.nomes_limites(item, inst.m)
        self.nome_item = "Encomenda" if self.frete else "Item"
        self.plural = "Encomendas" if self.frete else "Itens"
        self.nome_valor = "Frete (R$)" if self.frete else "Valor"

        self.title(f"Problema {item['nome']}")
        self.geometry("1100x720")
        self.minsize(900, 600)

        # ---------- cabecalho ----------
        topo = ttk.Frame(self, padding=(12, 10))
        topo.pack(fill="x")
        ttk.Label(topo, text=f"Problema {item['nome']}", font=("Segoe UI", 15, "bold")).pack(side="left")
        ttk.Button(topo, text="Exportar para Excel", command=self._exportar).pack(side="right")
        referencia, tipo = inst.referencia()
        otimo = (f"Melhor resposta possível (ótimo): {br(inst.otimo)}" if inst.otimo else
                 f"Ótimo desconhecido · limite teórico máximo: {br(referencia)}")
        ttk.Label(self, padding=(12, 0), font=("Segoe UI", 10),
                  text=f"{inst.n} {self.plural.lower()} · {inst.m} limite(s) · {otimo}").pack(anchor="w")

        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=10, pady=10)
        self._aba_resumo(abas)
        self._aba_itens(abas)
        self._aba_grafico(abas)

    # ---------------------------------------------------------------
    def _aba_resumo(self, abas):
        inst = self.inst
        aba = ttk.Frame(abas, padding=12)
        abas.add(aba, text="  Resumo e limites  ")

        valores = inst.lucros
        dono = "das encomendas" if self.frete else "dos itens"
        caixa = ttk.LabelFrame(aba, text=f" {self.nome_valor} {dono} ", padding=10)
        caixa.pack(fill="x")
        dados = [("Soma de todos", br(valores.sum())), (f"Média por {self.nome_item.lower()}", br(valores.mean(), 1)),
                 ("Menor", br(valores.min())), ("Maior", br(valores.max()))]
        for col, (rot, val) in enumerate(dados):
            ttk.Label(caixa, text=rot).grid(row=0, column=col, padx=18, sticky="w")
            ttk.Label(caixa, text=val, font=("Segoe UI", 13, "bold")).grid(row=1, column=col, padx=18, sticky="w")

        ttk.Label(aba, text="O tamanho de cada limite", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(14, 2))
        ttk.Label(aba, foreground="#555555", wraplength=1000, justify="left",
                  text="Capacidade = quanto o limite comporta. Total pedido = quanto todos os itens juntos "
                       "ocupariam. Cabe = que fração do total cabe (quanto menor, mais apertado).").pack(anchor="w")
        colunas = ["Limite", "Capacidade", "Total pedido (todos os itens)", "Cabe (%)", "Situação"]
        t = self._tabela(aba, colunas, [160, 140, 220, 100, 260], altura=min(12, inst.m + 1), expandir=False)
        totais = inst.pesos.sum(axis=1)
        for nome, cap, tot in zip(self.limites, inst.capacidades, totais):
            frac = cap / max(1, tot)
            situacao = ("tudo cabe (não restringe)" if frac >= 1 else
                        "muito apertado" if frac < 0.35 else "apertado" if frac < 0.6 else "folgado")
            t.insert("", "end", values=(nome, br(cap), br(tot), br(100 * frac, 1), situacao))

        mais_apertado = int(np.argmin(inst.capacidades / np.maximum(1, totais)))
        vezes = totais[mais_apertado] / max(1, inst.capacidades[mais_apertado])
        ttk.Label(aba, wraplength=1000, justify="left", font=("Segoe UI", 10),
                  text=f"Em palavras: para levar tudo, o limite mais apertado, "
                       f"{self.limites[mais_apertado]}, precisaria ser {br(vezes, 1)} vezes maior. "
                       f"Por isso é preciso escolher quais itens levar.").pack(anchor="w", pady=10)

    # ---------------------------------------------------------------
    def _aba_itens(self, abas):
        inst = self.inst
        aba = ttk.Frame(abas, padding=12)
        abas.add(aba, text=f"  {self.plural} (valor e peso)  ")
        ttk.Label(aba, foreground="#555555", wraplength=1000, justify="left",
                  text="Clique no título de uma coluna para ordenar. 'Espaço ocupado' = quanto o item usa, "
                       "em média, de cada limite. 'Valor por espaço' alto = item que compensa levar.").pack(anchor="w")
        espaco = (inst.pesos / np.maximum(1, inst.capacidades)[:, None]).mean(axis=0) * 100
        self.eficiencia = inst.lucros / np.maximum(espaco, 1e-9)
        colunas = [self.nome_item, self.nome_valor] + self.limites + ["Espaço ocupado (%)", "Valor por espaço"]
        larguras = [105, 105] + [max(95, 10 * len(n) + 20) for n in self.limites] + [175, 150]
        self.tab_itens = self._tabela(aba, colunas, larguras, altura=20, horizontal=True)
        self.linhas = []
        for j in range(inst.n):
            linha = [j + 1, int(inst.lucros[j])] + [int(v) for v in inst.pesos[:, j]] + \
                    [float(espaco[j]), float(self.eficiencia[j])]
            self.linhas.append(linha)
        self._mostrar_itens(self.linhas)
        for indice, coluna in enumerate(colunas):
            self.tab_itens.heading(coluna, command=lambda i=indice: self._ordenar(i))
        self._ordem = {}

    def _mostrar_itens(self, linhas):
        t = self.tab_itens
        t.delete(*t.get_children())
        for l in linhas:
            t.insert("", "end", values=[l[0], br(l[1])] + [br(v) for v in l[2:-2]] +
                     [br(l[-2], 2), br(l[-1], 1)])

    def _ordenar(self, indice):
        anterior = self._ordem.get(indice)
        # 1o clique: numeros do maior para o menor (o nº do item, do menor para o maior)
        decrescente = (indice != 0) if anterior is None else not anterior
        self._ordem[indice] = decrescente
        self._mostrar_itens(sorted(self.linhas, key=lambda l: l[indice], reverse=decrescente))

    # ---------------------------------------------------------------
    def _aba_grafico(self, abas):
        inst = self.inst
        aba = ttk.Frame(abas, padding=12)
        abas.add(aba, text="  Gráfico  ")
        ttk.Label(aba, foreground="#555555", wraplength=1000, justify="left",
                  text="Cada ponto é um item. Se os pontos formam uma 'linha' subindo, o valor acompanha o "
                       "tamanho: itens grandes valem mais, e fica difícil saber quais compensam (problema "
                       "difícil). Pontos espalhados = problema mais fácil.").pack(anchor="w")
        espaco = (inst.pesos / np.maximum(1, inst.capacidades)[:, None]).mean(axis=0) * 100
        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.scatter(espaco, inst.lucros, s=18, alpha=0.7, color="#4F81BD")
        ax.set_xlabel("Espaço ocupado (% médio de cada limite)")
        ax.set_ylabel(self.nome_valor)
        if inst.n > 2 and np.std(espaco) > 0 and np.std(inst.lucros) > 0:
            r = np.corrcoef(espaco, inst.lucros)[0, 1]
            ax.set_title(f"Valor x espaço — correlação = {br(r, 2)} (1 = andam juntos, 0 = sem relação)")
        ax.grid(alpha=0.3)
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 1)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 0)))
        canvas = FigureCanvasTkAgg(fig, master=aba)
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, pady=6)

        def ajustar(_evento=None):
            # encaixa a figura no tamanho real da area (evita cortes)
            largura, altura = widget.winfo_width(), widget.winfo_height()
            if largura > 50 and altura > 50:
                fig.set_size_inches(largura / fig.dpi, altura / fig.dpi, forward=False)
                fig.tight_layout()
                canvas.draw_idle()
        widget.bind("<Configure>", lambda e: self.after(150, ajustar), add="+")
        self.after(300, ajustar)

    # ---------------------------------------------------------------
    def _tabela(self, pai, colunas, larguras, altura=10, horizontal=False, expandir=True):
        quadro = ttk.Frame(pai)
        quadro.pack(fill="both" if expandir else "x", expand=expandir, pady=4)
        t = ttk.Treeview(quadro, columns=colunas, show="headings", height=altura)
        for c, w in zip(colunas, larguras):
            t.heading(c, text=c)
            t.column(c, width=w, minwidth=60, anchor="center", stretch=not horizontal)
        bv = ttk.Scrollbar(quadro, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=bv.set)
        t.grid(row=0, column=0, sticky="nsew")
        bv.grid(row=0, column=1, sticky="ns")
        if horizontal:
            bh = ttk.Scrollbar(quadro, orient="horizontal", command=t.xview)
            t.configure(xscrollcommand=bh.set)
            bh.grid(row=1, column=0, sticky="ew")
        quadro.rowconfigure(0, weight=1)
        quadro.columnconfigure(0, weight=1)
        return t

    def _exportar(self):
        inst = self.inst
        pasta = PASTA_PROJETO / "resultados" / "problemas"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"{self.item['nome']}.xlsx"
        itens = pd.DataFrame(self.linhas, columns=[self.nome_item, self.nome_valor] + self.limites +
                             ["Espaço ocupado (%)", "Valor por espaço"])
        totais = inst.pesos.sum(axis=1)
        limites = pd.DataFrame({"Limite": self.limites, "Capacidade": inst.capacidades,
                                "Total pedido": totais,
                                "Cabe (%)": np.round(100 * inst.capacidades / np.maximum(1, totais), 1)})
        try:
            with pd.ExcelWriter(caminho, engine="openpyxl") as xl:
                limites.to_excel(xl, sheet_name="Limites", index=False)
                itens.round(2).to_excel(xl, sheet_name=self.plural, index=False)
                for aba in xl.sheets.values():
                    for coluna in aba.columns:
                        aba.column_dimensions[coluna[0].column_letter].width = 16
        except PermissionError:
            messagebox.showerror("Arquivo aberto", "Feche o arquivo no Excel e tente de novo.", parent=self)
            return
        if messagebox.askyesno("Excel criado", f"Salvo em:\n{caminho}\n\nAbrir a pasta?", parent=self):
            self.abrir_pasta(pasta)
