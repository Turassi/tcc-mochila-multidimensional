"""
Leitura das instancias (os "problemas de teste").

Formato dos arquivos .dat (todos os numeros separados por espaco):
    n  m  otimo                  -> itens, limites, valor otimo (0 = desconhecido)
    p1 p2 ... pn                 -> valor (lucro) de cada item
    w11 w12 ... w1n              -> quanto cada item "gasta" do limite 1
    ...                          -> (uma linha para cada limite)
    wm1 wm2 ... wmn              -> quanto cada item "gasta" do limite m
    c1 c2 ... cm                 -> tamanho de cada limite (capacidades)
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

PASTA_PROJETO = Path(__file__).resolve().parent


@dataclass
class Instancia:
    nome: str
    grupo: str
    n: int                    # numero de itens
    m: int                    # numero de limites (dimensoes)
    lucros: np.ndarray        # valor de cada item
    pesos: np.ndarray         # matriz m x n
    capacidades: np.ndarray   # tamanho de cada limite
    otimo: int | None = None  # melhor resposta possivel (se conhecida)
    _limitante_pl: float | None = field(default=None, repr=False)

    def limitante_pl(self) -> float:
        """
        Limite superior pela "relaxacao linear": resolve o problema
        deixando levar PEDACOS de itens (ex.: meio notebook). Nenhuma
        resposta real consegue passar desse valor, entao ele serve de
        regua quando o otimo nao e conhecido (igual a Chu e Beasley, 1998).
        """
        if self._limitante_pl is None:
            res = linprog(
                c=-self.lucros.astype(float),
                A_ub=self.pesos.astype(float),
                b_ub=self.capacidades.astype(float),
                bounds=(0, 1),
                method="highs",
            )
            self._limitante_pl = float(-res.fun)
        return self._limitante_pl

    def referencia(self) -> tuple[float, str]:
        """Valor usado para calcular o gap: o otimo, se existir."""
        if self.otimo:
            return float(self.otimo), "otimo"
        return self.limitante_pl(), "limitante PL"


def ler_instancia(caminho: str, nome: str, grupo: str) -> Instancia:
    texto = (PASTA_PROJETO / caminho).read_text()
    numeros = [int(float(t)) for t in texto.split()]
    n, m, otimo = numeros[0], numeros[1], numeros[2]
    pos = 3
    lucros = np.array(numeros[pos:pos + n], dtype=np.int64)
    pos += n
    pesos = np.array(numeros[pos:pos + m * n], dtype=np.int64).reshape(m, n)
    pos += m * n
    capacidades = np.array(numeros[pos:pos + m], dtype=np.int64)
    if len(lucros) != n or len(capacidades) != m:
        raise ValueError(f"Arquivo {caminho} parece incompleto.")
    return Instancia(nome, grupo, n, m, lucros, pesos, capacidades,
                     otimo if otimo > 0 else None)


def carregar_todas(grupos: dict[str, dict[str, str]]) -> list[Instancia]:
    """grupos = {"Grupo 1": {"PB1": "caminho", ...}, ...}"""
    lista = []
    for grupo, arquivos in grupos.items():
        for nome, caminho in arquivos.items():
            if not (PASTA_PROJETO / caminho).exists():
                print(f"  [aviso] {caminho} nao encontrado, pulando {nome}.")
                continue
            lista.append(ler_instancia(caminho, nome, grupo))
    return lista
