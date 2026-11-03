"""
Gera cenarios FICTICIOS (mas com numeros realistas) de frete fracionado.

A situacao: um caminhao vai sair do terminal e existem mais encomendas
esperando do que cabem nele. Cada encomenda tem:
  - peso (kg), volume (litros) e valor da mercadoria (R$)  -> os 3 limites
  - valor do frete que ela paga (R$)                       -> o "lucro"

O frete segue a logica usada pelas transportadoras:
  peso taxado = o MAIOR entre o peso real e o peso cubado
  peso cubado = volume em m3 x fator de cubagem (300 kg/m3)
  frete       = peso taxado x tarifa por kg + 0,5% do valor da mercadoria
                (com frete minimo de R$ 50)

Saidas (na pasta instancias/frete):
  freteXX.dat  -> o problema no mesmo formato das outras instancias
  freteXX.csv  -> a lista de encomendas, para mostrar no TCC
"""
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

import config as cfg

PASTA = Path(__file__).resolve().parent / "instancias" / "frete"


def gerar_encomendas(quantidade, rng):
    # peso: muitas encomendas leves e poucas pesadas (distribuicao log-normal)
    peso = np.clip(rng.lognormal(mean=np.log(120), sigma=0.8, size=quantidade), 5, 1500)
    # densidade: de cargas leves e volumosas (60 kg/m3) a densas (700 kg/m3)
    densidade = rng.uniform(60, 700, quantidade)
    volume_m3 = peso / densidade
    # valor da mercadoria por kg: de R$ 8 (materiais) a R$ 250 (eletronicos)
    valor_por_kg = np.exp(rng.uniform(np.log(8), np.log(250), quantidade))
    valor_mercadoria = peso * valor_por_kg
    # tarifa por kg depende da distancia do destino
    tarifa = rng.uniform(0.35, 1.10, quantidade)

    peso_cubado = volume_m3 * cfg.FATOR_CUBAGEM
    peso_taxado = np.maximum(peso, peso_cubado)
    frete = np.maximum(50, peso_taxado * tarifa + 0.005 * valor_mercadoria)

    return {
        "peso_kg": np.round(peso).astype(int),
        "volume_litros": np.round(volume_m3 * 1000).astype(int),
        "valor_mercadoria_reais": np.round(valor_mercadoria).astype(int),
        "peso_cubado_kg": np.round(peso_cubado).astype(int),
        "peso_taxado_kg": np.round(peso_taxado).astype(int),
        "tarifa_reais_kg": np.round(tarifa, 2),
        "frete_reais": np.round(frete).astype(int),
    }


def otimo_exato(lucros, pesos, capacidades, limite_s=300):
    """Tenta achar o otimo com um resolvedor exato (programacao inteira)."""
    res = milp(
        c=-lucros,
        constraints=LinearConstraint(pesos, -np.inf, capacidades),
        integrality=np.ones_like(lucros),
        bounds=Bounds(0, 1),
        options={"time_limit": limite_s},
    )
    if res.status == 0:  # 0 = otimo comprovado
        return int(round(-res.fun))
    return 0


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    capacidades = np.array([cfg.CAMINHAO_PESO_KG, cfg.CAMINHAO_VOLUME_LITROS,
                            cfg.CAMINHAO_SEGURO_REAIS])
    for nome, caminho in cfg.GRUPO_FRETE.items():
        quantidade = int("".join(ch for ch in nome if ch.isdigit()))
        rng = np.random.default_rng(cfg.SEMENTE_FRETE + quantidade)
        enc = gerar_encomendas(quantidade, rng)

        lucros = enc["frete_reais"]
        pesos = np.vstack([enc["peso_kg"], enc["volume_litros"],
                           enc["valor_mercadoria_reais"]])
        print(f"{nome}: {quantidade} encomendas | demanda / capacidade do caminhao: "
              f"peso {pesos[0].sum() / capacidades[0]:.1f}x, "
              f"volume {pesos[1].sum() / capacidades[1]:.1f}x, "
              f"seguro {pesos[2].sum() / capacidades[2]:.1f}x")
        print("   procurando o otimo exato (pode levar alguns minutos)...")
        otimo = otimo_exato(lucros, pesos, capacidades)
        print(f"   otimo: R$ {otimo:,}" if otimo else "   otimo nao comprovado no tempo limite")

        linhas = [f"{quantidade} 3 {otimo}", " ".join(map(str, lucros))]
        linhas += [" ".join(map(str, linha)) for linha in pesos]
        linhas.append(" ".join(map(str, capacidades)))
        (PASTA.parent.parent / caminho).write_text("\n".join(linhas) + "\n")

        cabecalho = "encomenda;" + ";".join(enc.keys())
        csv = [cabecalho] + [
            f"{i + 1};" + ";".join(str(enc[k][i]).replace(".", ",") for k in enc)
            for i in range(quantidade)
        ]
        (PASTA / f"{nome.lower()}.csv").write_text("\n".join(csv) + "\n", encoding="utf-8-sig")
    print("\nCenarios gerados em instancias/frete")


if __name__ == "__main__":
    main()
