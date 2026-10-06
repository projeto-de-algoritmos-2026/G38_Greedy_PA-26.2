"""Interval Partitioning aplicado às janelas de manutenção.

Problema: dado um conjunto de janelas com horário fixo [inicio, fim), alocar o
MENOR número de técnicos de modo que nenhum técnico tenha duas janelas que se
sobreponham.

Algoritmo guloso (Kleinberg & Tardos, 4.1):
    1. Ordenar as janelas por horário de início.
    2. Para cada janela, se existe um técnico cuja última janela já terminou,
       reaproveitá-lo; senão, alocar um técnico novo.

Para achar "o técnico que fica livre mais cedo" em O(log n) usa-se um min-heap
(fila de prioridade em que o menor elemento sai primeiro) indexado pelo horário
em que cada técnico fica livre. Complexidade total: O(n log n).

Otimalidade: a *profundidade* do conjunto (maior número de janelas simultâneas
em algum instante) é um limite inferior óbvio — naquele instante, cada janela
precisa de um técnico distinto. O guloso só abre um técnico novo quando todos
os anteriores estão ocupados naquele instante, logo nunca ultrapassa a
profundidade. Limite inferior atingido ⇒ ótimo.
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field

from .modelos import JanelaManutencao
from .tempo import min_para_hm

log = logging.getLogger("IP")


@dataclass
class ResultadoParticao:
    num_tecnicos: int
    # técnico (1..k) -> janelas atribuídas, em ordem de início
    atribuicao: dict[int, list[JanelaManutencao]] = field(default_factory=dict)
    profundidade: int = 0

    @property
    def otimo(self) -> bool:
        return self.num_tecnicos == self.profundidade


def profundidade(janelas: list[JanelaManutencao]) -> int:
    """Maior número de janelas ativas ao mesmo tempo (limite inferior da resposta).

    Varredura de eventos: +1 em cada início, -1 em cada fim. Em empates no mesmo
    instante, fins são processados antes de inícios, porque [08:00, 10:00) e
    [10:00, 12:00) NÃO se sobrepõem e podem ficar com o mesmo técnico.
    """
    eventos: list[tuple[int, int]] = []
    for j in janelas:
        eventos.append((j.inicio, +1))
        eventos.append((j.fim, -1))
    eventos.sort()  # (-1) < (+1), então fins vêm antes de inícios no mesmo minuto

    atual = maximo = 0
    for _, delta in eventos:
        atual += delta
        maximo = max(maximo, atual)
    return maximo


def particionar(janelas: list[JanelaManutencao]) -> ResultadoParticao:
    """Executa o guloso e registra cada decisão no logger 'IP'."""
    ordenadas = sorted(janelas, key=lambda j: (j.inicio, j.fim))
    log.info("Passo 1 — ordenar %d janelas por horário de início", len(ordenadas))
    for j in ordenadas:
        log.debug("   %s  %s–%s  %s", j.id, min_para_hm(j.inicio), min_para_hm(j.fim), j.descricao)

    log.info("Passo 2 — percorrer em ordem, reaproveitando o técnico que fica livre mais cedo")

    # heap de (instante em que fica livre, número do técnico)
    livres_em: list[tuple[int, int]] = []
    atribuicao: dict[int, list[JanelaManutencao]] = {}

    for j in ordenadas:
        cabecalho = f"{min_para_hm(j.inicio)}  {j.id} ({min_para_hm(j.inicio)}–{min_para_hm(j.fim)}) {j.descricao}"

        if livres_em and livres_em[0][0] <= j.inicio:
            livre_desde, tecnico = heapq.heappop(livres_em)
            log.info("%s", cabecalho)
            log.info(
                "         → Técnico %d está livre desde %s → REAPROVEITADO",
                tecnico, min_para_hm(livre_desde),
            )
        else:
            tecnico = len(atribuicao) + 1
            atribuicao[tecnico] = []
            log.info("%s", cabecalho)
            if livres_em:
                proximo_livre, quem = livres_em[0]
                log.info(
                    "         → os %d técnico(s) já alocado(s) estão ocupados (o primeiro a "
                    "liberar é o Técnico %d, às %s) → ALOCA Técnico %d",
                    len(atribuicao) - 1, quem, min_para_hm(proximo_livre), tecnico,
                )
            else:
                log.info("         → nenhum técnico alocado ainda → ALOCA Técnico %d", tecnico)

        atribuicao[tecnico].append(j)
        heapq.heappush(livres_em, (j.fim, tecnico))
        log.debug(
            "         heap (livre_em, técnico): %s",
            [(min_para_hm(t), k) for t, k in sorted(livres_em)],
        )

    prof = profundidade(janelas)
    resultado = ResultadoParticao(len(atribuicao), atribuicao, prof)

    log.info("Passo 3 — verificar otimalidade")
    log.info("         técnicos alocados pelo guloso : %d", resultado.num_tecnicos)
    log.info("         profundidade (limite inferior): %d", prof)
    if resultado.otimo:
        log.info("         limite inferior atingido ⇒ solução ÓTIMA")
    else:  # não deve acontecer; fica como salvaguarda
        log.warning("         guloso acima do limite inferior — verifique a implementação")

    return resultado
