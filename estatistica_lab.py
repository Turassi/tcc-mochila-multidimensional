"""
Estatistica do Laboratorio para VARIOS algoritmos (Derrac et al., 2011):
  - ranking medio de cada algoritmo (1o lugar = 1);
  - teste de Friedman: "existe diferenca entre os algoritmos?";
  - pos-teste de Holm: o melhor algoritmo contra cada um dos outros.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, kruskal, mannwhitneyu, wilcoxon

from algoritmos_extra import CATALOGO

ALFA = 0.05


def ler(pasta):
    pasta = Path(pasta)
    df = pd.read_csv(pasta / "execucoes.csv", dtype={"melhor_solucao": str})
    conv = pd.read_csv(pasta / "convergencia.csv")
    return df, conv


def nome(alg):
    return CATALOGO.get(alg, {}).get("nome", alg)


def resumo_por_instancia(df):
    linhas = []
    for (inst, alg), d in df.groupby(["instancia", "algoritmo"], sort=False):
        tem_otimo = d["tipo_referencia"].iat[0] == "otimo"
        linhas.append({
            "Instância": inst, "Grupo": d["grupo"].iat[0], "Algoritmo": alg,
            "Execuções": len(d), "Melhor": d["melhor_valor"].max(),
            "Média": d["melhor_valor"].mean(), "Desvio": d["melhor_valor"].std(ddof=1),
            "Pior": d["melhor_valor"].min(), "Gap médio %": d["gap_pct"].mean(),
            "Sucesso %": 100 * d["sucesso"].mean() if tem_otimo else np.nan,
            "Tempo médio s": d["tempo_s"].mean(),
        })
    return pd.DataFrame(linhas)


def holm(pvalores):
    """Correcao de Holm: ajusta os p-valores quando ha varias comparacoes."""
    p = np.asarray(pvalores, dtype=float)
    ordem = np.argsort(p)
    ajust = np.empty_like(p)
    k = len(p)
    acumulado = 0.0
    for posicao, idx in enumerate(ordem):
        acumulado = max(acumulado, min(1.0, (k - posicao) * p[idx]))
        ajust[idx] = acumulado
    return ajust


def ranking(df):
    """Gap medio por instancia -> posicao de cada algoritmo -> media das posicoes."""
    tabela = df.pivot_table(index="instancia", columns="algoritmo", values="gap_pct", aggfunc="mean")
    posicoes = tabela.rank(axis=1, method="average")
    vitorias = (posicoes == 1).sum()
    r = pd.DataFrame({
        "Algoritmo": tabela.columns,
        "Nome": [nome(a) for a in tabela.columns],
        "Ranking médio": posicoes.mean().values,
        "Gap médio %": tabela.mean().values,
        "Vitórias (1º lugar)": vitorias.values,
    }).sort_values("Ranking médio").reset_index(drop=True)
    r.insert(0, "Posição", range(1, len(r) + 1))
    return r, tabela


def teste_global(tabela):
    """Friedman (3 ou mais algoritmos) ou Wilcoxon (2 algoritmos)."""
    algs, k, n = list(tabela.columns), tabela.shape[1], tabela.shape[0]
    if k < 2 or n < 2:
        return {"teste": "-", "p": np.nan,
                "texto": "São necessários pelo menos 2 algoritmos e 2 problemas para o teste global."}
    dados = [tabela[a].values for a in algs]
    if k == 2:
        dif = dados[0] - dados[1]
        p = 1.0 if np.allclose(dif, 0) else float(wilcoxon(dados[0], dados[1]).pvalue)
        teste = "Wilcoxon pareado"
    else:
        if all(np.allclose(d, dados[0]) for d in dados):
            p = 1.0
        else:
            p = float(friedmanchisquare(*dados).pvalue)
        teste = "Friedman"
    sig = p < ALFA
    texto = (f"Teste de {teste} com {n} problemas: p = {p:.4f}. ".replace(".", ",", 1)
             + ("Existe diferença significativa entre os algoritmos."
                if sig else "Não foi possível afirmar que os algoritmos são diferentes."))
    if n < 6:
        texto += " (Atenção: com menos de 6 problemas o teste tem pouco poder.)"
    return {"teste": teste, "p": p, "texto": texto}


def pos_teste(tabela, rank):
    """O 1o colocado contra cada um dos outros (Wilcoxon + correcao de Holm)."""
    if tabela.shape[1] < 2 or tabela.shape[0] < 2:
        return pd.DataFrame()
    melhor = rank["Algoritmo"].iat[0]
    outros = [a for a in rank["Algoritmo"] if a != melhor]
    brutos = []
    for a in outros:
        dif = tabela[melhor].values - tabela[a].values
        brutos.append(1.0 if np.allclose(dif, 0) else float(wilcoxon(tabela[melhor], tabela[a]).pvalue))
    ajustados = holm(brutos)
    return pd.DataFrame({
        "Comparação": [f"{melhor} x {a}" for a in outros],
        "p (Wilcoxon)": brutos, "p ajustado (Holm)": ajustados,
        "Resultado": [f"{melhor} melhor" if pa < ALFA else "Sem diferença significativa"
                      for pa in ajustados],
    })


def teste_por_instancia(df):
    """Em cada problema: Kruskal-Wallis entre todos + melhor contra cada outro (Holm)."""
    linhas = []
    for inst, d in df.groupby("instancia", sort=False):
        grupos = {a: g["melhor_valor"].values for a, g in d.groupby("algoritmo")}
        if len(grupos) < 2 or min(len(v) for v in grupos.values()) < 2:
            continue
        valores = list(grupos.values())
        todos_iguais = np.unique(np.concatenate(valores)).size == 1
        if len(grupos) >= 3:
            p_geral = 1.0 if todos_iguais else float(kruskal(*valores).pvalue)
        else:
            p_geral = 1.0 if todos_iguais else float(mannwhitneyu(*valores).pvalue)
        medias = {a: v.mean() for a, v in grupos.items()}
        lider = max(medias, key=medias.get)
        outros = [a for a in grupos if a != lider]
        brutos = []
        for a in outros:
            junto = np.concatenate([grupos[lider], grupos[a]])
            brutos.append(1.0 if np.unique(junto).size == 1
                          else float(mannwhitneyu(grupos[lider], grupos[a]).pvalue))
        ajust = holm(brutos)
        empatados = [a for a, pa in zip(outros, ajust) if pa >= ALFA]
        linhas.append({
            "Instância": inst, "Melhor média": lider, "p geral": p_geral,
            "Empatados com o melhor": ", ".join(empatados) if empatados else "nenhum",
            "Resultado": (f"{lider} melhor que todos" if not empatados
                          else f"{lider} na frente, empatado com {len(empatados)}")
                         if p_geral < ALFA else "Sem diferença significativa",
        })
    return pd.DataFrame(linhas)


def exportar_excel(pasta):
    df, conv = ler(pasta)
    res = resumo_por_instancia(df)
    rank, tabela = ranking(df)
    glob = teste_global(tabela)
    pos = pos_teste(tabela, rank)
    porinst = teste_por_instancia(df)
    saida = Path(pasta) / "resultados_laboratorio.xlsx"
    with pd.ExcelWriter(saida, engine="openpyxl") as xl:
        rank.round(3).to_excel(xl, sheet_name="1 Ranking", index=False)
        pd.DataFrame({"Teste global": [glob["texto"]]}).to_excel(
            xl, sheet_name="1 Ranking", index=False, startrow=len(rank) + 2)
        if not pos.empty:
            pos.round(4).to_excel(xl, sheet_name="2 Pos-teste Holm", index=False)
        porinst.round(4).to_excel(xl, sheet_name="3 Teste por problema", index=False)
        res.round(3).to_excel(xl, sheet_name="4 Resumo detalhado", index=False)
        tabela.round(3).to_excel(xl, sheet_name="5 Gap por problema")
        for aba in xl.sheets.values():
            for coluna in aba.columns:
                aba.column_dimensions[coluna[0].column_letter].width = 20
    return saida
