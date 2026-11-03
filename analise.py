"""
Analise dos resultados: gera as tabelas, os testes estatisticos e os
graficos que vao para o TCC.

Uso:
    py analise.py            -> analisa o experimento completo

Saidas (pasta resultados/):
    tabelas_tcc.xlsx   -> todas as tabelas, uma por aba (abre no Excel)
    resumo.txt         -> os principais achados escritos em portugues
    graficos/          -> imagens prontas para colar no TCC
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon

import config as cfg
from algoritmos import NOMES_COMPLETOS
from instancias import carregar_todas

PASTA = Path(__file__).resolve().parent / "resultados"
CORES = {"AG": "#C0504D", "EDB": "#4F81BD"}

# Resultados publicados por Andre e Parpinelli (2015), Tabela II
# (media do melhor valor, taxa de sucesso %, avaliacoes ate o otimo)
ARTIGO = {
    "AG": {"PB1": (3085.26, 82, 34995.18), "PB2": (3131.08, 17, 89051.75),
           "PB4": (95071.01, 97, 9251.30), "PB5": (2138.15, 95, 29852.48),
           "PB6": (769.57, 68, 51759.22), "PB7": (1026.34, 17, 92079.76),
           "PET7": (16428.88, 0, 100100), "SENTO1": (7640.90, 0, 100100),
           "SENTO2": (8620.05, 0, 100100), "WEING8": (566282.95, 0, 100100),
           "WEISH30": (10824.70, 0, 100100)},
    "EDB": {"PB1": (3089.07, 96, 14104.50), "PB2": (3144.55, 14, 91164.94),
            "PB4": (95168.00, 100, 4672.21), "PB5": (2135.60, 80, 32052.98),
            "PB6": (775.86, 99, 7200.84), "PB7": (1034.12, 77, 35502.17),
            "PET7": (16524.58, 56, 65795.81), "SENTO1": (7771.44, 97, 17091.08),
            "SENTO2": (8720.37, 67, 50493.94), "WEING8": (624062.37, 86, 55705.08),
            "WEISH30": (11191.00, 100, 33645.37)},
}


ACENTOS = {
    "Instancias": "Instâncias", "Instancia": "Instância", "instancias": "instâncias",
    "instancia": "instância", "INSTANCIA": "INSTÂNCIA", "media": "média", "medio": "médio",
    "Referencia": "Referência", "referencia": "referência", "otimo": "ótimo",
    "Execucoes": "Execuções", "execucoes": "execuções", "Diferenca": "Diferença",
    "diferenca": "diferença", "Diferencas": "Diferenças", "significancia": "significância",
    "Validacao": "Validação", "VALIDACAO": "VALIDAÇÃO", "orcamento": "orçamento",
    "Cenario": "Cenário", "CENARIOS": "CENÁRIOS", "disponiveis": "disponíveis",
    "Genetico": "Genético", "Evolucao": "Evolução", "Binaria": "Binária",
    "Distribuicao": "Distribuição", "Convergencia": "Convergência",
    "avaliacoes": "avaliações", "funcao": "função", "COMPARACAO": "COMPARAÇÃO",
    "Nao": "Não", "nao": "não", "atencao": "atenção", "implementacao": "implementação",
    "AUTOMATICO": "AUTOMÁTICO", "sao": "são", "nivel": "nível", "Nivel": "Nível", "instancias": "instâncias", "analise": "análise",
}


def acentuar(texto):
    """Coloca os acentos nos textos que vao para tabelas, graficos e resumo."""
    import re
    if not isinstance(texto, str):
        return texto
    for sem, com in ACENTOS.items():
        texto = re.sub(rf"\b{sem}\b", com, texto)
    return texto


def preparar(tabela):
    """Acentua cabecalhos e textos de uma tabela antes de ir para o Excel."""
    t = tabela.copy()
    t.columns = [acentuar(c) for c in t.columns]
    for c in t.columns:
        if not pd.api.types.is_numeric_dtype(t[c]):
            t[c] = t[c].map(acentuar)
    return t


def br(x, casas=2):
    """Formata numero no padrao brasileiro (1.234,56)."""
    if pd.isna(x):
        return "-"
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_resumo(df):
    linhas = []
    for (grupo, inst), d in df.groupby(["grupo", "instancia"], sort=False):
        base = {"Grupo": grupo, "Instancia": inst, "Itens (n)": d["n"].iat[0],
                "Limites (m)": d["m"].iat[0], "Referencia": d["referencia"].iat[0],
                "Tipo de referencia": d["tipo_referencia"].iat[0]}
        for alg in NOMES_COMPLETOS:
            a = d[d["algoritmo"] == alg]
            if a.empty:
                continue
            tem_otimo = a["tipo_referencia"].iat[0] == "otimo"
            aval = a["avaliacoes_ate_otimo"].fillna(cfg.ORCAMENTO_AVALIACOES)
            base.update({
                f"{alg} melhor": a["melhor_valor"].max(),
                f"{alg} media": a["melhor_valor"].mean(),
                f"{alg} desvio": a["melhor_valor"].std(ddof=1),
                f"{alg} pior": a["melhor_valor"].min(),
                f"{alg} gap medio %": a["gap_pct"].mean(),
                f"{alg} sucesso %": 100 * a["sucesso"].mean() if tem_otimo else np.nan,
                f"{alg} aval. ate otimo": aval.mean() if tem_otimo else np.nan,
                f"{alg} tempo medio s": a["tempo_s"].mean(),
            })
        linhas.append(base)
    return pd.DataFrame(linhas)


def testes_por_instancia(df, alfa):
    """Mann-Whitney: as 30 execucoes do AG contra as 30 da EDB, instancia por instancia."""
    linhas = []
    for (grupo, inst), d in df.groupby(["grupo", "instancia"], sort=False):
        ag = d.loc[d["algoritmo"] == "AG", "melhor_valor"].to_numpy()
        ed = d.loc[d["algoritmo"] == "EDB", "melhor_valor"].to_numpy()
        if len(ag) < 2 or len(ed) < 2:
            continue
        if np.unique(np.concatenate([ag, ed])).size == 1:
            p = 1.0  # todos os valores iguais: nao ha diferenca
        else:
            p = float(mannwhitneyu(ag, ed, alternative="two-sided").pvalue)
        if p < alfa:
            veredito = "EDB melhor" if np.median(ed) > np.median(ag) or (
                np.median(ed) == np.median(ag) and ed.mean() > ag.mean()) else "AG melhor"
        else:
            veredito = "Sem diferenca significativa"
        linhas.append({"Grupo": grupo, "Instancia": inst, "Mediana AG": np.median(ag),
                       "Mediana EDB": np.median(ed), "p-valor (Mann-Whitney)": p,
                       "Resultado": veredito})
    return pd.DataFrame(linhas)


def teste_global(resumo, alfa):
    """Wilcoxon pareado: o gap medio de cada instancia, AG contra EDB."""
    linhas = []
    conjuntos = [(g, resumo[resumo["Grupo"] == g]) for g in resumo["Grupo"].unique()]
    conjuntos.append(("Todas as instancias", resumo))
    for nome, r in conjuntos:
        ag, ed = r["AG gap medio %"].to_numpy(), r["EDB gap medio %"].to_numpy()
        dif = ag - ed
        if len(r) < 2 or np.allclose(dif, 0):
            p = 1.0
        else:
            p = float(wilcoxon(ag, ed).pvalue)
        linhas.append({
            "Conjunto": nome, "Instancias": len(r),
            "EDB com menor gap": int((dif > 1e-9).sum()),
            "AG com menor gap": int((dif < -1e-9).sum()),
            "Empates": int((np.abs(dif) <= 1e-9).sum()),
            "Gap medio AG %": ag.mean(), "Gap medio EDB %": ed.mean(),
            "p-valor (Wilcoxon)": p,
            "Diferenca significativa?": "Sim" if p < alfa else "Nao",
        })
    return pd.DataFrame(linhas)


def tabela_validacao(resumo):
    linhas = []
    for _, r in resumo[resumo["Grupo"] == "Grupo 1"].iterrows():
        inst = r["Instancia"]
        if inst not in ARTIGO["AG"]:
            continue
        linha = {"Instancia": inst}
        for alg in ("AG", "EDB"):
            media_art, suc_art, _ = ARTIGO[alg][inst]
            linha.update({f"{alg} media (artigo)": media_art,
                          f"{alg} media (este trabalho)": r[f"{alg} media"],
                          f"{alg} sucesso % (artigo)": suc_art,
                          f"{alg} sucesso % (este trabalho)": r[f"{alg} sucesso %"]})
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tabela_orcamento(conv, refs, marcos):
    """Qualidade (gap medio) com 10%, 50% e 100% das tentativas."""
    linhas = []
    for (inst, alg), d in conv.groupby(["instancia", "algoritmo"], sort=False):
        linha = {"Instancia": inst, "Algoritmo": alg}
        for marco in marcos:
            ate = d[d["avaliacoes"] <= marco].groupby("execucao")["melhor_valor"].max()
            linha[f"gap % com {marco:,} tentativas".replace(",", ".")] = \
                100 * (refs[inst] - ate.mean()) / refs[inst]
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tabela_frete(df, instancias):
    linhas = []
    for inst in instancias:
        if inst.grupo != "Frete":
            continue
        d = df[df["instancia"] == inst.nome]
        for alg in NOMES_COMPLETOS:
            a = d[d["algoritmo"] == alg]
            if a.empty:
                continue
            melhor = a.loc[a["melhor_valor"].idxmax()]
            x = np.array([int(c) for c in melhor["melhor_solucao"]])
            uso = 100 * (inst.pesos @ x) / inst.capacidades
            ref = inst.referencia()[0]
            linhas.append({
                "Cenario": inst.nome, "Encomendas disponiveis": inst.n,
                "Algoritmo": alg, "Frete otimo R$": inst.otimo,
                "Frete medio obtido R$": a["melhor_valor"].mean(),
                "% do otimo (media)": 100 * a["melhor_valor"].mean() / ref,
                "Melhor frete obtido R$": melhor["melhor_valor"],
                "Encomendas embarcadas (melhor)": int(x.sum()),
                "Uso do peso %": uso[0], "Uso do volume %": uso[1],
                "Uso do seguro %": uso[2],
                "Execucoes que acharam o otimo %": 100 * a["sucesso"].mean(),
            })
    return pd.DataFrame(linhas)


def graficos(df, conv, refs, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    # 1) Convergencia: como o gap cai ao longo das tentativas
    for inst, d in conv.groupby("instancia", sort=False):
        fig, ax = plt.subplots(figsize=(7, 4))
        for alg, a in d.groupby("algoritmo"):
            curva = a.groupby("avaliacoes")["melhor_valor"].mean()
            gap = 100 * (refs[inst] - curva) / refs[inst]
            ax.plot(gap.index, gap.values, label=acentuar(NOMES_COMPLETOS[alg]), color=CORES[alg], lw=2)
        ax.set_xlabel(acentuar("Tentativas (avaliacoes da funcao objetivo)"))
        ax.set_ylabel(acentuar("Gap medio (%)"))
        ax.set_title(acentuar(f"Convergencia - {inst}"))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v, 0)))
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(pasta / f"convergencia_{inst}.png", dpi=200)
        plt.close(fig)

    # 2) Boxplot do gap por instancia, um grafico por grupo
    for grupo, d in df.groupby("grupo", sort=False):
        nomes = list(dict.fromkeys(d["instancia"]))
        fig, ax = plt.subplots(figsize=(max(7, 1.1 * len(nomes)), 4.5))
        pos = np.arange(len(nomes))
        for desloc, alg in ((-0.2, "AG"), (0.2, "EDB")):
            dados = [d[(d["instancia"] == i) & (d["algoritmo"] == alg)]["gap_pct"] for i in nomes]
            bp = ax.boxplot(dados, positions=pos + desloc, widths=0.35, patch_artist=True,
                            showfliers=True)
            for caixa in bp["boxes"]:
                caixa.set_facecolor(CORES[alg])
                caixa.set_alpha(0.7)
            ax.plot([], [], color=CORES[alg], lw=8, alpha=0.7, label=acentuar(NOMES_COMPLETOS[alg]))
        ax.set_xticks(pos)
        ax.set_xticklabels(nomes, rotation=30)
        ax.set_ylabel("Gap (%) - quanto menor, melhor")
        ax.set_title(acentuar(f"Distribuicao do gap nas execucoes - {grupo}"))
        ax.grid(axis="y", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(pasta / f"boxplot_{grupo.replace(' ', '_').lower()}.png", dpi=200)
        plt.close(fig)


def escrever_resumo(resumo, testes, glob, valid, frete, caminho, alfa, n_exec):
    t = ["RESUMO AUTOMATICO DOS RESULTADOS", "=" * 60, ""]
    t.append(f"Execucoes por instancia e algoritmo: {n_exec} | "
             f"orcamento: {br(cfg.ORCAMENTO_AVALIACOES, 0)} tentativas | "
             f"nivel de significancia: {int(alfa * 100)}%")
    t.append("")
    t.append("1) COMPARACAO GERAL (Wilcoxon pareado, gap medio por instancia)")
    for _, g in glob.iterrows():
        t.append(f"   - {g['Conjunto']}: gap medio AG = {br(g['Gap medio AG %'])}%, "
                 f"EDB = {br(g['Gap medio EDB %'])}%. EDB melhor em {g['EDB com menor gap']}, "
                 f"AG melhor em {g['AG com menor gap']}, empates {g['Empates']}. "
                 f"p = {br(g['p-valor (Wilcoxon)'], 4)} -> diferenca significativa: "
                 f"{g['Diferenca significativa?']}.")
        if g["Instancias"] < 6:
            t.append("     (atencao: com menos de 6 instancias o Wilcoxon nao consegue "
                     "dar p < 0,05; use o teste por instancia abaixo)")
    t.append("")
    t.append("2) INSTANCIA POR INSTANCIA (Mann-Whitney)")
    for _, r in testes.iterrows():
        t.append(f"   - {r['Instancia']}: {r['Resultado']} (p = {br(r['p-valor (Mann-Whitney)'], 4)})")
    contagem = testes["Resultado"].value_counts()
    t.append("   Total: " + ", ".join(f"{k}: {v}" for k, v in contagem.items()))
    t.append("")
    if not valid.empty:
        t.append("3) VALIDACAO CONTRA O ARTIGO DE ANDRE E PARPINELLI (2015)")
        for _, v in valid.iterrows():
            t.append(f"   - {v['Instancia']}: sucesso AG {br(v['AG sucesso % (este trabalho)'], 0)}% "
                     f"(artigo {v['AG sucesso % (artigo)']}%) | EDB "
                     f"{br(v['EDB sucesso % (este trabalho)'], 0)}% (artigo {v['EDB sucesso % (artigo)']}%)")
        t.append("   Diferencas pequenas sao normais (sorte e detalhes de implementacao).")
        t.append("")
    if not frete.empty:
        t.append("4) CENARIOS DE FRETE FRACIONADO")
        for _, f in frete.iterrows():
            t.append(f"   - {f['Cenario']} / {f['Algoritmo']}: em media {br(f['% do otimo (media)'])}% "
                     f"do frete otimo (R$ {br(f['Frete otimo R$'], 0)}); melhor carga embarcou "
                     f"{f['Encomendas embarcadas (melhor)']} encomendas, usando "
                     f"{br(f['Uso do peso %'], 0)}% do peso, {br(f['Uso do volume %'], 0)}% do volume "
                     f"e {br(f['Uso do seguro %'], 0)}% do seguro.")
    caminho.write_text("\n".join(acentuar(linha) for linha in t) + "\n", encoding="utf-8")


def main():
    prefixo = ""

    arq_exec = PASTA / f"{prefixo}execucoes.csv"
    arq_conv = PASTA / f"{prefixo}convergencia.csv"
    if not arq_exec.exists():
        print("Nao achei os resultados. Rode o experimento primeiro.")
        return
    df = pd.read_csv(arq_exec, dtype={"melhor_solucao": str})
    conv = pd.read_csv(arq_conv)
    print(f"Lidas {len(df)} execucoes.")

    grupos = {"Grupo 1": cfg.GRUPO_1, "Grupo 2": cfg.GRUPO_2, "Frete": cfg.GRUPO_FRETE}
    nomes_usados = set(df["instancia"])
    grupos = {g: {k: v for k, v in arqs.items() if k in nomes_usados} for g, arqs in grupos.items()}
    instancias = carregar_todas(grupos)
    refs = {i.nome: i.referencia()[0] for i in instancias}

    alfa = cfg.NIVEL_SIGNIFICANCIA
    resumo = tabela_resumo(df)
    testes = testes_por_instancia(df, alfa)
    glob = teste_global(resumo, alfa)
    valid = tabela_validacao(resumo)
    marcos = [cfg.ORCAMENTO_AVALIACOES // 10 // 1000 * 1000,
              cfg.ORCAMENTO_AVALIACOES // 2 // 1000 * 1000,
              cfg.ORCAMENTO_AVALIACOES // 1000 * 1000]
    orcamento = tabela_orcamento(conv, refs, marcos)
    frete = tabela_frete(df, instancias)

    saida = PASTA / f"{prefixo}tabelas_tcc.xlsx"
    with pd.ExcelWriter(saida, engine="openpyxl") as xl:
        preparar(resumo.round(2)).to_excel(xl, sheet_name=acentuar("1 Resumo"), index=False)
        preparar(testes.round(4)).to_excel(xl, sheet_name=acentuar("2 Teste por instancia"), index=False)
        preparar(glob.round(4)).to_excel(xl, sheet_name=acentuar("3 Teste global"), index=False)
        if not valid.empty:
            preparar(valid.round(2)).to_excel(xl, sheet_name=acentuar("4 Validacao artigo"), index=False)
        preparar(orcamento.round(3)).to_excel(xl, sheet_name=acentuar("5 Gap por orcamento"), index=False)
        if not frete.empty:
            preparar(frete.round(2)).to_excel(xl, sheet_name=acentuar("6 Frete fracionado"), index=False)
        for aba in xl.sheets.values():
            for coluna in aba.columns:
                aba.column_dimensions[coluna[0].column_letter].width = 18

    graficos(df, conv, refs, PASTA / f"{prefixo}graficos")
    n_exec = int(df.groupby(["instancia", "algoritmo"]).size().max())
    escrever_resumo(resumo, testes, glob, valid, frete, PASTA / f"{prefixo}resumo.txt", alfa, n_exec)
    print(f"Tabelas: {saida}")
    print(f"Graficos: {PASTA / (prefixo + 'graficos')}")
    print(f"Resumo em texto: {PASTA / (prefixo + 'resumo.txt')}")


if __name__ == "__main__":
    main()
