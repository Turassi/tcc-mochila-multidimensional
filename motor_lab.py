"""
Motor do Laboratorio: roda algoritmos x problemas x execucoes em paralelo
e salva tudo em resultados/laboratorio/<data_hora>/.
"""
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from algoritmos_extra import CATALOGO, parametros_padrao
from instancias import PASTA_PROJETO, ler_instancia

PASTA_LAB = PASTA_PROJETO / "resultados" / "laboratorio"
SEMENTE_BASE = 2026

COLUNAS = ["grupo", "instancia", "n", "m", "algoritmo", "execucao", "semente", "melhor_valor",
           "referencia", "tipo_referencia", "gap_pct", "sucesso", "avaliacoes_ate_otimo",
           "tempo_s", "melhor_solucao"]


def rodar_tarefa(item, algoritmo, execucao, orcamento, populacao):
    """Uma execucao (roda dentro de um nucleo do processador)."""
    inst = ler_instancia(item["caminho"], item["nome"], item["grupo"])
    referencia, tipo = inst.referencia()
    p = parametros_padrao(orcamento, populacao)
    semente = SEMENTE_BASE + execucao
    r = CATALOGO[algoritmo]["funcao"](inst, semente, p)
    linha = {
        "grupo": inst.grupo, "instancia": inst.nome, "n": inst.n, "m": inst.m,
        "algoritmo": algoritmo, "execucao": execucao, "semente": semente,
        "melhor_valor": r["melhor_valor"], "referencia": round(referencia, 2),
        "tipo_referencia": tipo,
        "gap_pct": round(100 * (referencia - r["melhor_valor"]) / referencia, 4),
        "sucesso": int(inst.otimo is not None and r["melhor_valor"] >= inst.otimo),
        "avaliacoes_ate_otimo": r["avaliacoes_ate_otimo"] or "",
        "tempo_s": round(r["tempo_s"], 3), "melhor_solucao": r["melhor_solucao"],
    }
    hist = [[inst.nome, algoritmo, execucao, a, v] for a, v in r["historico"]]
    return linha, hist


def estimar_segundos(itens, algoritmos, execucoes, orcamento, nucleos):
    """Estimativa grosseira, baseada nos tempos medidos no TCC."""
    total = 0.0
    for item in itens:
        base = 3.0 + 0.012 * item["n"] + 0.0004 * item["n"] * item["m"]
        total += base * (orcamento / 100_100) * len(algoritmos) * execucoes
    return total / max(1, nucleos)


def executar(itens, algoritmos, execucoes, orcamento, populacao, nucleos,
             avisar, parar):
    """
    itens: lista de problemas (do catalogo)
    avisar(evento: dict): recebe o progresso
    parar(): devolve True se o usuario pediu para parar
    """
    pasta = PASTA_LAB / datetime.now().strftime("%Y-%m-%d_%Hh%Mm%Ss")
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "configuracao.json").write_text(json.dumps({
        "algoritmos": algoritmos, "problemas": [i["nome"] for i in itens],
        "execucoes": execucoes, "orcamento": orcamento, "populacao": populacao,
        "semente_base": SEMENTE_BASE, "inicio": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    tarefas = [(item, alg, e) for item in itens for alg in algoritmos
               for e in range(1, execucoes + 1)]
    total = len(tarefas)
    avisar({"tipo": "inicio", "total": total, "pasta": str(pasta)})
    inicio = time.time()
    feitas = 0
    with open(pasta / "execucoes.csv", "w", newline="", encoding="utf-8") as fe, \
         open(pasta / "convergencia.csv", "w", newline="", encoding="utf-8") as fc:
        we, wc = csv.DictWriter(fe, COLUNAS), csv.writer(fc)
        we.writeheader()
        wc.writerow(["instancia", "algoritmo", "execucao", "avaliacoes", "melhor_valor"])
        pool = ProcessPoolExecutor(max_workers=max(1, nucleos))
        try:
            futuros = [pool.submit(rodar_tarefa, it, alg, e, orcamento, populacao)
                       for it, alg, e in tarefas]
            for futuro in as_completed(futuros):
                if parar():
                    avisar({"tipo": "parando"})
                    break
                linha, hist = futuro.result()
                we.writerow(linha)
                wc.writerows(hist)
                fe.flush()
                fc.flush()
                feitas += 1
                decorrido = time.time() - inicio
                avisar({"tipo": "progresso", "feitas": feitas, "total": total,
                        "restante_s": decorrido / feitas * (total - feitas), "linha": linha})
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
    avisar({"tipo": "fim", "feitas": feitas, "total": total, "pasta": str(pasta),
            "minutos": (time.time() - inicio) / 60})
    return pasta


def experimentos_salvos():
    if not PASTA_LAB.exists():
        return []
    return sorted((p for p in PASTA_LAB.iterdir() if (p / "execucoes.csv").exists()),
                  reverse=True)


def numero_nucleos():
    return max(1, (os.cpu_count() or 2) - 1)
