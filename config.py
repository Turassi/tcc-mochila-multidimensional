# =====================================================================
#  CONFIGURACAO DO EXPERIMENTO
#  Todos os parametros ficam aqui. Se quiser mudar alguma coisa,
#  mude SO neste arquivo.
# =====================================================================

# ---------------------------------------------------------------------
# 1) PARAMETROS IGUAIS PARA OS DOIS ALGORITMOS (a "corrida justa")
# ---------------------------------------------------------------------

# Quantas solucoes (filas de 0 e 1) existem ao mesmo tempo.
TAMANHO_POPULACAO = 100

# Quantas rodadas (geracoes) cada algoritmo executa.
GERACOES = 1000

# Total de tentativas = populacao inicial + populacao x geracoes
# = 100 + 100 x 1000 = 100.100 (igual ao artigo de Andre e Parpinelli)
ORCAMENTO_AVALIACOES = TAMANHO_POPULACAO * (GERACOES + 1)

# Quantas vezes cada algoritmo roda em cada instancia.
EXECUCOES = 30

# Semente inicial. A execucao 1 usa SEMENTE_BASE + 1, a 2 usa + 2...
# Os dois algoritmos usam as MESMAS sementes, entao comecam com a
# MESMA populacao inicial (mais justo ainda).
SEMENTE_BASE = 2026

# De quantas em quantas tentativas o programa anota o melhor valor
# (serve para o grafico de convergencia).
INTERVALO_HISTORICO = 1000

# ---------------------------------------------------------------------
# 2) PARAMETROS DO ALGORITMO GENETICO (valores de Andre e Parpinelli)
# ---------------------------------------------------------------------
AG_TAMANHO_TORNEIO = 3        # quantos competem para virar pai
AG_TAXA_CRUZAMENTO = 0.80     # chance de misturar os dois pais (80%)
AG_TAXA_MUTACAO = 0.05        # chance de virar cada 0/1 do filho (5%)
AG_ELITISMO = True            # a melhor solucao passa direto adiante

# ---------------------------------------------------------------------
# 3) PARAMETROS DA EVOLUCAO DIFERENCIAL BINARIA (Andre e Parpinelli)
# ---------------------------------------------------------------------
ED_TAXA_PERTURBACAO = 0.50    # chance de mexer em cada posicao (50%)
ED_TAXA_MUTACAO = 0.05        # dentre as mexidas: chance de virar 0/1 (5%)
                              # (nas outras 95%, copia do colega)

# ---------------------------------------------------------------------
# 4) INSTANCIAS (os "problemas de teste")
# ---------------------------------------------------------------------
# Grupo 1: as 11 instancias do artigo, com valor otimo conhecido.
GRUPO_1 = {
    "PB1": "instancias/grupo1/pb1.dat",
    "PB2": "instancias/grupo1/pb2.dat",
    "PB4": "instancias/grupo1/pb4.dat",
    "PB5": "instancias/grupo1/pb5.dat",
    "PB6": "instancias/grupo1/pb6.dat",
    "PB7": "instancias/grupo1/pb7.dat",
    "PET7": "instancias/grupo1/pet7.dat",
    "SENTO1": "instancias/grupo1/sento1.dat",
    "SENTO2": "instancias/grupo1/sento2.dat",
    "WEING8": "instancias/grupo1/weing8.dat",
    "WEISH30": "instancias/grupo1/weish30.dat",
}

# Grupo 2: instancias maiores de Chu e Beasley (1998).
# Nome = limites x itens. Ex.: OR10x250 = 10 limites e 250 itens.
GRUPO_2 = {
    "OR5x100": "instancias/grupo2/OR5x100-0.25_1.dat",
    "OR5x250": "instancias/grupo2/OR5x250-0.25_1.dat",
    "OR5x500": "instancias/grupo2/OR5x500-0.25_1.dat",
    "OR10x100": "instancias/grupo2/OR10x100-0.25_1.dat",
    "OR10x250": "instancias/grupo2/OR10x250-0.25_1.dat",
    "OR10x500": "instancias/grupo2/OR10x500-0.25_1.dat",
    "OR30x100": "instancias/grupo2/OR30x100-0.25_1.dat",
    "OR30x250": "instancias/grupo2/OR30x250-0.25_1.dat",
    "OR30x500": "instancias/grupo2/OR30x500-0.25_1.dat",
}

# Grupo 3: cenarios ficticios de frete fracionado (gerados por
# gerar_frete.py). Numero = quantas encomendas esperam o caminhao.
GRUPO_FRETE = {
    "FRETE80": "instancias/frete/frete80.dat",
    "FRETE120": "instancias/frete/frete120.dat",
    "FRETE160": "instancias/frete/frete160.dat",
}

# ---------------------------------------------------------------------
# 5) CENARIO DE FRETE FRACIONADO (ficticio, mas com numeros realistas)
# ---------------------------------------------------------------------
CAMINHAO_PESO_KG = 12000          # limite de peso do caminhao
CAMINHAO_VOLUME_LITROS = 48000    # bau de 48 m3 (1 m3 = 1000 litros)
CAMINHAO_SEGURO_REAIS = 600000    # valor maximo de mercadoria segurado
FATOR_CUBAGEM = 300               # kg por m3 (padrao rodoviario no Brasil)
SEMENTE_FRETE = 7                 # para gerar sempre as mesmas encomendas

# ---------------------------------------------------------------------
# 6) TESTE ESTATISTICO
# ---------------------------------------------------------------------
NIVEL_SIGNIFICANCIA = 0.05        # 5%
