"""
Catalogo de problemas do Laboratorio: os do TCC, os recomendados
e os gerados aleatoriamente pelo usuario.
"""
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

import config as cfg
from gerar_frete import gerar_encomendas
from instancias import PASTA_PROJETO, ler_instancia

PASTA_GERADOS = PASTA_PROJETO / "instancias" / "gerados"

RECOMENDADOS_EXTRA = {
    "OR5x100-F50": "instancias/recomendadas/OR5x100-0.50_1.dat",
    "OR5x100-F75": "instancias/recomendadas/OR5x100-0.75_1.dat",
    "OR10x250-F50": "instancias/recomendadas/OR10x250-0.50_1.dat",
    "OR10x250-F75": "instancias/recomendadas/OR10x250-0.75_1.dat",
}

# Conjuntos prontos (as "recomendacoes")
RECOMENDACOES = {
    "Amostra pequena (3 problemas)": ["PB1", "PET7", "WEING8"],
    "Conjunto do TCC (23)": list(cfg.GRUPO_1) + list(cfg.GRUPO_2) + list(cfg.GRUPO_FRETE),
    "Validação com o artigo (11)": list(cfg.GRUPO_1),
    "Escalabilidade: pequeno → gigante (9)": list(cfg.GRUPO_2),
    "Frete fracionado (3)": list(cfg.GRUPO_FRETE),
    "Efeito da folga (6)": [
        "OR5x100", "OR5x100-F50", "OR5x100-F75", "OR10x250", "OR10x250-F50", "OR10x250-F75"],
    "Desafio p/ algoritmos novos (5)": ["WEING8", "SENTO2", "OR10x250", "OR30x500", "FRETE160"],
}

DESCRICAO_GRUPO = {
    "Grupo 1": "Artigo (UDESC)",
    "Grupo 2": "Grandes (Chu-Beasley)",
    "Frete": "Frete (fictício)",
    "Recomendados": "Variação da folga",
    "Gerados": "Gerado por você",
}


def _cabecalho(caminho):
    with open(PASTA_PROJETO / caminho) as f:
        n, m, otimo = (int(float(v)) for v in f.readline().split()[:3])
    return n, m, otimo


def catalogo():
    """Lista de todos os problemas disponiveis."""
    grupos = {"Grupo 1": cfg.GRUPO_1, "Grupo 2": cfg.GRUPO_2, "Frete": cfg.GRUPO_FRETE,
              "Recomendados": RECOMENDADOS_EXTRA}
    if PASTA_GERADOS.exists():
        grupos["Gerados"] = {p.stem: str(p.relative_to(PASTA_PROJETO))
                             for p in sorted(PASTA_GERADOS.glob("*.dat"))}
    lista = []
    for grupo, arquivos in grupos.items():
        for nome, caminho in arquivos.items():
            if not (PASTA_PROJETO / caminho).exists():
                continue
            inst = ler_instancia(caminho, nome, grupo)
            folga = float(np.mean(inst.capacidades / np.maximum(1, inst.pesos.sum(axis=1))))
            lista.append({"nome": nome, "grupo": grupo, "caminho": caminho,
                          "n": inst.n, "m": inst.m, "otimo": inst.otimo, "folga": folga})
    return lista


def eh_frete(item):
    return item["grupo"] == "Frete" or item["nome"].lower().startswith("frete")


def nomes_limites(item, m):
    if eh_frete(item) and m == 3:
        return ["Peso (kg)", "Volume (litros)", "Seguro (R$)"]
    return [f"Limite {i + 1}" for i in range(m)]


def carregar(item):
    return ler_instancia(item["caminho"], item["nome"], item["grupo"])


def otimo_exato(lucros, pesos, capacidades, limite_s=60):
    res = milp(c=-lucros, constraints=LinearConstraint(pesos, -np.inf, capacidades),
               integrality=np.ones_like(lucros), bounds=Bounds(0, 1),
               options={"time_limit": limite_s})
    return int(round(-res.fun)) if res.status == 0 else 0


def gerar(tipo, n, m, folga, semente, calcular_otimo=False):
    """
    tipo:
      "correlacionado"     -> metodo de Chu e Beasley (1998): valor ligado ao peso (mais dificil)
      "nao_correlacionado" -> valores e pesos sorteados separadamente (mais facil)
      "frete"              -> encomendas de frete fracionado (3 limites: peso, volume, seguro)
    """
    rng = np.random.default_rng(semente)
    if tipo == "frete":
        enc = gerar_encomendas(n, rng)
        lucros = enc["frete_reais"]
        pesos = np.vstack([enc["peso_kg"], enc["volume_litros"], enc["valor_mercadoria_reais"]])
        # o caminhao comporta "folga" x o total que esta esperando
        capacidades = np.maximum(1, np.round(folga * pesos.sum(axis=1))).astype(int)
        nome = f"frete_n{n}_f{int(folga * 100)}_s{semente}"
    else:
        pesos = rng.integers(0, 1001, (m, n))
        capacidades = np.round(folga * pesos.sum(axis=1)).astype(int)
        if tipo == "correlacionado":
            lucros = np.round(pesos.sum(axis=0) / m + 500 * rng.random(n)).astype(int)
        else:
            lucros = rng.integers(1, 1001, n)
        sigla = "corr" if tipo == "correlacionado" else "ncorr"
        nome = f"{sigla}_n{n}_m{m}_f{int(folga * 100)}_s{semente}"

    otimo = otimo_exato(lucros, pesos, capacidades) if calcular_otimo else 0
    PASTA_GERADOS.mkdir(parents=True, exist_ok=True)
    m_real = pesos.shape[0]
    linhas = [f"{n} {m_real} {otimo}", " ".join(map(str, lucros))]
    linhas += [" ".join(map(str, linha)) for linha in pesos]
    linhas.append(" ".join(map(str, capacidades)))
    (PASTA_GERADOS / f"{nome}.dat").write_text("\n".join(linhas) + "\n")
    return nome, otimo
