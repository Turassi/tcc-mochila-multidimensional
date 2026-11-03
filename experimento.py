"""
Roda o experimento: cada algoritmo x cada instancia x 30 execucoes.

Uso:
    py experimento.py            -> experimento completo
    py experimento.py --execucoes 5  -> so 5 execucoes (depois da para
                                        completar ate 30 rodando sem a opcao)

Se o computador desligar no meio, e so rodar de novo: o programa
pula o que ja foi feito e continua de onde parou.

Resultados (pasta resultados/):
    execucoes.csv      -> uma linha por execucao
    convergencia.csv   -> melhor valor a cada 1000 tentativas
"""
import argparse
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import config as cfg
from algoritmos import ALGORITMOS
from instancias import carregar_todas

PASTA = Path(__file__).resolve().parent
PASTA_RESULTADOS = PASTA / "resultados"
ARQ_EXECUCOES = PASTA_RESULTADOS / "execucoes.csv"
ARQ_CONVERGENCIA = PASTA_RESULTADOS / "convergencia.csv"

COLUNAS_EXEC = ["grupo", "instancia", "n", "m", "algoritmo", "execucao", "semente",
                "melhor_valor", "referencia", "tipo_referencia", "gap_pct", "sucesso",
                "avaliacoes_ate_otimo", "tempo_s", "melhor_solucao"]
COLUNAS_CONV = ["instancia", "algoritmo", "execucao", "avaliacoes", "melhor_valor"]


def rodar_uma(inst, algoritmo, execucao):
    """Roda UMA execucao (e chamada em paralelo pelos nucleos do processador)."""
    semente = cfg.SEMENTE_BASE + execucao
    referencia, tipo = inst.referencia()
    r = ALGORITMOS[algoritmo](inst, semente, cfg, inst.otimo)
    gap = 100 * (referencia - r["melhor_valor"]) / referencia
    linha = {
        "grupo": inst.grupo, "instancia": inst.nome, "n": inst.n, "m": inst.m,
        "algoritmo": algoritmo, "execucao": execucao, "semente": semente,
        "melhor_valor": r["melhor_valor"], "referencia": round(referencia, 2),
        "tipo_referencia": tipo, "gap_pct": round(gap, 4),
        "sucesso": int(inst.otimo is not None and r["melhor_valor"] >= inst.otimo),
        "avaliacoes_ate_otimo": r["avaliacoes_ate_otimo"] or "",
        "tempo_s": round(r["tempo_s"], 3), "melhor_solucao": r["melhor_solucao"],
    }
    historico = [[inst.nome, algoritmo, execucao, a, v] for a, v in r["historico"]]
    return linha, historico


def ja_feitas():
    if not ARQ_EXECUCOES.exists():
        return set()
    with open(ARQ_EXECUCOES, encoding="utf-8") as f:
        return {(l["instancia"], l["algoritmo"], int(l["execucao"])) for l in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execucoes", type=int, default=cfg.EXECUCOES,
                        help="quantas execucoes por instancia (padrao: config.py)")
    args = parser.parse_args()

    grupos = {"Grupo 1": cfg.GRUPO_1, "Grupo 2": cfg.GRUPO_2, "Frete": cfg.GRUPO_FRETE}
    execucoes = args.execucoes

    PASTA_RESULTADOS.mkdir(exist_ok=True)
    print("Carregando instancias...")
    instancias = carregar_todas(grupos)
    for inst in instancias:
        inst.referencia()  # calcula o limitante antes de mandar para os nucleos

    feitas = ja_feitas()
    tarefas = [(inst, alg, e) for inst in instancias for alg in ALGORITMOS
               for e in range(1, execucoes + 1) if (inst.nome, alg, e) not in feitas]
    total = len(tarefas)
    if total == 0:
        print("Tudo ja foi executado! Agora rode a analise.")
        return
    if feitas:
        print(f"Continuando de onde parou ({len(feitas)} execucoes ja feitas).")

    nucleos = max(1, (os.cpu_count() or 2) - 1)
    print(f"{total} execucoes para fazer, usando {nucleos} nucleos do processador.")
    print("Pode deixar rodando. Nao feche esta janela.\n")

    novo_exec = not ARQ_EXECUCOES.exists()
    novo_conv = not ARQ_CONVERGENCIA.exists()
    inicio = time.time()
    with open(ARQ_EXECUCOES, "a", newline="", encoding="utf-8") as fe, \
         open(ARQ_CONVERGENCIA, "a", newline="", encoding="utf-8") as fc:
        we, wc = csv.DictWriter(fe, COLUNAS_EXEC), csv.writer(fc)
        if novo_exec:
            we.writeheader()
        if novo_conv:
            wc.writerow(COLUNAS_CONV)

        with ProcessPoolExecutor(max_workers=nucleos) as pool:
            futuros = [pool.submit(rodar_uma, *t) for t in tarefas]
            for feitos, futuro in enumerate(as_completed(futuros), start=1):
                linha, historico = futuro.result()
                we.writerow(linha)
                wc.writerows(historico)
                fe.flush()
                fc.flush()
                decorrido = time.time() - inicio
                restante = decorrido / feitos * (total - feitos)
                print(f"[{feitos}/{total}] {linha['instancia']:>9} {linha['algoritmo']:>3} "
                      f"exec {linha['execucao']:>2}: valor {linha['melhor_valor']:>7} "
                      f"(gap {linha['gap_pct']:.2f}%) | faltam ~{restante / 60:.0f} min",
                      flush=True)

    print(f"\nPronto! Levou {(time.time() - inicio) / 60:.1f} minutos.")
    print(f"Resultados salvos em: {ARQ_EXECUCOES}")


if __name__ == "__main__":
    sys.exit(main())
