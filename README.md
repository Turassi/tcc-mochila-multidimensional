# Metaheurísticas clássicas e recentes no Problema da Mochila Multidimensional

Código-fonte do Trabalho de Conclusão de Curso **"Metaheurísticas clássicas e recentes no Problema da Mochila Multidimensional: estudo comparativo aplicado ao frete fracionado"**.

- **Autor:** Christian Leão Turassi
- **Orientador:** Prof. Leanderson André
- **Curso:** Bacharelado em Engenharia de Software – Universidade da Região de Joinville (Univille)

## Sobre o trabalho

O trabalho compara três metaheurísticas no **Problema da Mochila Multidimensional 0-1**, que modela a escolha de quais encomendas embarcar em um veículo no **frete fracionado** (respeitando peso, volume e valor segurado):

| Algoritmo | Ano | Papel no estudo |
|---|---|---|
| Algoritmo Genético (AG) | 1975 | Clássico |
| Evolução Diferencial Binária (EDB) | 1997 | Consolidado |
| Algoritmo do Quati (*Coati Optimization Algorithm*, COA) | 2023 | Recente |

Os três algoritmos usam o mesmo orçamento de 100.100 avaliações, o mesmo operador de reparo e a mesma população inicial, em 23 instâncias e 100 execuções por instância.

### Principais resultados

| Métrica | AG | EDB | COA |
|---|---|---|---|
| Gap médio (23 instâncias) | 6,54% | **2,54%** | 10,11% |
| Ranking médio (1 = melhor) | 2,00 | **1,04** | 2,96 |
| Frete obtido em relação ao ótimo | 96,05% | **99,29%** | 93,99% |

O teste de Friedman e os testes de Wilcoxon com correção de Holm indicaram diferença significativa entre os três algoritmos (p < 0,001).

## Como executar (Windows)

Requisito: **Python 3.10 ou superior** ([python.org](https://www.python.org/downloads/)), instalado com a opção *Add python.exe to PATH*.

| Arquivo | O que faz |
|---|---|
| `1_instalar.bat` | Instala as bibliotecas (apenas uma vez) |
| `2_rodar_experimento.bat` | Experimento do protocolo inicial (AG x EDB, 30 execuções) |
| `3_gerar_analise.bat` | Tabelas, testes estatísticos e gráficos do protocolo inicial |
| `4_abrir_laboratorio.bat` | Interface gráfica (usada nos resultados do artigo) |

Em outros sistemas: `pip install -r requirements.txt` e depois `python laboratorio.py`.

### Reproduzir os resultados do artigo

1. Abra o `4_abrir_laboratorio.bat`.
2. Aba **1. Algoritmos**: marque Algoritmo Genético, Evolução Diferencial Binária e Quati.
3. Aba **2. Problemas**: clique em **Conjunto do TCC (23)**.
4. Aba **3. Rodar**: 100 execuções e **100.100 tentativas**; clique em **Rodar experimento**.
5. Aba **4. Resultados**: ranking, testes estatísticos, gráficos e exportação para Excel.

As sementes aleatórias são fixas (2026 + número da execução), então os resultados são idênticos em qualquer computador.

## Laboratório

A interface gráfica também permite, de forma exploratória:

- comparar até 8 algoritmos (AG, EDB, PSO, Colônia de Formigas, Têmpera Simulada, Lobo Cinzento, Jaya e Quati);
- escolher instâncias, usar conjuntos recomendados ou gerar instâncias aleatórias;
- ver os detalhes de cada instância (valores, pesos, capacidades e correlação);
- obter ranking, teste de Friedman, pós-teste de Holm, gráficos e planilhas.

## Instâncias

| Grupo | Quantidade | Origem |
|---|---|---|
| Grupo 1 | 11 | OR-Library (conjunto SAC-94), com ótimo conhecido |
| Grupo 2 | 9 | Chu e Beasley (1998), de 100 a 500 itens |
| Frete | 3 | Cenários fictícios de frete fracionado, gerados por `gerar_frete.py` |

Detalhes em [`instancias/FONTES.txt`](instancias/FONTES.txt).

## Estrutura do código

| Arquivo | Conteúdo |
|---|---|
| `config.py` | Parâmetros do experimento |
| `algoritmos.py` | AG, EDB, avaliador e operador de reparo |
| `algoritmos_extra.py` | Algoritmos adicionais do laboratório |
| `instancias.py` | Leitura das instâncias e relaxação linear |
| `experimento.py` / `analise.py` | Experimento e análise do protocolo inicial |
| `laboratorio.py` / `janela_problema.py` | Interface gráfica |
| `motor_lab.py` / `estatistica_lab.py` | Execução e estatística do laboratório |
| `problemas.py` / `gerar_frete.py` | Catálogo, gerador de instâncias e cenários de frete |

## Referências principais

- André, L.; Parpinelli, R. S. (2015). The multiple knapsack problem approached by a binary differential evolution algorithm with adaptive parameters. *Polibits*, 51, 47–54.
- Chu, P. C.; Beasley, J. E. (1998). A genetic algorithm for the multidimensional knapsack problem. *Journal of Heuristics*, 4(1), 63–86.
- Dehghani, M. et al. (2023). Coati Optimization Algorithm. *Knowledge-Based Systems*, 259, 110011.
- Derrac, J. et al. (2011). A practical tutorial on the use of nonparametric statistical tests. *Swarm and Evolutionary Computation*, 1(1), 3–18.
