"""
Os dois algoritmos comparados no TCC, seguindo o pseudocodigo de
Andre e Parpinelli (2015), Algoritmos 1 e 2.

Uma "solucao" e uma fila de 0 e 1 (um numero por item):
    1 = o item vai no caminhao, 0 = o item fica.
"""
import time

import numpy as np


class Avaliador:
    """
    Faz tres coisas a cada tentativa:
      1. conserta a solucao se ela estourar algum limite (reparo);
      2. calcula o valor total dos itens escolhidos;
      3. conta as tentativas e anota o historico do melhor valor.
    Os DOIS algoritmos usam este mesmo avaliador, entao a regra e igual.
    """

    def __init__(self, inst, rng, otimo=None, intervalo_historico=1000):
        self.lucros = inst.lucros
        self.pesos = inst.pesos
        self.capacidades = inst.capacidades
        self.rng = rng
        self.otimo = otimo
        self.intervalo = intervalo_historico
        self.avaliacoes = 0
        self.melhor_valor = -1
        self.melhor_solucao = None
        self.avaliacoes_ate_otimo = None
        self.historico = []  # lista de (tentativas, melhor valor ate ali)

    def reparar(self, x):
        """
        Reparo de Andre e Parpinelli: enquanto algum limite estiver
        estourado, tira do caminhao um item escolhido ao acaso.
        """
        carga = self.pesos @ x
        if np.all(carga <= self.capacidades):
            return
        escolhidos = np.flatnonzero(x)
        self.rng.shuffle(escolhidos)
        for j in escolhidos:
            x[j] = 0
            carga -= self.pesos[:, j]
            if np.all(carga <= self.capacidades):
                return

    def avaliar(self, x):
        self.reparar(x)
        valor = int(self.lucros @ x)
        self.avaliacoes += 1
        if valor > self.melhor_valor:
            self.melhor_valor = valor
            self.melhor_solucao = x.copy()
            if (self.otimo is not None and valor >= self.otimo
                    and self.avaliacoes_ate_otimo is None):
                self.avaliacoes_ate_otimo = self.avaliacoes
        if self.avaliacoes % self.intervalo == 0:
            self.historico.append((self.avaliacoes, self.melhor_valor))
        return valor

    def resultado(self, inicio):
        if not self.historico or self.historico[-1][0] != self.avaliacoes:
            self.historico.append((self.avaliacoes, self.melhor_valor))
        return {
            "melhor_valor": self.melhor_valor,
            "melhor_solucao": "".join(map(str, self.melhor_solucao.tolist())),
            "avaliacoes": self.avaliacoes,
            "avaliacoes_ate_otimo": self.avaliacoes_ate_otimo,
            "tempo_s": time.perf_counter() - inicio,
            "historico": self.historico,
        }


def populacao_inicial(n, tamanho, rng):
    """Chutes aleatorios: cada item tem 50% de chance de comecar no caminhao."""
    return (rng.random((tamanho, n)) < 0.5).astype(np.int8)


# =====================================================================
# ALGORITMO GENETICO (Andre e Parpinelli, 2015 - Algoritmo 2)
# =====================================================================
def algoritmo_genetico(inst, semente, cfg, otimo=None):
    inicio = time.perf_counter()
    rng = np.random.default_rng(semente)
    av = Avaliador(inst, rng, otimo, cfg.INTERVALO_HISTORICO)
    tam, n = cfg.TAMANHO_POPULACAO, inst.n

    pop = populacao_inicial(n, tam, rng)
    aptidao = np.array([av.avaliar(ind) for ind in pop])

    def torneio(evitar=None):
        # sorteia alguns competidores e devolve o melhor deles
        while True:
            competidores = rng.integers(0, tam, cfg.AG_TAMANHO_TORNEIO)
            vencedor = competidores[np.argmax(aptidao[competidores])]
            if vencedor != evitar:
                return vencedor

    for _ in range(cfg.GERACOES):
        indice_elite = int(np.argmax(aptidao))
        elite, aptidao_elite = pop[indice_elite].copy(), aptidao[indice_elite]

        filhos = np.empty_like(pop)
        aptidao_filhos = np.empty(tam, dtype=np.int64)

        for i in range(0, tam, 2):
            pai1 = torneio()
            pai2 = torneio(evitar=pai1)
            filho_a, filho_b = pop[pai1].copy(), pop[pai2].copy()

            # CRUZAMENTO UNIFORME: cada posicao vem de um pai ou do outro
            if rng.random() < cfg.AG_TAXA_CRUZAMENTO:
                mascara = rng.random(n) < 0.5
                filho_a = np.where(mascara, pop[pai2], pop[pai1])
                filho_b = np.where(mascara, pop[pai1], pop[pai2])

            for indice, filho in ((i, filho_a), (i + 1, filho_b)):
                if indice >= tam:
                    break
                # MUTACAO: vira alguns 0/1 ao acaso
                vira = rng.random(n) < cfg.AG_TAXA_MUTACAO
                filho[vira] = 1 - filho[vira]
                aptidao_filhos[indice] = av.avaliar(filho)
                filhos[indice] = filho

        # ELITISMO: a melhor solucao antiga entra no lugar do pior filho
        if cfg.AG_ELITISMO:
            pior = int(np.argmin(aptidao_filhos))
            filhos[pior], aptidao_filhos[pior] = elite, aptidao_elite

        pop, aptidao = filhos, aptidao_filhos

    return av.resultado(inicio)


# =====================================================================
# EVOLUCAO DIFERENCIAL BINARIA (Andre e Parpinelli, 2015 - Algoritmo 1)
# =====================================================================
def evolucao_diferencial_binaria(inst, semente, cfg, otimo=None):
    inicio = time.perf_counter()
    rng = np.random.default_rng(semente)
    av = Avaliador(inst, rng, otimo, cfg.INTERVALO_HISTORICO)
    tam, n = cfg.TAMANHO_POPULACAO, inst.n

    pop = populacao_inicial(n, tam, rng)
    aptidao = np.array([av.avaliar(ind) for ind in pop])

    for _ in range(cfg.GERACOES):
        for i in range(tam):
            # sorteia um "colega" k diferente de i e uma posicao obrigatoria
            k = int(rng.integers(0, tam - 1))
            if k >= i:
                k += 1
            j_obrigatoria = int(rng.integers(0, n))

            copia = pop[i].copy()
            mexer = rng.random(n) < cfg.ED_TAXA_PERTURBACAO
            mexer[j_obrigatoria] = True          # mexe em pelo menos 1 posicao
            mutar = rng.random(n) < cfg.ED_TAXA_MUTACAO

            copiar_do_colega = mexer & ~mutar     # CRUZAMENTO
            copia[copiar_do_colega] = pop[k][copiar_do_colega]
            virar = mexer & mutar                 # MUTACAO
            copia[virar] = 1 - copia[virar]

            # SELECAO GULOSA: so troca se a copia for melhor
            valor = av.avaliar(copia)
            if valor > aptidao[i]:
                pop[i], aptidao[i] = copia, valor

    return av.resultado(inicio)


ALGORITMOS = {
    "AG": algoritmo_genetico,
    "EDB": evolucao_diferencial_binaria,
}
NOMES_COMPLETOS = {
    "AG": "Algoritmo Genetico",
    "EDB": "Evolucao Diferencial Binaria",
}
