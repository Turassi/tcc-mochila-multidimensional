"""
LABORATORIO DA MOCHILA MULTIDIMENSIONAL
Interface grafica para escolher algoritmos, escolher ou gerar problemas,
rodar experimentos e ver os resultados.

Uso: py laboratorio.py   (ou dois cliques em 5_abrir_laboratorio.bat)
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

CORES = ["#C0504D", "#4F81BD", "#9BBB59", "#8064A2", "#F79646", "#4BACC6", "#7F7F7F", "#D4A017"]


def br(x, casas=2):
    try:
        s = f"{float(x):,.{casas}f}"
    except (TypeError, ValueError):
        return "-"
    if s in ("nan", "-nan"):
        return "-"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def abrir_pasta(caminho):
    if sys.platform.startswith("win"):
        os.startfile(caminho)  # noqa
    else:
        subprocess.Popen(["xdg-open", str(caminho)])


class Laboratorio(tk.Tk):
    def __init__(self):
        super().__init__()
        # importacoes pesadas so aqui (os nucleos de calculo nao precisam delas)
        global CATALOGO, problemas, motor, est, Figure, FigureCanvasTkAgg, np, FuncFormatter
        import numpy as np
        from matplotlib.ticker import FuncFormatter
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        import estatistica_lab as est
        import motor_lab as motor
        import problemas
        from algoritmos_extra import CATALOGO

        self.title("Laboratório da Mochila Multidimensional")
        self.geometry("1220x780")
        self.minsize(1050, 680)
        estilo = ttk.Style(self)
        if "vista" not in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 15, "bold"))
        estilo.configure("Dica.TLabel", foreground="#555555")
        estilo.configure("Grande.TButton", font=("Segoe UI", 11, "bold"), padding=8)

        self.fila = queue.Queue()
        self.parar_flag = threading.Event()
        self.rodando = False
        self.cores = {alg: CORES[i % len(CORES)] for i, alg in enumerate(CATALOGO)}

        topo = ttk.Frame(self, padding=(12, 10, 12, 4))
        topo.pack(fill="x")
        ttk.Label(topo, text="Laboratório da Mochila Multidimensional", style="Titulo.TLabel").pack(side="left")
        ttk.Label(topo, style="Dica.TLabel",
                  text="   1) Algoritmos  →  2) Problemas  →  3) Rodar  →  4) Resultados").pack(side="left")

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self._aba_algoritmos()
        self._aba_problemas()
        self._aba_rodar()
        self._aba_resultados()
        self._aba_sobre()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(200, self._ler_fila)
        self._atualizar_resumo()

    # -----------------------------------------------------------------
    # ABA 1 - ALGORITMOS
    # -----------------------------------------------------------------
    def _aba_algoritmos(self):
        aba = ttk.Frame(self.abas, padding=12)
        self.abas.add(aba, text="  1. Algoritmos  ")
        ttk.Label(aba, style="Dica.TLabel",
                  text="Marque os algoritmos que vão competir. Todos usam o mesmo número de "
                       "tentativas, o mesmo reparo e começam das mesmas soluções.").pack(anchor="w")
        botoes = ttk.Frame(aba)
        botoes.pack(anchor="w", pady=8)
        for texto, filtro in [("Marcar todos", lambda c: True), ("Desmarcar todos", lambda c: False),
                              ("Só os do TCC", lambda c: c["tipo"] == "TCC"),
                              ("TCC + clássicos", lambda c: c["tipo"] in ("TCC", "Clássico")),
                              ("TCC + recentes", lambda c: c["tipo"] in ("TCC", "Recente"))]:
            ttk.Button(botoes, text=texto, command=lambda f=filtro: self._marcar_algs(f)).pack(side="left", padx=3)

        quadro = ttk.Frame(aba)
        quadro.pack(fill="both", expand=True)
        self.var_algs = {}
        for coluna, titulo in enumerate(["Usar", "Algoritmo", "Ano", "Tipo", "Como funciona (resumo)"]):
            ttk.Label(quadro, text=titulo, font=("Segoe UI", 10, "bold")).grid(row=0, column=coluna, sticky="w", padx=6, pady=4)
        for linha, (sigla, info) in enumerate(CATALOGO.items(), start=1):
            var = tk.BooleanVar(value=True)
            var.trace_add("write", lambda *_: self._atualizar_resumo())
            self.var_algs[sigla] = var
            ttk.Checkbutton(quadro, variable=var).grid(row=linha, column=0, padx=6)
            tk.Label(quadro, text=f"■ {info['nome']}", fg=self.cores[sigla],
                     font=("Segoe UI", 10, "bold")).grid(row=linha, column=1, sticky="w", padx=6, pady=5)
            ttk.Label(quadro, text=str(info["ano"])).grid(row=linha, column=2, sticky="w", padx=6)
            ttk.Label(quadro, text=f"{info['tipo']} · {info['familia']}").grid(row=linha, column=3, sticky="w", padx=6)
            ttk.Label(quadro, text=info["resumo"], wraplength=430).grid(row=linha, column=4, sticky="w", padx=6)
        quadro.columnconfigure(4, weight=1)

    def _marcar_algs(self, filtro):
        for sigla, var in self.var_algs.items():
            var.set(filtro(CATALOGO[sigla]))

    def algoritmos_escolhidos(self):
        return [s for s, v in self.var_algs.items() if v.get()]

    # -----------------------------------------------------------------
    # ABA 2 - PROBLEMAS
    # -----------------------------------------------------------------
    def _aba_problemas(self):
        aba = ttk.Frame(self.abas, padding=12)
        self.abas.add(aba, text="  2. Problemas  ")
        ttk.Label(aba, style="Dica.TLabel",
                  text="Clique numa linha para marcar ou desmarcar. Dois cliques abrem os detalhes "
                       "(valor e peso de cada item, tamanho dos limites).").pack(anchor="w")
        corpo = ttk.Frame(aba)
        corpo.pack(fill="both", expand=True, pady=6)

        esq = ttk.LabelFrame(corpo, text=" ⭐ Recomendações ", padding=8)
        esq.pack(side="left", fill="y")
        for titulo, nomes in problemas.RECOMENDACOES.items():
            ttk.Button(esq, text=titulo, width=30,
                       command=lambda n=nomes: self._selecionar_problemas(n)).pack(fill="x", pady=2)
        ttk.Separator(esq).pack(fill="x", pady=8)
        ttk.Button(esq, text="Limpar seleção", command=lambda: self._selecionar_problemas([])).pack(fill="x")
        ttk.Label(esq, style="Dica.TLabel", wraplength=200, justify="left",
                  text="\nDica: a Amostra pequena roda em poucos minutos. O Desafio reúne problemas em que "
                       "os algoritmos mais se diferenciam.").pack(anchor="w")

        dir_ = ttk.LabelFrame(corpo, text=" 🎲 Gerar problema aleatório ", padding=10)
        dir_.pack(side="right", fill="y")
        meio = ttk.Frame(corpo)
        meio.pack(side="left", fill="both", expand=True, padx=10)
        colunas = ("sel", "nome", "grupo", "itens", "limites", "folga", "otimo")
        self.arvore = ttk.Treeview(meio, columns=colunas, show="headings", height=20)
        for c, t, w in zip(colunas, ["", "Problema", "Tipo", "Itens", "Limites", "Cabe", "Ótimo"],
                           [30, 150, 150, 48, 54, 48, 100]):
            self.arvore.heading(c, text=t)
            self.arvore.column(c, width=w, anchor="center" if c != "grupo" else "w")
        barra = ttk.Scrollbar(meio, orient="vertical", command=self.arvore.yview)
        self.arvore.configure(yscrollcommand=barra.set)
        self.arvore.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.arvore.bind("<Button-1>", self._clique_problema)
        self.arvore.bind("<Double-1>", self._duplo_clique)
        self.ultimo_problema = None
        self.selecionados = set()
        self._preencher_problemas()
        self._selecionar_problemas(problemas.RECOMENDACOES["Amostra pequena (3 problemas)"])

        self.tipos_geracao = {"Padrão Chu e Beasley (difícil)": "correlacionado",
                              "Não correlacionado (mais fácil)": "nao_correlacionado",
                              "Frete fracionado (3 limites)": "frete"}
        self.var_tipo = tk.StringVar(value=list(self.tipos_geracao)[0])
        self.var_n = tk.IntVar(value=100)
        self.var_m = tk.IntVar(value=5)
        self.var_folga = tk.StringVar(value="0,25")
        self.var_semente = tk.IntVar(value=1)
        self.var_exato = tk.BooleanVar(value=True)
        campos = [("Tipo", ttk.Combobox(dir_, textvariable=self.var_tipo, values=list(self.tipos_geracao),
                                        state="readonly", width=27)),
                  ("Itens (encomendas)", ttk.Spinbox(dir_, from_=10, to=1000, increment=10,
                                                     textvariable=self.var_n, width=8)),
                  ("Limites (dimensões)", ttk.Spinbox(dir_, from_=1, to=50, textvariable=self.var_m, width=8)),
                  ("Folga (quanto cabe)", ttk.Combobox(dir_, textvariable=self.var_folga,
                                                       values=["0,25", "0,50", "0,75"], width=6,
                                                       state="readonly")),
                  ("Semente (nº do sorteio)", ttk.Spinbox(dir_, from_=1, to=9999,
                                                          textvariable=self.var_semente, width=8))]
        for i, (rotulo, widget) in enumerate(campos):
            ttk.Label(dir_, text=rotulo).grid(row=2 * i, column=0, sticky="w", pady=(6, 0))
            widget.grid(row=2 * i + 1, column=0, sticky="w")
        self.spin_m = campos[2][1]
        self.var_tipo.trace_add("write", lambda *_: self.spin_m.configure(
            state="disabled" if self.tipos_geracao[self.var_tipo.get()] == "frete" else "normal"))
        ttk.Checkbutton(dir_, text="Calcular o ótimo exato\n(até 60 s; bom até ~200 itens)",
                        variable=self.var_exato).grid(row=10, column=0, sticky="w", pady=8)
        ttk.Button(dir_, text="Gerar e adicionar à lista", command=self._gerar).grid(row=11, column=0, sticky="we")
        ttk.Label(dir_, style="Dica.TLabel", wraplength=210, justify="left",
                  text="Folga 0,25 = o limite comporta 25% do total dos itens (apertado). "
                       "0,75 = folgado. A mesma semente sempre gera o mesmo problema.").grid(
            row=12, column=0, sticky="w", pady=8)

        rodape = ttk.Frame(aba)
        rodape.pack(fill="x")
        self.rotulo_sel = ttk.Label(rodape, text="")
        self.rotulo_sel.pack(side="left")
        self.bt_detalhes = ttk.Button(rodape, text="🔍  Ver detalhes (clique num problema primeiro)",
                                      command=self._detalhes)
        self.bt_detalhes.pack(side="left", padx=20)
        ttk.Label(rodape, style="Dica.TLabel",
                  text="'Cabe' = quanto do total dos itens cabe nos limites (menor = mais apertado)").pack(side="left")

    def _preencher_problemas(self):
        self.arvore.delete(*self.arvore.get_children())
        self.problemas = {p["nome"]: p for p in problemas.catalogo()}
        for nome, p in self.problemas.items():
            self.arvore.insert("", "end", iid=nome, values=(
                "☑" if nome in self.selecionados else "☐", nome,
                problemas.DESCRICAO_GRUPO.get(p["grupo"], p["grupo"]), p["n"], p["m"],
                f"{br(100 * p['folga'], 0)}%",
                br(p["otimo"], 0) if p["otimo"] else "desconhecido"))

    def _clique_problema(self, evento):
        if self.arvore.identify("region", evento.x, evento.y) != "cell":
            return
        nome = self.arvore.identify_row(evento.y)
        if not nome:
            return
        self.ultimo_problema = nome
        self.arvore.selection_set(nome)
        self.bt_detalhes.configure(text=f"🔍  Ver detalhes de {nome}  (valores, pesos e limites)")
        if nome in self.selecionados:
            self.selecionados.discard(nome)
        else:
            self.selecionados.add(nome)
        self.arvore.set(nome, "sel", "☑" if nome in self.selecionados else "☐")
        self._atualizar_resumo()

    def _duplo_clique(self, evento):
        nome = self.arvore.identify_row(evento.y)
        if not nome:
            return
        # o primeiro clique marcou/desmarcou; desfaz para o duplo clique so abrir os detalhes
        if nome in self.selecionados:
            self.selecionados.discard(nome)
        else:
            self.selecionados.add(nome)
        self.arvore.set(nome, "sel", "☑" if nome in self.selecionados else "☐")
        self._atualizar_resumo()
        self.ultimo_problema = nome
        self._detalhes()

    def _detalhes(self):
        nome = self.ultimo_problema
        if not nome or nome not in self.problemas:
            messagebox.showinfo("Escolha um problema", "Clique numa linha da lista primeiro.")
            return
        from janela_problema import JanelaProblema
        self.config(cursor="watch")
        self.update()
        try:
            JanelaProblema(self, self.problemas[nome], abrir_pasta)
        finally:
            self.config(cursor="")

    def _selecionar_problemas(self, nomes):
        self.selecionados = {n for n in nomes if n in self.problemas}
        for nome in self.problemas:
            self.arvore.set(nome, "sel", "☑" if nome in self.selecionados else "☐")
        self._atualizar_resumo()

    def _gerar(self):
        try:
            tipo = self.tipos_geracao[self.var_tipo.get()]
            n, m = int(self.var_n.get()), int(self.var_m.get())
            folga = float(self.var_folga.get().replace(",", "."))
            semente = int(self.var_semente.get())
        except (ValueError, tk.TclError):
            messagebox.showerror("Valor inválido", "Confira os números digitados.")
            return
        if not (10 <= n <= 1000 and 1 <= m <= 50):
            messagebox.showerror("Valor inválido", "Use de 10 a 1000 itens e de 1 a 50 limites.")
            return
        self.config(cursor="watch")
        self.update()
        try:
            nome, otimo = problemas.gerar(tipo, n, m, folga, semente, self.var_exato.get())
        finally:
            self.config(cursor="")
        self.selecionados.add(nome)
        self._preencher_problemas()
        self.arvore.see(nome)
        self._atualizar_resumo()
        extra = (f"Ótimo exato: {br(otimo, 0)}." if otimo else
                 "Ótimo não calculado (o gap será medido contra o limite teórico).")
        messagebox.showinfo("Problema gerado", f"'{nome}' foi criado e marcado.\n{extra}")

    def itens_escolhidos(self):
        return [self.problemas[n] for n in self.problemas if n in self.selecionados]

    # -----------------------------------------------------------------
    # ABA 3 - RODAR
    # -----------------------------------------------------------------
    def _aba_rodar(self):
        aba = ttk.Frame(self.abas, padding=12)
        self.abas.add(aba, text="  3. Rodar  ")
        conf = ttk.LabelFrame(aba, text=" Configuração ", padding=10)
        conf.pack(fill="x")
        self.var_exec = tk.IntVar(value=10)
        self.orcamentos = {"10.100 tentativas (rápido)": 10_100, "50.100 tentativas": 50_100,
                           "100.100 tentativas (igual ao TCC)": 100_100}
        self.var_orc = tk.StringVar(value="100.100 tentativas (igual ao TCC)")
        self.var_nucleos = tk.IntVar(value=motor.numero_nucleos())
        ttk.Label(conf, text="Execuções por problema:").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(conf, from_=1, to=100, textvariable=self.var_exec, width=6).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(conf, style="Dica.TLabel", text="30 = padrão de artigo; 5 a 10 = para explorar").grid(row=0, column=2, sticky="w")
        ttk.Label(conf, text="Tentativas por execução:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(conf, textvariable=self.var_orc, values=list(self.orcamentos), state="readonly",
                     width=32).grid(row=1, column=1, columnspan=2, sticky="w", padx=6)
        ttk.Label(conf, text="Núcleos do processador:").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(conf, from_=1, to=os.cpu_count() or 1, textvariable=self.var_nucleos,
                    width=6).grid(row=2, column=1, sticky="w", padx=6)
        ttk.Label(conf, style="Dica.TLabel", text="mais núcleos = mais rápido (o PC fica mais lento enquanto roda)").grid(row=2, column=2, sticky="w")
        for var in (self.var_exec, self.var_orc, self.var_nucleos):
            var.trace_add("write", lambda *_: self._atualizar_resumo())

        self.rotulo_resumo = ttk.Label(aba, font=("Segoe UI", 11), wraplength=1100, justify="left")
        self.rotulo_resumo.pack(anchor="w", pady=10)
        botoes = ttk.Frame(aba)
        botoes.pack(anchor="w")
        self.bt_rodar = ttk.Button(botoes, text="▶  Rodar experimento", style="Grande.TButton", command=self._rodar)
        self.bt_rodar.pack(side="left")
        self.bt_parar = ttk.Button(botoes, text="■  Parar", command=self._parar, state="disabled")
        self.bt_parar.pack(side="left", padx=8)
        self.barra = ttk.Progressbar(aba, mode="determinate")
        self.barra.pack(fill="x", pady=(12, 4))
        self.rotulo_status = ttk.Label(aba, text="Pronto.")
        self.rotulo_status.pack(anchor="w")
        self.log = tk.Text(aba, height=10, font=("Consolas", 9), state="disabled", bg="#F7F7F7")
        self.log.pack(fill="both", expand=True, pady=6)

    def _orcamento(self):
        return self.orcamentos.get(self.var_orc.get(), 100_100)

    def _atualizar_resumo(self):
        if not hasattr(self, "rotulo_resumo"):
            return
        algs, itens = self.algoritmos_escolhidos(), self.itens_escolhidos()
        if hasattr(self, "rotulo_sel"):
            self.rotulo_sel.configure(text=f"{len(itens)} problema(s) marcado(s).")
        try:
            execs, nuc = int(self.var_exec.get()), int(self.var_nucleos.get())
        except (ValueError, tk.TclError):
            return
        total = len(algs) * len(itens) * execs
        seg = motor.estimar_segundos(itens, algs, execs, self._orcamento(), nuc)
        tempo = f"{seg / 60:.0f} min" if seg >= 90 else f"{seg:.0f} s"
        self.rotulo_resumo.configure(text=(
            f"{len(algs)} algoritmo(s) × {len(itens)} problema(s) × {execs} execução(ões) = "
            f"{total} execuções.   Tempo estimado: ~{tempo} (estimativa grosseira)."))

    def _escrever_log(self, texto):
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        linhas = int(self.log.index("end-1c").split(".")[0])
        if linhas > 400:
            self.log.delete("1.0", f"{linhas - 400}.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _rodar(self):
        algs, itens = self.algoritmos_escolhidos(), self.itens_escolhidos()
        if not algs:
            messagebox.showwarning("Faltou escolher", "Marque pelo menos um algoritmo (aba 1).")
            return
        if not itens:
            messagebox.showwarning("Faltou escolher", "Marque pelo menos um problema (aba 2).")
            return
        execs, nuc, orc = int(self.var_exec.get()), int(self.var_nucleos.get()), self._orcamento()
        self.rodando = True
        self.parar_flag.clear()
        self.bt_rodar.configure(state="disabled")
        self.bt_parar.configure(state="normal")
        self.barra.configure(value=0, maximum=len(algs) * len(itens) * execs)
        self._escrever_log(f"--- Iniciando: {', '.join(algs)} em {len(itens)} problema(s) ---")
        threading.Thread(target=self._trabalho, args=(itens, algs, execs, orc, nuc), daemon=True).start()

    def _trabalho(self, itens, algs, execs, orc, nuc):
        try:
            motor.executar(itens, algs, execs, orc, 100, nuc,
                           avisar=self.fila.put, parar=self.parar_flag.is_set)
        except Exception as erro:  # mostra qualquer problema na tela
            self.fila.put({"tipo": "erro", "mensagem": repr(erro)})

    def _parar(self):
        self.parar_flag.set()
        self.rotulo_status.configure(text="Parando... (terminando as execuções em andamento)")

    def _ler_fila(self):
        try:
            while True:
                ev = self.fila.get_nowait()
                tipo = ev["tipo"]
                if tipo == "progresso":
                    l = ev["linha"]
                    self.barra.configure(value=ev["feitas"])
                    r = ev["restante_s"]
                    self.rotulo_status.configure(text=(
                        f"{ev['feitas']} de {ev['total']} execuções | faltam ~"
                        + (f"{r / 60:.0f} min" if r >= 90 else f"{r:.0f} s")))
                    self._escrever_log(f"{l['instancia']:>14}  {l['algoritmo']:>5}  exec {l['execucao']:>3}: "
                                       f"valor {l['melhor_valor']:>8}  gap {br(l['gap_pct'])}%")
                elif tipo == "fim":
                    self._fim(ev)
                elif tipo == "erro":
                    self._fim(None)
                    messagebox.showerror("Erro", "Aconteceu um erro:\n" + ev["mensagem"] +
                                         "\n\nVerifique a mensagem acima e tente novamente.")
                elif tipo == "parando":
                    self._escrever_log("Parada pedida pelo usuário.")
        except queue.Empty:
            pass
        self.after(200, self._ler_fila)

    def _fim(self, ev):
        self.rodando = False
        self.bt_rodar.configure(state="normal")
        self.bt_parar.configure(state="disabled")
        if ev is None:
            self.rotulo_status.configure(text="Interrompido por erro.")
            return
        self.rotulo_status.configure(text=f"Concluído: {ev['feitas']} de {ev['total']} execuções "
                                          f"em {ev['minutos']:.1f} min.")
        self._escrever_log(f"--- Fim. Resultados em {ev['pasta']} ---")
        if ev["feitas"] > 0:
            self._atualizar_experimentos(selecionar=Path(ev["pasta"]).name)
            self.abas.select(3)

    # -----------------------------------------------------------------
    # ABA 4 - RESULTADOS
    # -----------------------------------------------------------------
    def _aba_resultados(self):
        aba = ttk.Frame(self.abas, padding=10)
        self.abas.add(aba, text="  4. Resultados  ")
        topo = ttk.Frame(aba)
        topo.pack(fill="x")
        ttk.Label(topo, text="Experimento:").pack(side="left")
        self.var_exp = tk.StringVar()
        self.combo_exp = ttk.Combobox(topo, textvariable=self.var_exp, state="readonly", width=28)
        self.combo_exp.pack(side="left", padx=6)
        self.combo_exp.bind("<<ComboboxSelected>>", lambda e: self._carregar_resultados())
        ttk.Button(topo, text="Atualizar lista", command=self._atualizar_experimentos).pack(side="left")
        ttk.Button(topo, text="Exportar para Excel", command=self._exportar).pack(side="left", padx=6)
        ttk.Button(topo, text="Abrir pasta", command=self._abrir_pasta_exp).pack(side="left")
        self.rotulo_exp = ttk.Label(topo, style="Dica.TLabel")
        self.rotulo_exp.pack(side="left", padx=10)

        sub = ttk.Notebook(aba)
        sub.pack(fill="both", expand=True, pady=6)
        # Ranking
        f1 = ttk.Frame(sub, padding=8)
        sub.add(f1, text=" Ranking geral ")
        self.tab_rank = self._tabela(f1, ["Posição", "Algoritmo", "Ranking médio", "Gap médio %", "Vitórias"],
                                     [70, 330, 120, 120, 90], altura=8)
        self.rotulo_global = ttk.Label(f1, wraplength=1100, justify="left", font=("Segoe UI", 10, "bold"))
        self.rotulo_global.pack(anchor="w", pady=8)
        ttk.Label(f1, text="Pós-teste: o 1º colocado contra cada um dos outros (Wilcoxon + correção de Holm)").pack(anchor="w")
        self.tab_pos = self._tabela(f1, ["Comparação", "p (Wilcoxon)", "p ajustado (Holm)", "Resultado"],
                                    [200, 130, 150, 300], altura=6)
        ttk.Label(f1, style="Dica.TLabel", wraplength=1100, justify="left",
                  text="Como ler: o ranking médio diz a posição média de cada algoritmo nos problemas "
                       "(1 = sempre o melhor). p abaixo de 0,05 = diferença real, não sorte.").pack(anchor="w", pady=4)
        # Por problema
        f2 = ttk.Frame(sub, padding=8)
        sub.add(f2, text=" Por problema ")
        self.tab_inst = self._tabela(f2, ["Problema", "Algoritmo", "Média", "Desvio", "Melhor", "Gap médio %",
                                          "Sucesso %", "Tempo s"],
                                     [130, 90, 120, 100, 110, 110, 100, 90], altura=11)
        ttk.Label(f2, text="Teste estatístico em cada problema").pack(anchor="w", pady=(8, 0))
        self.tab_teste = self._tabela(f2, ["Problema", "Melhor média", "p geral", "Resultado"],
                                      [130, 110, 100, 450], altura=5)
        # Graficos
        f3 = ttk.Frame(sub, padding=8)
        sub.add(f3, text=" Gráficos ")
        ctrl = ttk.Frame(f3)
        ctrl.pack(fill="x")
        ttk.Label(ctrl, text="Problema:").pack(side="left")
        self.var_inst_graf = tk.StringVar()
        self.combo_inst = ttk.Combobox(ctrl, textvariable=self.var_inst_graf, state="readonly", width=20)
        self.combo_inst.pack(side="left", padx=6)
        self.combo_inst.bind("<<ComboboxSelected>>", lambda e: self._desenhar())
        self.var_graf = tk.StringVar(value="convergencia")
        for texto, valor in [("Convergência", "convergencia"), ("Caixas (boxplot)", "boxplot"),
                             ("Ranking geral", "ranking")]:
            ttk.Radiobutton(ctrl, text=texto, value=valor, variable=self.var_graf,
                            command=self._desenhar).pack(side="left", padx=6)
        ttk.Button(ctrl, text="Salvar imagem", command=self._salvar_grafico).pack(side="right")
        self.figura = Figure(figsize=(6, 3.2), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figura, master=f3)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._redesenho = None
        self.canvas.get_tk_widget().bind("<Configure>", self._ao_redimensionar, add="+")
        self.dados = None
        self._atualizar_experimentos()

    def _tabela(self, pai, colunas, larguras, altura=10):
        quadro = ttk.Frame(pai)
        quadro.pack(fill="both", expand=True)
        t = ttk.Treeview(quadro, columns=colunas, show="headings", height=altura)
        for c, w in zip(colunas, larguras):
            t.heading(c, text=c)
            t.column(c, width=w, anchor="center")
        b = ttk.Scrollbar(quadro, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=b.set)
        t.pack(side="left", fill="both", expand=True)
        b.pack(side="left", fill="y")
        return t

    def _atualizar_experimentos(self, selecionar=None):
        self.exps = {p.name: p for p in motor.experimentos_salvos()}
        self.combo_exp.configure(values=list(self.exps))
        if selecionar and selecionar in self.exps:
            self.var_exp.set(selecionar)
        elif self.exps and self.var_exp.get() not in self.exps:
            self.var_exp.set(next(iter(self.exps)))
        if self.var_exp.get():
            self._carregar_resultados()

    def _carregar_resultados(self):
        pasta = self.exps.get(self.var_exp.get())
        if not pasta:
            return
        try:
            df, conv = est.ler(pasta)
        except Exception as erro:
            messagebox.showerror("Erro", f"Não consegui ler os resultados:\n{erro}")
            return
        if df.empty:
            self.rotulo_exp.configure(text="(experimento vazio)")
            return
        rank, tabela = est.ranking(df)
        glob = est.teste_global(tabela)
        pos = est.pos_teste(tabela, rank)
        res = est.resumo_por_instancia(df)
        testes = est.teste_por_instancia(df)
        self.dados = {"df": df, "conv": conv, "rank": rank, "tabela": tabela, "pasta": pasta}
        self.rotulo_exp.configure(text=f"{len(df)} execuções · {df['algoritmo'].nunique()} algoritmos · "
                                       f"{df['instancia'].nunique()} problemas")
        for t in (self.tab_rank, self.tab_pos, self.tab_inst, self.tab_teste):
            t.delete(*t.get_children())
        for _, r in rank.iterrows():
            self.tab_rank.insert("", "end", values=(f"{r['Posição']}º", r["Nome"] if f"({r['Algoritmo']})" in r["Nome"]
                                                    else f"{r['Nome']} ({r['Algoritmo']})",
                                                    br(r["Ranking médio"]), br(r["Gap médio %"]),
                                                    r["Vitórias (1º lugar)"]))
        self.rotulo_global.configure(text=glob["texto"])
        for _, r in pos.iterrows():
            self.tab_pos.insert("", "end", values=(r["Comparação"], br(r["p (Wilcoxon)"], 4),
                                                   br(r["p ajustado (Holm)"], 4), r["Resultado"]))
        for _, r in res.iterrows():
            self.tab_inst.insert("", "end", values=(r["Instância"], r["Algoritmo"], br(r["Média"]),
                                                    br(r["Desvio"]), br(r["Melhor"], 0), br(r["Gap médio %"]),
                                                    br(r["Sucesso %"], 0), br(r["Tempo médio s"], 1)))
        for _, r in testes.iterrows():
            self.tab_teste.insert("", "end", values=(r["Instância"], r["Melhor média"],
                                                     br(r["p geral"], 4), r["Resultado"]))
        nomes = list(dict.fromkeys(df["instancia"]))
        self.combo_inst.configure(values=nomes)
        if self.var_inst_graf.get() not in nomes:
            self.var_inst_graf.set(nomes[0])
        self._desenhar()

    def _desenhar(self):
        widget = self.canvas.get_tk_widget()
        largura, altura = widget.winfo_width(), widget.winfo_height()
        if largura > 50 and altura > 50:  # ajusta a figura ao tamanho real da area
            self.figura.set_size_inches(largura / self.figura.dpi, altura / self.figura.dpi, forward=False)
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        if not self.dados:
            ax.text(0.5, 0.5, "Rode um experimento para ver os gráficos", ha="center", va="center")
            ax.axis("off")
            self.canvas.draw()
            return
        df, conv, tipo = self.dados["df"], self.dados["conv"], self.var_graf.get()
        inst = self.var_inst_graf.get()
        if tipo == "convergencia":
            d = conv[conv["instancia"] == inst]
            ref = df.loc[df["instancia"] == inst, "referencia"].iat[0]
            for alg, a in d.groupby("algoritmo", sort=False):
                curva = a.groupby("avaliacoes")["melhor_valor"].mean()
                ax.plot(curva.index, 100 * (ref - curva.values) / ref, lw=2,
                        color=self.cores.get(alg), label=est.nome(alg))
            ax.set_xlabel("Tentativas (avaliações)")
            ax.set_ylabel("Gap médio (%) — menor é melhor")
            ax.set_title(f"Convergência — {inst}")
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 0)))
            ax.legend(fontsize=8)
        elif tipo == "boxplot":
            d = df[df["instancia"] == inst]
            algs = list(dict.fromkeys(d["algoritmo"]))
            bp = ax.boxplot([d[d["algoritmo"] == a]["gap_pct"] for a in algs], patch_artist=True)
            for caixa, a in zip(bp["boxes"], algs):
                caixa.set_facecolor(self.cores.get(a))
                caixa.set_alpha(0.7)
            ax.set_xticks(range(1, len(algs) + 1))
            ax.set_xticklabels(algs)
            ax.set_ylabel("Gap (%) — menor é melhor")
            ax.set_title(f"Distribuição do gap nas execuções — {inst}")
        else:
            rank = self.dados["rank"].iloc[::-1]
            ax.barh(rank["Algoritmo"], rank["Ranking médio"],
                    color=[self.cores.get(a) for a in rank["Algoritmo"]])
            ax.set_xlabel("Ranking médio (1 = melhor)")
            ax.set_title("Ranking geral (todos os problemas do experimento)")
        ax.grid(alpha=0.3)
        self.figura.tight_layout()
        self.canvas.draw()

    def _ao_redimensionar(self, _evento):
        if self._redesenho:
            self.after_cancel(self._redesenho)
        self._redesenho = self.after(300, self._desenhar)

    def _salvar_grafico(self):
        if not self.dados:
            return
        nome = f"grafico_{self.var_graf.get()}_{self.var_inst_graf.get()}.png"
        caminho = Path(self.dados["pasta"]) / nome
        self.figura.savefig(caminho, dpi=200)
        messagebox.showinfo("Imagem salva", f"Salvo em:\n{caminho}")

    def _exportar(self):
        if not self.dados:
            messagebox.showwarning("Nada para exportar", "Escolha um experimento primeiro.")
            return
        caminho = est.exportar_excel(self.dados["pasta"])
        if messagebox.askyesno("Excel criado", f"Arquivo salvo em:\n{caminho}\n\nAbrir a pasta?"):
            abrir_pasta(caminho.parent)

    def _abrir_pasta_exp(self):
        pasta = self.exps.get(self.var_exp.get()) if hasattr(self, "exps") else None
        abrir_pasta(pasta or motor.PASTA_LAB)

    # -----------------------------------------------------------------
    # ABA 5 - SOBRE
    # -----------------------------------------------------------------
    def _aba_sobre(self):
        aba = ttk.Frame(self.abas, padding=12)
        self.abas.add(aba, text="  Sobre os algoritmos  ")
        texto = tk.Text(aba, wrap="word", font=("Segoe UI", 10), padx=10, pady=10)
        texto.pack(fill="both", expand=True)
        partes = ["COMO A COMPARAÇÃO É FEITA\n",
                  "Todos os algoritmos recebem o mesmo número de tentativas, usam o mesmo reparo "
                  "(tirar itens ao acaso até caber) e começam das mesmas 100 soluções iniciais. "
                  "Assim, qualquer diferença vem do algoritmo.\n\n"]
        for sigla, info in CATALOGO.items():
            partes.append(f"{info['nome']} ({sigla}, {info['ano']})\n")
            partes.append(f"Tipo: {info['tipo']} · Família: {info['familia']}\n")
            partes.append(f"{info['resumo']}\nReferência: {info['referencia']}\n\n")
        partes.append(
            "AVISO SOBRE OS ALGORITMOS RECENTES\n"
            "Muitos algoritmos inspirados em animais lançados nos últimos anos são criticados na "
            "literatura por repetirem ideias antigas com nomes novos (Sörensen, 2015; "
            "Camacho-Villalón, Dorigo e Stützle, 2023). A biblioteca de referência mealpy marca o "
            "Algoritmo do Quati como de status científico 'questionável'. Por isso ele está aqui: "
            "para ser testado com as mesmas regras dos outros.\n\n"
            "DETALHES DE IMPLEMENTAÇÃO\n"
            "GWO, Jaya e Quati trabalham com posições entre 0 e 1 (acima de 0,5 = leva o item). "
            "A Colônia de Formigas é uma versão simplificada inspirada em Kong, Tian e Kao (2008). "
            "Os parâmetros são os valores padrão das publicações originais.")
        texto.insert("1.0", "".join(partes))
        texto.configure(state="disabled")

    def _fechar(self):
        if self.rodando and not messagebox.askyesno(
                "Experimento rodando", "Há um experimento rodando. Parar e fechar?"):
            return
        self.parar_flag.set()
        self.destroy()


def main():
    app = Laboratorio()
    app.mainloop()


if __name__ == "__main__":
    main()
