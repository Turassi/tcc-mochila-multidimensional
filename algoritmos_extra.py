"""
Algoritmos extras do Laboratorio (alem do AG e da EDB do TCC).

REGRAS IGUAIS PARA TODOS (a "corrida justa"):
  - mesmo avaliador e mesmo reparo (algoritmos.Avaliador);
  - mesma populacao inicial (mesma semente => mesmas 100 solucoes);
  - mesmo orcamento de avaliacoes (tentativas). Quando acaba, o algoritmo para.

Os algoritmos que trabalham com numeros "quebrados" (GWO, Jaya, Quati)
guardam uma posicao entre 0 e 1 para cada item. Para avaliar, a regra e:
posicao > 0,5 -> o item vai (1); senao, fica (0).
"""
import time
from types import SimpleNamespace

import numpy as np

from algoritmos import (Avaliador, algoritmo_genetico, evolucao_diferencial_binaria,
                        populacao_inicial)


class OrcamentoEsgotado(Exception):
    """Avisa que as tentativas acabaram."""


class AvaliadorLimitado(Avaliador):
    def __init__(self, inst, rng, otimo, intervalo, limite):
        super().__init__(inst, rng, otimo, intervalo)
        self.limite = limite

    def avaliar(self, x):
        if self.avaliacoes >= self.limite:
            raise OrcamentoEsgotado
        return super().avaliar(x)


def _inicio_comum(inst, semente, p):
    """Mesma populacao inicial do AG e da EDB (mesmas chamadas ao sorteio)."""
    rng = np.random.default_rng(semente)
    av = AvaliadorLimitado(inst, rng, inst.otimo, p.intervalo, p.orcamento)
    pop = populacao_inicial(inst.n, p.populacao, rng)
    apt = np.array([av.avaliar(ind) for ind in pop], dtype=np.int64)
    return rng, av, pop, apt


def _posicoes_de(bits, rng):
    """Cria posicoes continuas coerentes com os bits (1 -> acima de 0,5)."""
    return np.where(bits == 1, rng.uniform(0.5, 1.0, bits.shape), rng.uniform(0.0, 0.5, bits.shape))


def _avaliar_posicao(av, x, rng):
    """Converte posicao em bits, avalia (com reparo) e corrige a posicao."""
    bits = (x > 0.5).astype(np.int8)
    valor = av.avaliar(bits)
    tirados = (bits == 0) & (x > 0.5)          # itens que o reparo removeu
    x[tirados] = rng.uniform(0.0, 0.5, int(tirados.sum()))
    return valor


# =====================================================================
# 1) ENXAME DE PARTICULAS BINARIO - Kennedy e Eberhart (1997)
# =====================================================================
def pso_binario(inst, semente, p):
    inicio = time.perf_counter()
    rng, av, pos, apt = _inicio_comum(inst, semente, p)
    tam, n = pos.shape
    vel = rng.uniform(-p.pso_vmax, p.pso_vmax, (tam, n))
    pbest, pbest_apt = pos.copy(), apt.copy()
    g = int(np.argmax(pbest_apt))
    try:
        while True:
            for i in range(tam):
                r1, r2 = rng.random(n), rng.random(n)
                vel[i] = (p.pso_inercia * vel[i]
                          + p.pso_c1 * r1 * (pbest[i] - pos[i])
                          + p.pso_c2 * r2 * (pbest[g] - pos[i]))
                np.clip(vel[i], -p.pso_vmax, p.pso_vmax, out=vel[i])
                # funcao sigmoide: velocidade alta -> chance alta de ser 1
                pos[i] = (rng.random(n) < 1 / (1 + np.exp(-vel[i]))).astype(np.int8)
                valor = av.avaliar(pos[i])
                if valor > pbest_apt[i]:
                    pbest[i], pbest_apt[i] = pos[i], valor
                    if valor > pbest_apt[g]:
                        g = i
    except OrcamentoEsgotado:
        pass
    return av.resultado(inicio)


# =====================================================================
# 2) SISTEMA DE FORMIGAS BINARIO - adaptado de Kong, Tian e Kao (2008)
# =====================================================================
def formigas_binario(inst, semente, p):
    inicio = time.perf_counter()
    rng, av, pop, apt = _inicio_comum(inst, semente, p)
    tam, n = pop.shape
    feromonio = np.full(n, 0.5)               # chance de cada item ser escolhido
    melhor_global = pop[np.argmax(apt)].copy()
    melhor_iter = melhor_global.copy()
    try:
        while True:
            # deposito: as melhores solucoes reforcam os itens que escolheram
            alvo = 0.5 * melhor_iter + 0.5 * melhor_global
            feromonio = (1 - p.aco_evaporacao) * feromonio + p.aco_evaporacao * alvo
            np.clip(feromonio, p.aco_min, 1 - p.aco_min, out=feromonio)
            # se tudo ficou "decidido" demais, reinicia o feromonio
            if np.mean(np.abs(feromonio - 0.5)) * 2 > p.aco_convergencia:
                feromonio[:] = 0.5
            melhor_valor_iter, melhor_iter = -1, None
            for _ in range(tam):
                formiga = (rng.random(n) < feromonio).astype(np.int8)
                valor = av.avaliar(formiga)
                if valor > melhor_valor_iter:
                    melhor_valor_iter, melhor_iter = valor, formiga
            if av.melhor_solucao is not None:
                melhor_global = av.melhor_solucao.copy()
    except OrcamentoEsgotado:
        pass
    return av.resultado(inicio)


# =====================================================================
# 3) TEMPERA SIMULADA (Simulated Annealing) - Kirkpatrick et al. (1983)
# =====================================================================
def tempera_simulada(inst, semente, p):
    inicio = time.perf_counter()
    rng, av, pop, apt = _inicio_comum(inst, semente, p)
    n = inst.n
    atual = pop[np.argmax(apt)].copy()        # comeca da melhor inicial
    valor_atual = int(apt.max())
    t0 = p.sa_temp_inicial * inst.lucros.mean()
    restantes = max(1, p.orcamento - av.avaliacoes)
    resfriamento = (p.sa_temp_final / p.sa_temp_inicial) ** (1 / restantes)
    temperatura = t0
    try:
        while True:
            vizinho = atual.copy()
            j = int(rng.integers(0, n))
            vizinho[j] = 1 - vizinho[j]       # troca um item (entra ou sai)
            valor = av.avaliar(vizinho)
            piora = valor_atual - valor
            # aceita se melhorou; se piorou, aceita com uma chance que cai com o tempo
            if piora <= 0 or rng.random() < np.exp(-piora / temperatura):
                atual, valor_atual = vizinho, valor
            temperatura *= resfriamento
    except OrcamentoEsgotado:
        pass
    return av.resultado(inicio)


# =====================================================================
# 4) LOBO CINZENTO (Grey Wolf Optimizer) - Mirjalili et al. (2014)
# =====================================================================
def lobo_cinzento(inst, semente, p):
    inicio = time.perf_counter()
    rng, av, pop, apt = _inicio_comum(inst, semente, p)
    tam, n = pop.shape
    x = _posicoes_de(pop, rng)
    apt = apt.astype(float)
    try:
        while True:
            ordem = np.argsort(-apt)
            alfa, beta, delta = x[ordem[0]].copy(), x[ordem[1]].copy(), x[ordem[2]].copy()
            a = 2 - 2 * min(1.0, av.avaliacoes / p.orcamento)   # cai de 2 para 0
            for i in range(tam):
                novos = []
                for lider in (alfa, beta, delta):
                    A = 2 * a * rng.random(n) - a
                    C = 2 * rng.random(n)
                    novos.append(lider - A * np.abs(C * lider - x[i]))
                x[i] = np.clip(sum(novos) / 3, 0, 1)
                apt[i] = _avaliar_posicao(av, x[i], rng)
    except OrcamentoEsgotado:
        pass
    return av.resultado(inicio)


# =====================================================================
# 5) JAYA - Rao (2016): "sem parametros"
# =====================================================================
def jaya(inst, semente, p):
    inicio = time.perf_counter()
    rng, av, pop, apt = _inicio_comum(inst, semente, p)
    tam, n = pop.shape
    x = _posicoes_de(pop, rng)
    try:
        while True:
            melhor, pior = x[np.argmax(apt)].copy(), x[np.argmin(apt)].copy()
            for i in range(tam):
                # vai na direcao do melhor e foge do pior
                novo = x[i] + rng.random(n) * (melhor - x[i]) - rng.random(n) * (pior - x[i])
                novo = np.clip(novo, 0, 1)
                valor = _avaliar_posicao(av, novo, rng)
                if valor > apt[i]:
                    x[i], apt[i] = novo, valor
    except OrcamentoEsgotado:
        pass
    return av.resultado(inicio)


# =====================================================================
# 6) QUATI (Coati Optimization Algorithm) - Dehghani et al. (2023)
#    Implementado conforme a versao de referencia da biblioteca mealpy.
# =====================================================================
def quati(inst, semente, p):
    inicio = time.perf_counter()
    rng, av, pop, apt = _inicio_comum(inst, semente, p)
    tam, n = pop.shape
    x = _posicoes_de(pop, rng)
    iteracao = 0
    try:
        while True:
            iteracao += 1
            metade = tam // 2
            melhor = x[np.argmax(apt)].copy()       # a "iguana" na arvore
            # Fase 1 (exploracao): metade ataca a iguana na arvore...
            for i in range(metade):
                novo = np.clip(x[i] + rng.random() * (melhor - rng.integers(1, 3) * x[i]), 0, 1)
                valor = _avaliar_posicao(av, novo, rng)
                if valor > apt[i]:
                    x[i], apt[i] = novo, valor
            # ...e a outra metade caca uma iguana que caiu num lugar aleatorio
            for i in range(metade, tam):
                iguana = rng.random(n)
                valor_iguana = _avaliar_posicao(av, iguana, rng)
                if valor_iguana > apt[i]:
                    novo = x[i] + rng.random() * (iguana - rng.integers(1, 3) * x[i])
                else:
                    novo = x[i] + rng.random() * (x[i] - iguana)
                novo = np.clip(novo, 0, 1)
                valor = _avaliar_posicao(av, novo, rng)
                if valor > apt[i]:
                    x[i], apt[i] = novo, valor
            # Fase 2 (refinamento): pequenos passos, cada vez menores
            alcance = 1.0 / iteracao
            for i in range(tam):
                novo = np.clip(x[i] + (1 - 2 * rng.random()) * (rng.random() * alcance), 0, 1)
                valor = _avaliar_posicao(av, novo, rng)
                if valor > apt[i]:
                    x[i], apt[i] = novo, valor
    except OrcamentoEsgotado:
        pass
    return av.resultado(inicio)


# =====================================================================
# AG e EDB do TCC, adaptados para aceitar outro orcamento
# =====================================================================
def _cfg_classico(p):
    return SimpleNamespace(
        TAMANHO_POPULACAO=p.populacao,
        GERACOES=max(1, (p.orcamento - p.populacao) // p.populacao),
        INTERVALO_HISTORICO=p.intervalo,
        AG_TAMANHO_TORNEIO=p.ag_torneio, AG_TAXA_CRUZAMENTO=p.ag_cruzamento,
        AG_TAXA_MUTACAO=p.ag_mutacao, AG_ELITISMO=True,
        ED_TAXA_PERTURBACAO=p.ed_perturbacao, ED_TAXA_MUTACAO=p.ed_mutacao,
    )


def ag(inst, semente, p):
    return algoritmo_genetico(inst, semente, _cfg_classico(p), inst.otimo)


def edb(inst, semente, p):
    return evolucao_diferencial_binaria(inst, semente, _cfg_classico(p), inst.otimo)


def parametros_padrao(orcamento=100_100, populacao=100):
    """Valores usados quando o usuario nao muda nada (todos da literatura)."""
    return SimpleNamespace(
        orcamento=orcamento, populacao=populacao,
        intervalo=max(100, orcamento // 100),
        ag_torneio=3, ag_cruzamento=0.80, ag_mutacao=0.05,        # Andre e Parpinelli (2015)
        ed_perturbacao=0.50, ed_mutacao=0.05,                     # Andre e Parpinelli (2015)
        pso_c1=2.0, pso_c2=2.0, pso_vmax=4.0, pso_inercia=1.0,    # Kennedy e Eberhart (1997)
        aco_evaporacao=0.10, aco_min=0.01, aco_convergencia=0.95,
        sa_temp_inicial=1.0, sa_temp_final=0.001,
    )


# Catalogo mostrado na interface
CATALOGO = {
    "AG": {"funcao": ag, "nome": "Algoritmo Genético", "ano": 1975, "familia": "Evolutivo",
           "tipo": "TCC", "referencia": "Holland (1975); versão de André e Parpinelli (2015)",
           "resumo": "Cruza as melhores soluções (pais) para gerar filhos, com pequenas mutações."},
    "EDB": {"funcao": edb, "nome": "Evolução Diferencial Binária", "ano": 1997, "familia": "Evolutivo",
            "tipo": "TCC", "referencia": "Storn e Price (1997); Krause et al. (2012)",
            "resumo": "Cada solução tenta melhorar copiando partes de um colega; só troca se melhorar."},
    "PSO": {"funcao": pso_binario, "nome": "Enxame de Partículas Binário (PSO)", "ano": 1997,
            "familia": "Enxame", "tipo": "Clássico", "referencia": "Kennedy e Eberhart (1997)",
            "resumo": "Partículas 'voam' em direção à melhor posição própria e à melhor do grupo."},
    "ACO": {"funcao": formigas_binario, "nome": "Colônia de Formigas Binária", "ano": 2008,
            "familia": "Enxame", "tipo": "Clássico", "referencia": "Adaptado de Kong, Tian e Kao (2008)",
            "resumo": "As melhores soluções deixam 'feromônio' nos itens; as próximas formigas seguem o rastro."},
    "SA": {"funcao": tempera_simulada, "nome": "Têmpera Simulada (Simulated Annealing)", "ano": 1983,
           "familia": "Trajetória", "tipo": "Clássico", "referencia": "Kirkpatrick, Gelatt e Vecchi (1983)",
           "resumo": "Uma única solução troca um item por vez; no começo aceita pioras, depois só melhoras."},
    "GWO": {"funcao": lobo_cinzento, "nome": "Lobo Cinzento (Grey Wolf Optimizer)", "ano": 2014,
            "familia": "Metáfora recente", "tipo": "Recente", "referencia": "Mirjalili, Mirjalili e Lewis (2014)",
            "resumo": "A matilha se move guiada pelos três melhores lobos (alfa, beta e delta)."},
    "JAYA": {"funcao": jaya, "nome": "Jaya", "ano": 2016, "familia": "Sem metáfora", "tipo": "Recente",
             "referencia": "Rao (2016)",
             "resumo": "Cada solução se aproxima da melhor e se afasta da pior. Não tem parâmetros para ajustar."},
    "QUATI": {"funcao": quati, "nome": "Quati (Coati Optimization Algorithm)", "ano": 2023,
              "familia": "Metáfora recente", "tipo": "Recente",
              "referencia": "Dehghani, Montazeri, Trojovská e Trojovský (2023)",
              "resumo": "Imita quatis caçando iguanas e fugindo de predadores. Pouco testado e com "
                        "questionamentos na literatura: ótimo candidato para 'validar'."},
}
