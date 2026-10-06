# Escalonador de Help Desk de TI com Algoritmos Gulosos

### Alunos
| Matrícula | Aluno |
| -- | -- |
| 211062384 | Pedro Henrique Braga de Morais |

Trabalho da disciplina **Projeto de Algoritmos** — aplicação real de dois algoritmos
gulosos vistos no módulo: **Interval Partitioning** e **Minimizing Lateness (EDF)**.


O programa lê um arquivo JSON descrevendo um turno de help desk e imprime, passo a
passo, as decisões que cada algoritmo toma, a prova de que o resultado é ótimo e um
resumo operacional do turno.

```
python main.py dados/exemplo_turno.json
```

Só usa a biblioteca padrão do Python (3.10+). Sem dependências.

---

## 1. O problema real

Um help desk de TI corporativo lida, todo dia, com dois tipos de trabalho:

| Tipo | Característica | Pergunta operacional |
|---|---|---|
| **Janelas de manutenção** (atualizar firmware, aplicar patches no ERP, trocar nobreak…) | Horário **fixo**, acordado com a área afetada. Exige um técnico dedicado do início ao fim. | *Quantos técnicos preciso escalar para cobrir todas as janelas, e quem faz o quê?* |
| **Fila de chamados** (VPN não conecta, impressora offline, conta bloqueada…) | Cada chamado tem uma **duração estimada** e um **prazo de SLA** (Service Level Agreement — o prazo contratual máximo de resolução). | *Em que ordem o técnico de plantão deve atender para que nenhum SLA estoure "muito"?* |

São dois problemas de escalonamento diferentes, e cada um é resolvido de forma exata
por um algoritmo guloso clássico.

## 2. Modelagem

```
Entrada (JSON)
├── janelas_manutencao ──► Interval Partitioning ──► nº mínimo de técnicos + escala de cada um
└── chamados ───────────► Minimizing Lateness   ──► ordem de atendimento + atraso máximo
                                                        │
                                   Resumo: técnicos necessários vs. disponíveis
```

**Simplificações assumidas** (todas declaradas na seção 7):

- Os chamados já estão na fila no início do turno (backlog da noite/manhã).
- Um único técnico atende a fila, sem interromper um chamado para começar outro.
- Todo técnico pode executar qualquer janela ou chamado.

## 3. Algoritmo 1 — Interval Partitioning

**Problema.** Dado um conjunto de intervalos `[início, fim)`, particioná-los no menor
número de grupos tal que intervalos do mesmo grupo não se sobreponham. Cada grupo é um
técnico.

**Algoritmo guloso** (Kleinberg & Tardos, §4.1):

```
ordenar janelas por início
heap ← vazio                      # (instante em que fica livre, técnico)
para cada janela j em ordem:
    se heap não vazio e topo(heap).livre_em ≤ j.início:
        técnico ← pop(heap)       # reaproveita quem ficou livre mais cedo
    senão:
        técnico ← novo técnico    # todos estão ocupados neste instante
    atribuir j a técnico
    push(heap, (j.fim, técnico))
```

**Complexidade.** `O(n log n)` — a ordenação domina; cada janela faz uma operação de
heap em `O(log n)`.

**Por que é ótimo.** Defina a *profundidade* do conjunto como o maior número de janelas
ativas em um mesmo instante. Nesse instante cada janela precisa de um técnico distinto,
logo **profundidade ≤ ótimo**. O guloso só cria um técnico novo quando todos os
anteriores estão ocupados naquele instante — ou seja, quando a profundidade naquele
ponto é pelo menos o número de técnicos já criados. Portanto **guloso ≤ profundidade**.
Combinando: guloso = profundidade = ótimo.

O programa calcula a profundidade separadamente (varredura de eventos +1/−1) e
imprime as duas quantidades lado a lado como certificado de otimalidade.

> Detalhe de implementação: `[08:00, 10:00)` e `[10:00, 12:00)` **não** se sobrepõem
> (intervalos semiabertos), então o mesmo técnico pode emendar as duas. A varredura
> processa fins antes de inícios no mesmo minuto para refletir isso.

## 4. Algoritmo 2 — Minimizing Lateness (EDF)

**Problema.** Um recurso (o técnico de plantão); `n` tarefas, cada uma com duração
`t_j` e prazo `d_j`, todas disponíveis em `t = 0`. Escolher a ordem que minimiza o
**atraso máximo** `L = max_j (fim_j − d_j)`.

**Algoritmo guloso** (Kleinberg & Tardos, §4.2): atender em ordem crescente de prazo —
**Earliest Deadline First**. É a mesma regra usada por escalonadores de sistemas de
tempo real.

```
ordenar chamados por prazo
t ← início do turno
para cada chamado c em ordem:
    c.início ← t ;  c.fim ← t + c.duração ;  t ← c.fim
atraso_máximo ← max(0, max_c (c.fim − c.prazo))
```

**Complexidade.** `O(n log n)` — é uma ordenação seguida de uma passada linear.

**Por que é ótimo** (argumento de troca, resumido). Em qualquer ordem sem ociosidade,
chame de *inversão* um par adjacente `(i, j)` em que `i` vem antes mas `d_i > d_j`.
Trocar os dois:

- `j` termina mais cedo → seu atraso só diminui;
- `i` passa a terminar exatamente onde `j` terminava; como `d_i > d_j`, o atraso de `i`
  na nova posição é **menor** que o atraso que `j` tinha ali.

Logo a troca nunca aumenta o atraso máximo. Removendo inversões uma a uma chega-se à
ordem EDF (a única sem inversões, a menos de empates) com atraso máximo ≤ ao da ordem
original. Como isso vale para uma ordem ótima, EDF é ótimo.

**Certificado no log.** Para qualquer prazo `d`, os chamados com prazo ≤ `d` somam `T`
minutos de trabalho; o último deles termina em pelo menos `início + T` e tem prazo
≤ `d`, logo alguém atrasa pelo menos `início + T − d`. O máximo sobre todos os `d` é
um limite inferior para **qualquer** ordem — e o EDF atinge exatamente esse valor. O
programa imprime o limite ao lado do resultado.

**Comparação com ordens intuitivas.** O programa também simula três ordens que um
gestor usaria "de cabeça" e mostra que todas perdem para o EDF no exemplo:

| Estratégia | Atraso máximo | Chamados fora do SLA |
|---|---|---|
| FIFO (ordem de abertura) | 2h | 4 |
| SPT — menor duração primeiro | 25min | 3 |
| Prioridade declarada (P1 > P2 > P3) | 3h30 | 6 |
| **EDF — menor prazo primeiro** | **15min** | **1** |

A ordem por prioridade é a pior justamente porque ignora **há quanto tempo** o chamado
espera: um P3 aberto ontem às 16:30 já está com o SLA quase vencido às 08:00, enquanto o
P1 aberto às 07:50 ainda tem 4 horas. Em um help desk real, a prioridade já está embutida
no prazo (P1 tem SLA mais curto) — por isso ordenar pelo prazo é a forma correta de
honrá-la.

## 5. Como executar

```bash
# log completo
python main.py dados/exemplo_turno.json

# mostra também o estado do heap a cada passo
python main.py dados/exemplo_turno.json --debug

# grava o resultado estruturado para consumo por outro programa
python main.py dados/exemplo_turno.json --json saida.json

# variante com um técnico a menos → alerta de equipe insuficiente
python main.py dados/exemplo_equipe_curta.json

# testes (gulosos vs. força bruta em instâncias aleatórias)
python -m unittest discover -s tests -v
```

## 6. Formato do arquivo de entrada

```jsonc
{
  "turno": { "inicio": "08:00", "fim": "18:00" },
  "equipe_disponivel": 4,

  "janelas_manutencao": [
    { "id": "JM-01", "descricao": "Atualização de firmware dos switches",
      "inicio": "08:00", "fim": "09:30" }
  ],

  "chamados": [
    { "id": "CH-101", "descricao": "VPN não conecta", "prioridade": "P2",
      "abertura": "05/10 18:00",      // informativo, aparece no log
      "duracao_min": 40,              // estimativa de atendimento
      "prazo": "10:00" }              // instante em que o SLA expira
  ]
}
```

Horários no formato `HH:MM`. Ids devem ser únicos. O programa valida a entrada e
aborta com mensagem clara se algo estiver inconsistente (fim antes do início, duração
não positiva, id repetido).

## 7. Limitações — o que o modelo NÃO cobre

Declaradas de propósito: cada uma delas muda o problema para algo que **não** é
resolvido por guloso.

1. **Chamados que chegam durante o turno.** O EDF é ótimo quando todas as tarefas estão
   disponíveis no início. Com instantes de chegada diferentes e sem interrupção
   (`1 | r_j | L_max` na notação de escalonamento), o problema é NP-difícil. Com
   interrupção permitida (preempção), EDF volta a ser ótimo — mas aí o modelo de
   "técnico que larga um chamado no meio" é outro.
2. **Vários técnicos na mesma fila.** Minimizar atraso máximo em máquinas paralelas
   (`P || L_max`) também é NP-difícil. Por isso o modelo tem exatamente um técnico de
   plantão para a fila.
3. **EDF minimiza o pior atraso, não a quantidade de chamados atrasados.** Existem
   instâncias em que outra ordem atrasa menos chamados (com um deles atrasando muito).
   Minimizar o número de atrasados é o algoritmo de Moore–Hodgson, outro problema.
4. **Janelas são fixas.** Se o horário de uma janela pudesse deslizar dentro de uma
   faixa ("entre 09:00 e 12:00, dura 1h"), o problema vira escalonamento com janelas
   de tempo, que em geral é NP-difícil e não tem solução gulosa exata.
5. **Técnicos intercambiáveis.** Não há habilidades ou restrições de quem pode fazer
   o quê.
6. **Durações são estimativas exatas.** Não há tratamento de incerteza.

## 8. Testes

`tests/test_algoritmos.py` compara os dois gulosos com **força bruta** em centenas de
instâncias aleatórias pequenas:

- Interval Partitioning: a atribuição é válida (nenhum técnico com janelas sobrepostas),
  o número de técnicos é igual à profundidade e igual ao mínimo obtido testando todas as
  colorações possíveis (n ≤ 6).
- Minimizing Lateness: a ordem é por prazo, sem ociosidade, atinge o limite inferior e
  é igual ao mínimo sobre todas as permutações (n ≤ 7); nunca perde para FIFO, SPT ou
  prioridade.

## 9. Estrutura do repositório

```
.
├── main.py                            # CLI: lê o JSON, roda os dois algoritmos, imprime o log
├── helpdesk/
│   ├── modelos.py                     # dataclasses + leitura/validação da entrada
│   ├── tempo.py                       # conversão HH:MM ↔ minutos
│   ├── interval_partitioning.py       # algoritmo 1 + cálculo da profundidade
│   ├── minimizing_lateness.py         # algoritmo 2 + limite inferior + estratégias de comparação
│   └── relatorio.py                   # Gantt ASCII e tabelas
├── dados/
│   ├── exemplo_turno.json             # turno realista (10 janelas, 8 chamados)
│   └── exemplo_equipe_curta.json      # mesmo turno, equipe insuficiente
└── tests/
    └── test_algoritmos.py             # gulosos vs. força bruta
```

## 10. Referências

- KLEINBERG, J.; TARDOS, É. *Algorithm Design*. Addison-Wesley, 2006. Capítulo 4
  (Greedy Algorithms), seções 4.1 (Interval Partitioning) e 4.2 (Scheduling to
  Minimize Lateness).
